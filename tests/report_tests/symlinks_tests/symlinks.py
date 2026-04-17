# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Symlinks(Plugin, IndependentPlugin):
    """Collect directories that contain symlinks
    """

    plugin_name = 'symlinks'
    short_desc = 'fake plugin to test different symlinks test cases'

    def setup(self):

        self.add_copy_spec([
            "/etc/absolute",
            "/etc/relative",
            "/etc/recursive",
            "/var/lib/symlink",
        ])

        symlink_conf_file = "/var/lib/symlink/symlink.ini"

        try:
            with open(symlink_conf_file, 'r', encoding='UTF-8') as cfile:
                for line in cfile.read().splitlines():
                    if not line:
                        continue
        except IOError as error:
            self._log_error(f'Could not open conf file {symlink_conf_file}:'
                            f' {error}')

    def postproc(self):

        inifile = "/var/lib/symlink/symlink.ini"

        self.do_path_regex_sub(inifile, r"(.*)", r"\1*********")
