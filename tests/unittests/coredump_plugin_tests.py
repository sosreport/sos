# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
"""
Unit tests for the user-facing PluginOpts on the coredump plugin

I've kept the commentary here extra verbose for the benefit of future
maintainers, this stuff can get dense and obtuse in my experience.

Approach
--------
These tests exercise ``Coredump.setup()`` directly rather than running a
full sosreport. Real systemd-coredump interaction is impossible in CI
(it needs actual crashed processes), so we replace three external
touchpoints with mocks:

1. ``collect_cmd_output`` is stubbed with scripted ``coredumpctl list``
   and ``coredumpctl info`` transcripts built by the ``_list_output``
   and ``_info_output`` helpers in this file. The transcripts preserve
   the column positions and regex-bearing lines the plugin parses, so
   the plugin's own parsing code still runs unmodified.

2. ``add_copy_spec`` is replaced with a ``MagicMock`` so we can inspect
   exactly which paths the plugin *would have* collected, without
   touching the filesystem.

3. ``os.stat`` is patched inside the coredump module's namespace so
   ``core_size`` comparisons see sizes we choose, not real files.

Each test sets one PluginOpt via ``plugin.set_option()``, runs
``setup()``, then asserts on the recorded mock calls. Kept hermetic
(no filesystem, no systemd, no real coredumps) so it runs identically
on any CI host.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from sos.archive import TarFileArchive
from sos.policies.distros import LinuxPolicy
from sos.policies.init_systems import InitSystem
from sos.report.plugins.coredump import Coredump


# ---------------------------------------------------------------------------
# Test doubles
#
# These are inlined rather than imported from plugin_tests.py because the
# CI harness runs unittest discovery with ``PYTHONPATH=.`` and sibling
# imports inside tests/unittests/ are not reliably resolvable across the
# different runners (python -m unittest, avocado) used by this project.
# ---------------------------------------------------------------------------


class MockArchive(TarFileArchive):
    """Minimal stand-in for the real TarFileArchive.

    Records ``add_file`` / ``add_string`` calls in ``self.m`` so tests
    can observe what the plugin tried to collect without touching disk.
    """

    # pylint: disable=super-init-not-called
    def __init__(self):
        self.m = {}
        self.strings = {}

    def name(self):
        return "mock.archive"

    def add_file(self, src, dest=None, force=False):
        if not dest:
            dest = src
        self.m[src] = dest

    def add_string(self, content, dest, mode='w'):
        self.m[dest] = content

    def add_link(self, source, link_name):
        pass

    def open_file(self, path):
        return open(self.m.get(path), 'r', encoding='utf-8')

    def close(self):
        pass

    def compress(self, method):
        pass

    def name_max(self):
        return 255

    def get_archive_path(self):
        return "/tmp/mockarchive"


class MockOptions:
    """Stand-in for the cmdlineopts namespace Plugin.__init__ reads."""

    all_logs = False
    dry_run = False
    since = None
    log_size = 25
    allow_system_changes = False
    no_postproc = False
    skip_files = []
    skip_commands = []
    sysroot = None


# ---------------------------------------------------------------------------
# Fake coredumpctl transcripts
#
# The coredump plugin parses the output of two real commands. These helpers
# reproduce just enough of the real output for the plugin's parsers to run
# unchanged. If systemd ever changes the shape of these commands, these
# helpers (and quite possibly the plugin itself) will need to track it.
# ---------------------------------------------------------------------------

# Example of the real ``coredumpctl list --reverse`` output that
# ``_list_output`` below simulates. Kept unindented so the columns are
# easy to eyeball without running into line-length limits.
#
# TIME                        PID   UID GID SIG     COREFILE EXE          SIZE
# Wed 2024-01-10 09:42:17 UTC 12345   0   0 SIGSEGV present  /usr/bin/foo  1.2M
# Wed 2024-01-10 09:41:02 UTC 12300   0   0 SIGABRT present  /usr/sbin/bar 512K
def _list_output(entries):
    """Build a ``coredumpctl list --reverse`` transcript.

    :param entries: list of (pid, exe) tuples, one per fake coredump row.
    """
    header = ("TIME                         PID  UID  GID SIG     COREFILE "
              "EXE                SIZE")
    lines = [header]
    for pid, exe in entries:
        lines.append(
            f"Wed 2026-04-22 10:00:00 UTC {pid} 0 0 SIGSEGV present "
            f"{exe} -"
        )
    return "\n".join(lines)


# Example of the real ``coredumpctl info <pid>`` output that
# ``_info_output`` below simulates. Only the ``Storage:`` and
# ``Executable:`` lines are consulted by the plugin.
#
#            PID: 12345 (foo)
#            UID: 0 (root)
#            GID: 0 (root)
#         Signal: 11 (SEGV)
#      Timestamp: Wed 2024-01-10 09:42:17 UTC (2s ago)
#        Storage: /var/lib/systemd/coredump/core.foo.0.abcd.12345.lz4 (present)
#     Executable: /usr/bin/foo
def _info_output(exe="/usr/bin/foo", pid="12345",
                 include_executable=True, present=True):
    """Build a ``coredumpctl info <pid>`` transcript.

    The plugin only looks at two lines from this output:

    * ``Storage:`` — regex'd for the core path and the literal
      ``(present)`` marker.
    * ``Executable:`` — regex'd for the binary path, but only when
      ``save_executable`` is enabled.

    :param include_executable: omit the Executable line to exercise the
        branch that logs a "Could not find executable path" warning.
    :param present: emit ``(missing)`` instead of ``(present)`` to
        exercise the branch that silently skips a missing core.
    """
    storage_suffix = "(present)" if present else "(missing)"
    storage = (f"         Storage: /var/lib/systemd/coredump/"
               f"core.foo.0.abcd.{pid}.lz4 {storage_suffix}")
    lines = [
        f"           PID: {pid}",
        storage,
    ]
    if include_executable:
        lines.append(f"      Executable: {exe}")
    return "\n".join(lines)


class CoredumpOptionTests(unittest.TestCase):
    """Exercise the user-facing PluginOpts on
    ``sos.report.plugins.coredump.Coredump``.

    Each test follows the same rhythm:

    1. Build a plugin with ``_make_plugin()``.
    2. Install a scripted ``collect_cmd_output`` via
       ``_install_collect_stub(plugin, entries)``.
    3. Replace ``add_copy_spec`` (and ``_log_info`` when relevant) with
       fresh ``MagicMock()`` instances so we can inspect recorded calls.
    4. Set the option under test via ``plugin.set_option(...)``.
    5. Run ``plugin.setup()`` inside a ``with patch(...os.stat...):``
       block to intercept filesystem size checks.
    6. Assert on the mocks' recorded calls.
    """

    # ------------------------------------------------------------------
    # Plugin construction
    # ------------------------------------------------------------------

    def _make_plugin(self):
        """Return a fresh ``Coredump`` plugin wired to test doubles.

        The ``commons`` dict passed here is a minimal version of what
        ``sos.report`` builds at runtime — just the keys
        ``Plugin.__init__`` actually reads. ``probe_runtime=False`` keeps
        the policy from interrogating the host, and ``cmddir`` matches
        the value sos sets in ``sos/report/__init__.py``.
        """
        plugin = Coredump({
            'sysroot': os.getcwd(),
            'policy': LinuxPolicy(init=InitSystem(), probe_runtime=False),
            'cmdlineopts': MockOptions(),
            'devices': {},
            'cmddir': 'sos_commands',
        })
        plugin.archive = MockArchive()
        return plugin

    # ------------------------------------------------------------------
    # Intercept helpers
    #
    # These three helpers replace the points in Coredump.setup() that
    # would otherwise touch the real system: external commands, real
    # filesystem stats, and the plugin's own collection sink.
    # ------------------------------------------------------------------

    def _install_collect_stub(self, plugin, list_entries, info_builder=None):
        """Replace ``plugin.collect_cmd_output`` with a scripted responder.

        The plugin calls ``collect_cmd_output`` twice per coredump in the
        real path:

        * Once with ``"coredumpctl list --reverse"`` to get the table.
        * Once per entry with ``"coredumpctl info <pid>"``.

        ``side_effect=fake_collect`` tells the MagicMock to call our
        ``fake_collect`` function on every invocation and return its
        result, giving us per-call dispatch based on the command string.

        :param list_entries: passed straight to ``_list_output`` to build
            the canned list output.
        :param info_builder: optional callable ``pid -> info_output_str``
            for tests that need per-pid variation (e.g. omitting the
            Executable line). Defaults to a single ``/usr/bin/foo`` entry.
        :returns: the MagicMock itself, so a caller can inspect
            ``.call_args_list`` to see every command the plugin issued.
        """
        if info_builder is None:
            def info_builder(pid):
                return _info_output(pid=pid)

        def fake_collect(cmd, *_args, **_kwargs):
            if cmd.startswith("coredumpctl list"):
                return {'status': 0, 'output': _list_output(list_entries)}
            if cmd.startswith("coredumpctl info"):
                pid = cmd.rsplit(" ", 1)[-1]
                return {'status': 0, 'output': info_builder(pid)}
            return {'status': 1, 'output': ''}

        collect_mock = MagicMock(side_effect=fake_collect)
        plugin.collect_cmd_output = collect_mock
        return collect_mock

    @staticmethod
    def _fake_stat(size_bytes):
        """Return a fake ``os.stat_result`` with only ``st_size`` set.

        The plugin reads only ``st_size`` from ``os.stat()``, so that's
        all we need to populate. ``MagicMock`` will happily answer any
        other attribute access with another mock, which is fine here.
        """
        st = MagicMock()
        st.st_size = size_bytes
        return st

    @staticmethod
    def _per_core_copy_calls(add_copy_spec_mock):
        """Return only the per-dump ``add_copy_spec`` calls.

        ``Coredump.setup()`` opens with a single bulk call —
        ``self.add_copy_spec([<five config file paths>])`` — before it
        reaches the per-coredump logic. That first call passes a
        **list** as its positional argument. The per-dump calls inside
        the loop (and the save_executable branch) pass a **string**
        (a single path).

        Filtering on ``isinstance(call.args[0], str)`` lets tests assert
        on "how many cores did the plugin try to collect?" without
        having to know or care about the static config-file preamble.
        """
        return [
            call for call in add_copy_spec_mock.call_args_list
            if call.args and isinstance(call.args[0], str)
        ]

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    # --- dumps ---------------------------------------------------------

    def test_dumps_option_limits_collected_cores(self):
        plugin = self._make_plugin()
        entries = [(str(10000 + i), "/usr/bin/foo") for i in range(5)]
        self._install_collect_stub(plugin, entries)
        plugin.add_copy_spec = MagicMock()
        plugin.set_option("dumps", 2)

        with patch("sos.report.plugins.coredump.os.stat",
                   return_value=self._fake_stat(1024)):
            plugin.setup()

        # Only 2 cores should have been added via add_copy_spec despite
        # the stub providing 5 info-ready entries. The very first
        # add_copy_spec call is the static config-file list; ignore it.
        per_core = self._per_core_copy_calls(plugin.add_copy_spec)
        self.assertEqual(len(per_core), 2)

    # --- core_size -----------------------------------------------------

    def test_core_size_skips_oversized_cores(self):
        plugin = self._make_plugin()
        entries = [("11111", "/usr/bin/foo"), ("22222", "/usr/bin/foo")]
        self._install_collect_stub(plugin, entries)
        plugin.add_copy_spec = MagicMock()
        plugin._log_info = MagicMock()
        plugin.set_option("core_size", 200)

        size_map = {
            "/var/lib/systemd/coredump/core.foo.0.abcd.11111.lz4":
                300 * 1024 * 1024,
            "/var/lib/systemd/coredump/core.foo.0.abcd.22222.lz4":
                50 * 1024 * 1024,
        }

        def fake_stat(path):
            return self._fake_stat(size_map[path])

        with patch("sos.report.plugins.coredump.os.stat",
                   side_effect=fake_stat):
            plugin.setup()

        # Only the 50MB core should have been collected.
        collected_paths = [c.args[0] for c in
                           self._per_core_copy_calls(plugin.add_copy_spec)]
        self.assertEqual(
            collected_paths,
            ["/var/lib/systemd/coredump/core.foo.0.abcd.22222.lz4"],
        )

        skip_logged = any(
            "size exceeding coredump.core_size" in call.args[0]
            for call in plugin._log_info.call_args_list
        )
        self.assertTrue(skip_logged,
                        "Expected an _log_info about oversized core dump")

    # --- save_executable -----------------------------------------------

    def test_save_executable_default_does_not_copy_exe(self):
        plugin = self._make_plugin()
        self._install_collect_stub(plugin, [("12345", "/usr/bin/foo")])
        plugin.add_copy_spec = MagicMock()
        # save_executable defaults to False — do not set_option.

        with patch("sos.report.plugins.coredump.os.stat",
                   return_value=self._fake_stat(1024)):
            plugin.setup()

        # Only the core itself should be copied; the executable should not.
        per_core = self._per_core_copy_calls(plugin.add_copy_spec)
        self.assertEqual(len(per_core), 1)
        self.assertEqual(
            per_core[0].args[0],
            "/var/lib/systemd/coredump/core.foo.0.abcd.12345.lz4",
        )

    def test_save_executable_true_copies_executable(self):
        plugin = self._make_plugin()
        self._install_collect_stub(plugin, [("12345", "/usr/bin/foo")])
        plugin.add_copy_spec = MagicMock()
        plugin.set_option("save_executable", True)

        with patch("sos.report.plugins.coredump.os.stat",
                   return_value=self._fake_stat(1024)):
            plugin.setup()

        # Two per-core calls: one for the executable (sizelimit=0), one
        # for the core itself.
        per_core = self._per_core_copy_calls(plugin.add_copy_spec)
        self.assertEqual(len(per_core), 2)

        exe_call = per_core[0]
        self.assertEqual(exe_call.args[0], "/usr/bin/foo")
        self.assertEqual(exe_call.kwargs.get("sizelimit"), 0)

        core_call = per_core[1]
        self.assertEqual(
            core_call.args[0],
            "/var/lib/systemd/coredump/core.foo.0.abcd.12345.lz4",
        )

    def test_save_executable_without_exe_in_info_logs_warning(self):
        plugin = self._make_plugin()
        self._install_collect_stub(
            plugin,
            [("12345", "/usr/bin/foo")],
            info_builder=lambda pid: _info_output(
                pid=pid, include_executable=False),
        )
        plugin.add_copy_spec = MagicMock()
        plugin._log_info = MagicMock()
        plugin.set_option("save_executable", True)

        with patch("sos.report.plugins.coredump.os.stat",
                   return_value=self._fake_stat(1024)):
            plugin.setup()

        # No executable line => no executable add_copy_spec, only the core.
        per_core = self._per_core_copy_calls(plugin.add_copy_spec)
        self.assertEqual(len(per_core), 1)
        self.assertEqual(
            per_core[0].args[0],
            "/var/lib/systemd/coredump/core.foo.0.abcd.12345.lz4",
        )

        warn_logged = any(
            "Could not find executable path" in call.args[0]
            for call in plugin._log_info.call_args_list
        )
        self.assertTrue(warn_logged,
                        "Expected an _log_info about missing executable path")

    # --- executable ----------------------------------------------------

    def test_executable_regex_filters_entries(self):
        plugin = self._make_plugin()
        entries = [
            ("10001", "/usr/bin/foo"),
            ("10002", "/usr/sbin/bar"),
            ("10003", "/usr/bin/FOOBAR"),  # case-insensitive match
        ]
        collect_mock = self._install_collect_stub(plugin, entries)
        plugin.add_copy_spec = MagicMock()
        plugin.set_option("executable", "foo")

        with patch("sos.report.plugins.coredump.os.stat",
                   return_value=self._fake_stat(1024)):
            plugin.setup()

        info_pids = [
            call.args[0].rsplit(" ", 1)[-1]
            for call in collect_mock.call_args_list
            if call.args[0].startswith("coredumpctl info")
        ]
        # bar is filtered out; foo and FOOBAR (re.I) both match.
        self.assertEqual(info_pids, ["10001", "10003"])

    def test_executable_regex_empty_allows_all(self):
        plugin = self._make_plugin()
        entries = [
            ("10001", "/usr/bin/foo"),
            ("10002", "/usr/sbin/bar"),
            ("10003", "/usr/bin/baz"),
        ]
        collect_mock = self._install_collect_stub(plugin, entries)
        plugin.add_copy_spec = MagicMock()
        # executable defaults to '' — do not set_option.

        with patch("sos.report.plugins.coredump.os.stat",
                   return_value=self._fake_stat(1024)):
            plugin.setup()

        info_pids = [
            call.args[0].rsplit(" ", 1)[-1]
            for call in collect_mock.call_args_list
            if call.args[0].startswith("coredumpctl info")
        ]
        self.assertEqual(info_pids, ["10001", "10002", "10003"])


if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
