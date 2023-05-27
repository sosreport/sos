# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class cxl(Plugin, IndependentPlugin):
    """This plugin collects data from Compute Express Link (CXL) devices
    """

    short_desc = 'Compute Express Link (CXL)'
    plugin_name = 'cxl'
    profiles = ('storage', 'hardware', 'memory')
    # Utilities can be installed by package or self compiled
    packages = ('cxl-cli', 'daxctl')
    commands = ('cxl', 'daxctl')

    def setup(self):
        """ Use the daxctl-list(1) command to collect:
        -i, --idle
           Include idle (not enabled / zero-sized) devices in the listing

        -D, --devices
           Include device-dax instance info in the listing (default)

        -M, --mappings
           Include device-dax instance mappings info in the listing

        -R, --regions
           Include region info in the listing

        Output is JSON formatted
        """
        self.add_cmd_output([
            "daxctl version",
            "daxctl list",
            "daxctl list -iDRM"
        ])

        """ Use the cxl-list(1) command to collect data about
        all CXL devices.

        -M, --memdevs
           Include CXL memory devices in the listing

        -i, --idle
           Include idle (not enabled / zero-sized) devices in the listing

        -H, --health
           Include health information in the memdev listing

        -I, --partition
           Include partition information in the memdev listing

        -A, --alert-config
           Include alert configuration in the memdev listing

        -B, --buses
           Include bus / CXL root object(s) in the listing

        -P, --ports
           Include port objects (CXL / PCIe root ports + Upstream Switch Ports)
           in the listing.

        -E, --endpoints
           Include endpoint objects (CXL Memory Device decoders) in the listing

        -D, --decoders
           Include decoder objects (CXL Memory decode capability instances in
           buses, ports, and endpoints) in the listing.

        -T, --targets
           Extend decoder listings with downstream port target information,
           port and bus listings with the downstream port information, and / or
           regions with mapping information.

        -R, --regions
           Include region objects in the listing.

        -v, --verbose
           Increase verbosity of the output. This can be specified multiple
           times to be even more verbose on the informational and miscellaneous
           output, and can be used to override omitted flags for showing
           specific information. Note that cxl list --verbose --verbose is
           equivalent to cxl list -vv.

           •   -v Enable --memdevs, --regions, --buses, --ports, --decoders,
                  and --targets.

           •   -vv Everything -v provides, plus include disabled devices with
                   --idle.

           •   -vvv Everything -vv provides, plus enable --health and
                    --partition.

        Output is JSON formatted
        """
        self.add_cmd_output([
            "cxl version",
            "cxl list",
            "cxl list -vvv"
        ])

# vim: set et ts=4 sw=4 :
