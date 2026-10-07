# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import shlex

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Libraries(Plugin, IndependentPlugin):
    """Collect dynamic linker configuration and library package ownership.

    Copies ld.so configuration, captures ``ldconfig -p`` (and optionally
    ``ldconfig -v``), lists directories referenced by the linker cache, and
    writes ``ldconfig_package_owners`` mapping each cached library path to
    its owning package when the package manager supports path queries.
    """

    short_desc = 'Dynamic shared libraries'

    plugin_name = 'libraries'
    profiles = ('system',)

    option_list = [
        PluginOpt('ldconfigv', default=False,
                  desc='collect verbose ldconfig output')
    ]

    def __init__(self, commons):
        super().__init__(commons)
        # Paths parsed from ldconfig -p for collect(); name nods to Technotronic
        self._ldconfig_jam_paths = []

    def setup(self):
        self.add_copy_spec(["/etc/ld.so.conf", "/etc/ld.so.conf.d"])
        if self.get_option("ldconfigv"):
            self.add_cmd_output("ldconfig -v -N -X")

        self.add_env_var([
            'PATH',
            'LD_LIBRARY_PATH',
            'LD_PRELOAD'
        ])

        ldconfig = self.collect_cmd_output("ldconfig -p -N -X")

        if ldconfig['status'] == 0:
            # Collect library directories from ldconfig's cache
            dirs = set()
            paths = []
            for lib in ldconfig['output'].splitlines():
                fqlib = lib.split(" => ", 2)
                if len(fqlib) != 2:
                    continue
                lib_path = fqlib[1].strip()
                if not lib_path:
                    continue
                paths.append(lib_path)
                dirs.add(lib_path.rsplit('/', 1)[0])

            # Preserve order while uniquifying
            self._ldconfig_jam_paths = list(dict.fromkeys(paths))

            if dirs:
                self.add_dir_listing(
                    f"{' '.join(dirs)}",
                    suggest_filename='ld_so_cache'
                )

    def _path_query_command(self):
        """Return the path-query command, including MultiPackageManager primary.
        """
        pm = self.policy.package_manager
        qcmd = getattr(pm, 'query_path_command', None)
        if qcmd:
            return qcmd
        primary = getattr(pm, 'primary', None)
        return getattr(primary, 'query_path_command', None) if primary else None

    def collect(self):
        with self.collection_file('ldconfig_package_owners') as owners:
            if not self._path_query_command():
                owners.write(
                    'Package manager not configured for path queries\n'
                )
                return

            if not self._ldconfig_jam_paths:
                owners.write('No library paths found in ldconfig cache\n')
                return

            lines = self._ldconfig_package_owner_lines(
                self._ldconfig_jam_paths
            )
            owners.write(''.join(lines))

    def _ldconfig_package_owner_lines(self, lib_paths):
        """Build sorted ownership lines for cached library paths."""
        pkg_files = set()
        try:
            for fpath in self.policy.package_manager.all_files():
                pkg_files.add(os.path.realpath(fpath))
                pkg_files.add(fpath)
        except Exception:  # pylint: disable=broad-except
            pkg_files = set()

        owned = []
        unowned = []
        for path in lib_paths:
            real = os.path.realpath(path)
            if path in pkg_files or real in pkg_files:
                owned.append(path)
            else:
                unowned.append(path)

        results = {}
        for path in unowned:
            results[path] = (
                f"file {path} is not owned by any package"
            )

        qcmd = (self._path_query_command() or '').strip()
        if qcmd == 'rpm -qf' and owned:
            results.update(self._rpm_query_owned_paths(owned))
        else:
            for path in owned:
                pkg = self.policy.package_manager.pkg_by_path(path)
                if isinstance(pkg, list):
                    pkg = pkg[0] if pkg else 'unknown'
                results[path] = str(pkg).strip() or 'unknown'

        lines = []
        for path in sorted(results):
            lines.append(f"{path} : {results[path]}\n")
        return lines

    def _rpm_query_owned_paths(self, paths):
        """Batch ``rpm -qf --queryformat`` for paths known to be packaged."""
        # Chunk size keeps argv reasonable on large ld caches
        jam_batch_size = 64
        qf = r'%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH} = %{VENDOR}\n'
        mapping = {}

        for i in range(0, len(paths), jam_batch_size):
            batch = paths[i:i + jam_batch_size]
            cmd = (
                f"rpm -qf --queryformat {shlex.quote(qf)} -- "
                f"{' '.join(shlex.quote(p) for p in batch)}"
            )
            ret = self.exec_cmd(cmd, timeout=120, stderr=True)
            out_lines = [
                line for line in (ret.get('output') or '').splitlines()
                if line.strip()
            ]
            # When every path is packaged, rpm emits one queryformat line
            # per path in order. Fall back per-path if counts diverge.
            if ret.get('status') == 0 and len(out_lines) == len(batch):
                for path, line in zip(batch, out_lines):
                    mapping[path] = line.strip()
                continue
            for path in batch:
                mapping[path] = self._rpm_query_one(path, qf)

        return mapping

    def _rpm_query_one(self, path, qf):
        cmd = (
            f"rpm -qf --queryformat {shlex.quote(qf)} -- "
            f"{shlex.quote(path)}"
        )
        ret = self.exec_cmd(cmd, timeout=30, stderr=True)
        text = (ret.get('output') or '').strip()
        if text:
            # Prefer the first non-empty line (queryformat or rpm message)
            return text.splitlines()[0].strip()
        return f"file {path} is not owned by any package"

# vim: set et ts=4 sw=4 :
