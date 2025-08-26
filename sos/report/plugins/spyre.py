# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
#
# This plugin enables collection of logs for system with IBM Spyre card

import re
import pyudev

from sos.report.plugins import Plugin, IndependentPlugin


class Spyre(Plugin, IndependentPlugin):
    """Spyre chip is IBM’s AI accelerator, designed to handle AI inferencing
    and workloads.

    The Spyre plugin collects data about the Spyre card’s VFIO device node
    tree, configuration files, and more.
    """

    short_desc = 'IBM Spyre Accelerator Information'
    plugin_name = 'spyre'
    architectures = ('ppc.*',)

    @staticmethod
    def get_spyre_cards_bus_ids():
        context = pyudev.Context()
        spyre_cards_bus_ids = []
        card_vendor_ids = ["0x1014"]    # IBM : 0x1014
        card_device_ids = ["0x06a7", "0x06a8"]  # spyre card device IDs

        for device in context.list_devices(subsystem='pci'):
            vendor_id = device.attributes.get("vendor").decode("utf-8").strip()
            if vendor_id not in card_vendor_ids:
                continue

            device_id = device.attributes.get("device").decode("utf-8").strip()
            if device_id not in card_device_ids:
                continue

            spyre_cards_bus_ids.append(device.sys_name)

        return spyre_cards_bus_ids

    def setup(self):
        spyre_cards = self.get_spyre_cards_bus_ids()

        # Nothing to collect if spyre card is not present in the system
        if not spyre_cards:
            return

        # Collects the VFIO device's sysfs directory structure
        for card in spyre_cards:
            match = re.match(r"(\w+:\w+):", card)
            if not match:
                continue

            pci_domain_bus = match.group(1)

            pci_vfio_dir = f"/sys/devices/pci{pci_domain_bus}/{card}/vfio-dev"
            self.add_dir_listing(pci_vfio_dir, tree=True)

        # Spyre card configuration files
        self.add_copy_spec([
            "/etc/modprobe.d/vfio-pci.conf",
            "/etc/udev/rules.d/95-vfio-3.rules",
            "/etc/security/limits.d/memlock.conf",
        ])

# vim: set et ts=4 sw=4 :
