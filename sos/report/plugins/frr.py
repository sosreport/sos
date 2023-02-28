# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Frr(Plugin, RedHatPlugin):
    """
    FRR is a routing project that provides numerous traditional routing
    protocols for Linux platforms. In particular, OpenStack uses FRR to provide
    BGP functionality for the overcloud nodes.

    This plugin is primarily designed the deployment of FRR within OSP
    environments, which deploy FRR in a container.
    """

    short_desc = 'Frr routing service'

    plugin_name = 'frr'
    profiles = ('network',)

    files = ('/etc/frr/zebra.conf',)
    packages = ('frr',)
    containers = ('frr',)

    def setup(self):
        self.add_copy_spec("/etc/frr/")

        if self.container_exists('frr'):
            subcmds = [
                'show bgp detail',
                'show bgp neighbors',
                'show bgp summary',
                'show history',
                'show ip bgp detail',
                'show ip bgp neighbors',
                'show ip bgp summary',
                'show ip bgp',
                'show ip route',
                'show ipv6 route',
                'show running-config',
                'show version',
            ]

            self.add_cmd_output(
                [f"vtysh -c '{subcmd}'" for subcmd in subcmds],
                container='frr'
            )

# vim: set et ts=4 sw=4 :
