# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class Java(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """Java runtime"""

    plugin_name = "java"
    profiles = ('webserver', 'java')
    verify_packages = ('java.*',)

    def setup(self):
        self.add_copy_spec("/etc/java")
        self.add_forbidden_path("/etc/java/security")
        self.add_cmd_output("alternatives --display java",
                            root_symlink="java")
        self.add_cmd_output("readlink -f /usr/bin/java")


# vim: set et ts=4 sw=4 :
