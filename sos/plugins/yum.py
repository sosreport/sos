# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin


class Yum(Plugin, RedHatPlugin):
    """yum information
    """

    plugin_name = 'yum'
    profiles = ('system', 'packagemanager', 'sysmgmt')

    files = ('/etc/yum.conf',)
    packages = ('yum',)

    option_list = [
        ("yumlist", "list repositories and packages", "slow", False),
        ("yumdebug", "gather yum debugging data", "slow", False)
    ]

    def setup(self):
        # Pull all yum related information
        self.add_copy_spec([
            "/etc/yum",
            "/etc/yum.repos.d",
            "/etc/yum.conf",
            "/var/log/yum.log"
        ])

        # Get a list of channels the machine is subscribed to.
        self.add_cmd_output("yum -C repolist")

        # candlepin info
        self.add_forbidden_path("/etc/pki/entitlement/key.pem")
        self.add_forbidden_path("/etc/pki/entitlement/*-key.pem")
        self.add_copy_spec([
            "/etc/pki/product/*.pem",
            "/etc/pki/consumer/cert.pem",
            "/etc/pki/entitlement/*.pem"
        ])
        self.add_cmd_output("yum history")

        if self.get_option("yumlist"):
            # List various information about available packages
            self.add_cmd_output("yum list")

        if self.get_option("yumdebug") and self.is_installed('yum-utils'):
            # RHEL6+ alternative for this whole function:
            # self.add_cmd_output("yum-debug-dump '%s'"
            # % os.path.join(self.commons['dstroot'],"yum-debug-dump"))
            r = self.call_ext_prog("yum-debug-dump")
            try:
                self.add_cmd_output("zcat %s" % (r['output'].split()[-1],))
            except IndexError:
                pass

# vim: set et ts=4 sw=4 :
