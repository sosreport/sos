# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageOneReportTest


class BiosPluginTest(StageOneReportTest):
    """
    Test the BIOS plugin to ensure it collects firmware and BIOS information
    needed for RT certification and troubleshooting.

    :avocado: tags=stageone
    """

    sos_cmd = '-o bios'

    def test_plugin_ran(self):
        """Verify the bios plugin was executed"""
        self.assertPluginIncluded('bios')

    def test_dmidecode_collected(self):
        """Verify dmidecode command outputs were collected"""
        # At a minimum we should have some dmidecode output
        self.assertFileGlobInArchive('sos_commands/bios/dmidecode*')

    def test_sysfs_bios_info_collected(self):
        """Verify BIOS sysfs information was collected"""
        # Should collect bios_version, bios_vendor, bios_date at minimum
        self.assertFileGlobInArchive('sys/class/dmi/id/bios_*')

    def test_sysfs_system_info_collected(self):
        """Verify system information from sysfs was collected"""
        # Should collect product_name, sys_vendor, etc.
        self.assertFileGlobInArchive('sys/class/dmi/id/*_vendor')

    def test_kernel_cmdline_collected(self):
        """Verify kernel boot parameters were collected for RT context"""
        self.assertFileGlobInArchive('proc/cmdline')

    def test_cpu_topology_collected(self):
        """Verify CPU topology was collected for SMT/NUMA verification"""
        self.assertFileGlobInArchive(
            'sys/devices/system/cpu/cpu*/topology/thread_siblings_list')

    def test_no_duplicate_vendor_plugin_commands(self):
        """Commands owned by other plugins must not be repeated here.

        Command output is not deduplicated across plugins, so these are
        deliberately left to hardware/boot/tuned/networking/fwupd.
        """
        for cmd in ['efibootmgr*', 'mokutil*', 'tuned-adm*', 'ethtool*',
                    'fwupdmgr_get-devices', 'fwupdmgr_get-history']:
            self.assertFileGlobNotInArchive(f'sos_commands/bios/{cmd}')

    def test_dmidecode_type_breakdown_collected(self):
        """Per-type dmidecode output is unique to this plugin"""
        self.assertFileGlobInArchive('sos_commands/bios/dmidecode_-t_bios')

# vim: set et ts=4 sw=4 :
