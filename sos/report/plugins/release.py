# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Release(Plugin, UbuntuPlugin):

    short_desc = 'Linux release information'

    plugin_name = 'release'
    profiles = ('system',)

    def setup(self):
        self.add_cmd_output("lsb_release -a")
        self.add_cmd_output("lsb_release -d", suggest_filename="lsb_release",
                            root_symlink="lsb-release")

        self.add_copy_spec([
            "/etc/*release",
            "/etc/lsb-release/*"
        ])


class DebianRelease(Release, DebianPlugin):

    def setup(self):
        super(DebianRelease, self).setup()
        self.add_copy_spec('/etc/debian_version')


class RedHatRelease(Release, RedHatPlugin):

    def setup(self):
        self.add_file_tags({'/etc/redhat-release': 'redhat_release'})
        super(RedHatRelease, self).setup()

# vim: set et ts=4 sw=4 :
