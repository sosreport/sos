# Copyright (C) 2023 Red Hat, Inc., Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import re
from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Coredump(Plugin, IndependentPlugin):
    """
    This plugin collects from the systemd-coredump service, which is leveraged
    via the coredumpctl command.

    Beyond basic configuration of the service, the plugin will also attempt to
    collect information on available coredumps. For any coredumps reported by
    coredumpctl for which the core is present, this plugin will collect that
    coredump file. The number of dump files collects is controlled by the
    `dumps` option, defaulting to 3. Note that core collection is performed
    based on the most recent cores generated. The summary information provided
    by `coredumpctl info` is also collected.

    The coredump files will be at their canonical location in the sos archive,
    usually under var/lib/systemd/coredump. Symlinks are dropped in the plugin
    directory to assist in identifying which coredump aligns to which entry in
    the provided `coredumpctl list` output collection.

    Users may leverage the `executable` option to control which coredumps the
    plugin will collect. This option takes a case-insensitive python regex
    string. If provided, only coredump entries for which the EXE field in
    `coredumpctl list` output matches will be collected.

    The dump files collected are compressed, and users should be aware that
    when inflated these files can be orders of magnitude larger than their
    collected sizes.
    """

    short_desc = 'systemd-coredump related information and dump files'

    plugin_name = "coredump"
    profiles = ('system', 'debug')
    packages = ('systemd-udev', 'systemd-coredump')

    option_list = [
        PluginOpt("dumps", default=3, desc="number of dump files to collect"),
        PluginOpt("executable", default='',
                  desc=("only collect info and dump output for executables "
                        "matching this regex"))
    ]

    def setup(self):
        self.add_copy_spec([
            "/etc/systemd/coredump.conf",
            "/etc/systemd/coredump.conf.d/",
            "/run/systemd/coredump.conf.d/",
            "/usr/lib/systemd/coredump.conf.d/",
            "/usr/lib/systemd/systemd-coredump"
        ])

        coredump_list = self.collect_cmd_output("coredumpctl list --reverse")
        if coredump_list['status'] != 0:
            return

        cores_collected = 0
        for line in coredump_list["output"].splitlines()[1:]:
            cdump = line.split()
            pid = cdump[4]
            exe = cdump[-2]
            if regex := self.get_option("executable"):
                if not re.search(regex, exe, re.I):
                    continue
            cinfo = self.collect_cmd_output(f"coredumpctl info {pid}")
            if cinfo['status'] != 0:
                continue
            res = cinfo['output']
            if cores_collected < self.get_option("dumps"):
                core = re.search(r"(^\s*Storage:(.*)(\(present\)))", res, re.M)
                try:
                    core_path = core.groups()[1].strip()
                    # a_c_s does not return any information for a skipped file,
                    # so stat the size here and if the core is larger than our
                    # limit, move on to the next
                    # TODO: do not hardcode this. Extend log-size to per-plugin
                    # TODO: option and link this to that value
                    if os.stat(core_path).st_size > 209715200:
                        self._log_info(
                            f"Skipping core dump file {core_path} due to size"
                        )
                        continue
                    self.add_copy_spec(core_path, tailit=False, sizelimit=200)
                    plugpath = self.path_join(
                        self.commons['cmddir'],
                        self.name(),
                        f"coredump_{pid}_{self._mangle_command(exe)}"
                    )
                    # use os.path instead of the plugin wrapper here so that
                    # we always get the real path of the archive on disk
                    arcpath = os.path.join(self.archive.get_archive_path(),
                                           core_path)
                    linkpath = os.path.relpath(arcpath, plugpath)
                    linkpath = linkpath.replace('../', '', 1)
                    self.archive.add_link(linkpath, plugpath)
                    cores_collected += 1
                except AttributeError:
                    # no match on the re.search()
                    pass
                except Exception as err:
                    self._log_info(
                        f"Could not collect coredump for {pid} : {err}"
                    )

# vim: set et ts=4 sw=4 :
