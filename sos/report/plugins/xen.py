# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import re
from sos.report.plugins import Plugin, RedHatPlugin


class Xen(Plugin, RedHatPlugin):

    short_desc = 'Xen virtualization'

    plugin_name = 'xen'
    profiles = ('virt',)

    def determine_xen_host(self):
        """ Determine xen host type """
        if os.access("/proc/acpi/dsdt", os.R_OK):
            result = self.exec_cmd("grep -qi xen /proc/acpi/dsdt")
            if result['status'] == 0:
                return "hvm"

        if os.access("/proc/xen/capabilities", os.R_OK):
            result = self.exec_cmd("grep -q control_d /proc/xen/capabilities")
            if result['status'] == 0:
                return "dom0"
            return "domU"
        return "baremetal"

    def check_enabled(self):
        return self.determine_xen_host() == "baremetal"

    def is_running_xenstored(self):
        """ Check if xenstored is running """
        xs_pid = self.exec_cmd("pidof xenstored")['output']
        xs_pidnum = re.split('\n$', xs_pid)[0]
        return xs_pidnum.isdigit()

    def dom_collect_proc(self):
        """ Collect /proc/xen """
        self.add_copy_spec([
            "/proc/xen/balloon",
            "/proc/xen/capabilities",
            "/proc/xen/xsd_kva",
            "/proc/xen/xsd_port"])
        # determine if CPU has PAE support
        self.add_cmd_output("grep pae /proc/cpuinfo")
        # determine if CPU has Intel-VT or AMD-V support
        self.add_cmd_output("egrep -e 'vmx|svm' /proc/cpuinfo")

    def setup(self):
        host_type = self.determine_xen_host()
        if host_type == "domU":
            # we should collect /proc/xen and /sys/hypervisor
            self.dom_collect_proc()
            # determine if hardware virtualization support is enabled
            # in BIOS: /sys/hypervisor/properties/capabilities
            self.add_copy_spec("/sys/hypervisor")
        elif host_type == "hvm":
            # what do we collect here???
            pass
        elif host_type == "dom0":
            # default of dom0, collect lots of system information
            self.add_copy_spec([
                "/var/log/xen",
                "/etc/xen",
                "/sys/hypervisor/version",
                "/sys/hypervisor/compilation",
                "/sys/hypervisor/properties",
                "/sys/hypervisor/type"])
            self.add_cmd_output([
                "xm dmesg",
                "xm info",
                "xm list",
                "xm list --long",
                "bridge link show"
            ])
            self.dom_collect_proc()
            if self.is_running_xenstored():
                self.add_copy_spec("/sys/hypervisor/uuid")
                self.add_cmd_output("xenstore-ls")
            else:
                # we need tdb instead of xenstore-ls if cannot get it.
                self.add_copy_spec("/var/lib/xenstored/tdb")
        else:
            # for bare-metal, we don't have to do anything special
            return  # USEFUL

        self.add_custom_text("Xen hostType: "+host_type)

# vim: set et ts=4 sw=4 :
