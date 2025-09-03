# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
#
# This plugin enables collection of logs for system with IBM Spyre card

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
    def get_ibm_spyre_devices(lspci_output):
        """Extract PCI domain, bus, device, function for devices that match:
        - Vendor ID = 0x1014 (IBM)
        - Device ID = 0x06a7 or 0x06a8

        Parameters
        ----------
        lspci_out : str
        The output string from `lspci -n`.

        Returns
        -------
        list of tuples
        A list of (domain, bus, device, function) tuples for each matching
        card.
        """

        spyre_cards = []

        if not lspci_output:
            return None

        for line in lspci_output.splitlines():
            if not line.strip():
                continue

            try:
                pci_addr, _class, ids, _rest = line.split(maxsplit=3)
                vendor, device = ids.lower().split(":")
            except ValueError:
                continue

            if vendor == "1014" and device in ("06a7", "06a8"):
                if pci_addr.count(":") == 1:
                    pci_addr = "0000:" + pci_addr
                try:
                    domain, bus, dev_func = pci_addr.split(":")
                    pci_device, function = dev_func.split(".")
                except ValueError:
                    continue

                spyre_cards.append((domain, bus, pci_device, function))

        return spyre_cards

    def setup(self):

        lspci = self.exec_cmd("lspci -n")
        if lspci['status'] != 0:
            return

        spyre_cards = self.get_ibm_spyre_devices(lspci['output'])

        # Nothing to collect if spyre card is not found
        if not spyre_cards:
            return

        # Collects the VFIO device's sysfs directory structure
        for domain, bus, device, function in spyre_cards:
            pci_addr = f"{domain}:{bus}:{device}.{function}"
            pci_vfio = f"/sys/devices/pci{domain}:{bus}/{pci_addr}/vfio-dev"
            self.add_dir_listing(pci_vfio, tree=True)

        # Spyre card configuration files
        self.add_copy_spec([
            "/etc/modprobe.d/vfio-pci.conf",
            "/etc/udev/rules.d/95-vfio-3.rules",
            "/etc/security/limits.d/memlock.conf",
        ])

# vim: set et ts=4 sw=4 :
