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


class SubscriptionManager(Plugin, RedHatPlugin):
    """subscription-manager information
    """

    plugin_name = 'subscription-manager'
    profiles = ('system', 'packagemanager', 'sysmgmt')

    files = ('/etc/rhsm/rhsm.conf',)
    packages = ('subscription-manager',)

    def setup(self):
        # rhsm config and logs
        self.add_copy_spec([
            "/etc/rhsm/",
            "/var/log/rhsm/rhsm.log",
            "/var/log/rhsm/rhsmcertd.log"])
        self.add_cmd_output([
            "subscription-manager list --installed",
            "subscription-manager list --consumed",
            "subscription-manager identity"
        ])
        self.add_cmd_output("rhsm-debug system --sos --no-archive "
                            "--no-subscriptions --destination %s"
                            % self.get_cmd_output_path())

# vim: et ts=4 sw=4
