# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Sas(Plugin, IndependentPlugin):
    """Collects SAS PHY link rate information.

    For each SAS PHY present on the system, this plugin collects the
    current negotiated link rate as reported by the kernel, as well as
    the hardware maximum link rate. A negotiated rate lower than the
    hardware maximum indicates the link has trained at a reduced speed,
    which can point to problems with the cabling, backplane, or an
    expander.

    The attributes of SAS devices and the contents of SES enclosures are
    not collected by this plugin.
    """

    short_desc = 'SAS PHY link rates'
    plugin_name = 'sas'
    profiles = ('storage', 'hardware')
    files = (
        '/sys/class/sas_phy/*/negotiated_linkrate',
        '/sys/class/sas_phy/*/maximum_linkrate_hw',
    )

    def setup(self):
        self.add_copy_spec([
            '/sys/class/sas_phy/*/negotiated_linkrate',
            '/sys/class/sas_phy/*/maximum_linkrate_hw',
        ])


# vim: set et ts=4 sw=4 :
