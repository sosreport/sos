# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Bios(Plugin, IndependentPlugin):
    """
    This plugin gathers BIOS and firmware information from the system.
    It collects version information, BIOS configuration settings, and
    hardware details needed for RT certification and troubleshooting
    firmware-related issues.

    For RT/Telco workloads, this plugin captures critical BIOS settings
    such as:
    - C-states (CPU idle states) configuration
    - P-states (CPU frequency/power management) configuration
    - Turbo/boost settings
    - CPU power management policies

    It also collects data needed to correlate BIOS configuration with the
    OS-visible state during RT certification:
    - CPU topology and NUMA layout (SMT / SubNUMA verification)
    - Per-NIC SR-IOV enablement (a BIOS-level setting)
    - Kernel boot parameters

    Vendor BIOS configuration is gathered via local vendor CLI tools when
    available (Dell racadm, HPE ilorest, Lenovo onecli, SuperMicro sum).
    All collection is performed locally on the running system; out-of-band
    BMC/Redfish collection is intentionally out of scope.

    Commands already run by other plugins are deliberately not repeated
    here, since command output is not deduplicated across plugins:
      dmidecode (plain)           -> hardware
      efibootmgr, mokutil         -> boot
      fwupdmgr get-devices/history-> fwupd
      tuned-adm                   -> tuned
      ethtool -i                  -> networking
      mstconfig (Mellanox NICs)   -> mellanox_firmware
      lspci -nnvv                 -> pci
    File copy specs ARE deduplicated by the archive, so overlapping
    copy_spec entries are kept for completeness and tagging.
    """

    short_desc = 'BIOS and firmware information'

    plugin_name = "bios"
    profiles = ('system', 'hardware', 'performance')

    option_list = [
        PluginOpt('efi-vars', default=False,
                  desc='collect detailed EFI variable information'),
        PluginOpt('vendor-tools', default=True,
                  desc='collect BIOS settings via vendor tools if available'),
    ]

    def _is_supermicro(self):
        """Return True if DMI identifies this as a SuperMicro system.

        The SuperMicro BIOS tool is named 'sum', which collides with the
        coreutils sum(1) checksum utility present on every system. Without
        this check, 'sum -c GetCurrentBiosCfg' would run coreutils sum and
        collect its usage error on all non-SuperMicro hardware.
        """
        for field in ("sys_vendor", "board_vendor"):
            path = f"/sys/class/dmi/id/{field}"
            if not self.path_exists(path):
                continue
            try:
                with open(path, 'r', encoding='UTF-8') as vfile:
                    vendor = vfile.read().strip().lower()
            except OSError:
                continue
            if "supermicro" in vendor or "super micro" in vendor:
                return True
        return False

    def setup(self):
        # DMI/SMBIOS information from sysfs
        # This provides BIOS version, vendor, date, and hardware details
        self.add_copy_spec([
            "/sys/class/dmi/id/bios_date",
            "/sys/class/dmi/id/bios_release",
            "/sys/class/dmi/id/bios_vendor",
            "/sys/class/dmi/id/bios_version",
            "/sys/class/dmi/id/board_name",
            "/sys/class/dmi/id/board_vendor",
            "/sys/class/dmi/id/board_version",
            "/sys/class/dmi/id/chassis_type",
            "/sys/class/dmi/id/chassis_vendor",
            "/sys/class/dmi/id/chassis_version",
            "/sys/class/dmi/id/product_family",
            "/sys/class/dmi/id/product_name",
            "/sys/class/dmi/id/product_version",
            "/sys/class/dmi/id/sys_vendor",
            "/sys/class/dmi/id/ec_firmware_release"
        ])

        # Per-type DMI decode. The plain 'dmidecode' run is omitted: the
        # hardware plugin already collects it (with a root_symlink).
        self.add_cmd_output([
            "dmidecode -t bios",       # BIOS-specific information
            "dmidecode -t system",     # System information
            "dmidecode -t baseboard",  # Motherboard information
            "dmidecode -t chassis",    # Chassis information
            "dmidecode -t processor",  # CPU info (includes microcode)
        ], tags="dmidecode")

        # Legacy BIOS decode
        self.add_cmd_output("biosdecode", tags="biosdecode")

        # Firmware listing via /sys/firmware
        self.add_dir_listing('/sys/firmware', recursive=True,
                             tags='ls_sys_firmware')

        # Firmware inventory. Only the variants the fwupd plugin does not
        # already run are collected here: it covers get-devices and
        # get-history, but not --show-all-devices or get-updates.
        self.add_cmd_output([
            "fwupdmgr get-devices --show-all-devices",
            "fwupdmgr get-updates",
        ], tags="fwupd")

        # If detailed EFI variables requested
        if self.get_option("efi-vars"):
            self.add_dir_listing('/sys/firmware/efi/efivars',
                                 tags='efi_vars')

        # System Management BIOS strings
        self.add_cmd_output("dmidecode -s bios-vendor", tags="bios_vendor")
        self.add_cmd_output("dmidecode -s bios-version", tags="bios_version")
        self.add_cmd_output("dmidecode -s bios-release-date",
                            tags="bios_release_date")
        self.add_cmd_output("dmidecode -s system-manufacturer",
                            tags="system_manufacturer")
        self.add_cmd_output("dmidecode -s system-product-name",
                            tags="system_product_name")
        self.add_cmd_output("dmidecode -s baseboard-manufacturer",
                            tags="baseboard_manufacturer")
        self.add_cmd_output("dmidecode -s baseboard-product-name",
                            tags="baseboard_product_name")

        # BIOS Configuration Settings - Critical for RT/Telco workloads
        # Collect C-state (CPU idle state) configuration
        self.add_copy_spec([
            "/sys/devices/system/cpu/cpu*/cpuidle/state*/name",
            "/sys/devices/system/cpu/cpu*/cpuidle/state*/desc",
            "/sys/devices/system/cpu/cpu*/cpuidle/state*/disable",
            "/sys/devices/system/cpu/cpu*/cpuidle/state*/latency",
            "/sys/devices/system/cpu/cpu*/cpuidle/state*/residency",
            "/sys/devices/system/cpu/cpu*/cpuidle/state*/time",
            "/sys/devices/system/cpu/cpu*/cpuidle/state*/usage",
        ], tags="cpu_idle_states")

        # Collect P-state (CPU frequency/power) configuration
        cpufreq = "/sys/devices/system/cpu/cpu*/cpufreq"
        self.add_copy_spec([
            f"{cpufreq}/affected_cpus",
            f"{cpufreq}/scaling_driver",
            f"{cpufreq}/scaling_governor",
            f"{cpufreq}/scaling_available_governors",
            f"{cpufreq}/scaling_max_freq",
            f"{cpufreq}/scaling_min_freq",
            f"{cpufreq}/cpuinfo_max_freq",
            f"{cpufreq}/cpuinfo_min_freq",
            f"{cpufreq}/scaling_cur_freq",
            f"{cpufreq}/energy_performance_preference",
            f"{cpufreq}/energy_performance_available_preferences",
            f"{cpufreq}/boost",
        ], tags="cpu_freq_states")

        # Intel-specific P-state driver info
        self.add_copy_spec([
            "/sys/devices/system/cpu/intel_pstate/status",
            "/sys/devices/system/cpu/intel_pstate/hwp_dynamic_boost",
            "/sys/devices/system/cpu/intel_pstate/max_perf_pct",
            "/sys/devices/system/cpu/intel_pstate/min_perf_pct",
            "/sys/devices/system/cpu/intel_pstate/no_turbo",
            "/sys/devices/system/cpu/intel_pstate/num_pstates",
            "/sys/devices/system/cpu/intel_pstate/turbo_pct",
        ], tags="intel_pstate")

        # AMD-specific P-state driver info. The driver-wide controls
        # (status, prefcore, dynamic_epp) are the counterpart to the
        # intel_pstate directory above; the exact set varies by kernel
        # version, so glob rather than enumerate.
        self.add_copy_spec([
            f"{cpufreq}/amd_pstate_highest_perf",
            f"{cpufreq}/amd_pstate_max_freq",
            f"{cpufreq}/amd_pstate_lowest_nonlinear_freq",
            "/sys/devices/system/cpu/amd_pstate/*",
        ], tags="amd_pstate")

        # CPU power management and thermal
        self.add_copy_spec([
            "/sys/devices/system/cpu/smt/active",
            "/sys/devices/system/cpu/smt/control",
            "/sys/devices/system/cpu/vulnerabilities/*",
        ], tags="cpu_config")

        # Per-NIC SR-IOV state. SR-IOV is enabled in BIOS and its
        # configuration has caused RT/telco regressions, so the enablement
        # and VF counts are recorded per interface. NIC driver/firmware
        # versions come from 'ethtool -i' in the networking plugin, and
        # Mellanox firmware settings from the mellanox_firmware plugin.
        self.add_copy_spec([
            "/sys/class/net/*/device/sriov_totalvfs",
            "/sys/class/net/*/device/sriov_numvfs",
            "/sys/class/net/*/device/sriov_drivers_autoprobe",
        ], tags="nic_sriov")

        # CPU topology and NUMA layout - verifies the OS-visible result of
        # BIOS settings such as HyperThreading (SMT) and SubNUMA/SNC.
        self.add_copy_spec([
            "/sys/devices/system/cpu/cpu*/topology/thread_siblings_list",
            "/sys/devices/system/cpu/cpu*/topology/core_siblings_list",
            "/sys/devices/system/node/node*/cpulist",
            "/sys/devices/system/node/node*/distance",
        ], tags="cpu_topology")

        # Kernel boot parameters, so BIOS settings can be correlated with
        # the OS-side configuration used during certification. The active
        # tuned profile is collected by the tuned plugin.
        self.add_copy_spec("/proc/cmdline", tags="kernel_cmdline")

        # Vendor-specific BIOS configuration tools (if available)
        if self.get_option("vendor-tools"):
            # HPE iLOrest - comprehensive BIOS settings
            self.add_cmd_output([
                "ilorest list --selector Bios. --json --nologo",
                "ilorest get --selector Bios. --json --nologo",
            ], tags="hpe_ilorest", timeout=60)

            # HPE conrep - legacy BIOS configuration tool
            self.add_cmd_output("conrep -s -f /dev/stdout",
                                tags="hpe_conrep", timeout=60)

            # Dell racadm - BIOS configuration.
            # OMSA installs this as idracadm7 under /opt rather than as
            # 'racadm' on PATH (see the dellrac plugin), so prefer the
            # packaged location and fall back to PATH only if present.
            racadm = "/opt/dell/srvadmin/bin/idracadm7"
            if not self.path_exists(racadm):
                racadm = "racadm"
            # 'get BIOS' returns only the list of attribute group names,
            # so each RT-relevant group must be fetched individually.
            # BiosBootSettings holds BootMode; IntegratedDevices holds
            # SriovGlobalEnable, the BIOS-level SR-IOV switch.
            self.add_cmd_output([
                f"{racadm} get BIOS",
                f"{racadm} get BIOS.SysProfileSettings",
                f"{racadm} get BIOS.ProcSettings",
                f"{racadm} get BIOS.MemSettings",
                f"{racadm} get BIOS.BiosBootSettings",
                f"{racadm} get BIOS.IntegratedDevices",
            ], tags="dell_racadm", timeout=60)

            # Dell syscfg - older Dell systems
            self.add_cmd_output("syscfg /s /b /aoe",
                                tags="dell_syscfg", timeout=60)

            # Lenovo OneCLI
            self.add_cmd_output("onecli config show --output-format json",
                                tags="lenovo_onecli", timeout=60)

            # SuperMicro Update Manager (sum) - BIOS configuration export.
            # Gated on DMI vendor because 'sum' collides with coreutils
            # sum(1); see _is_supermicro(). The other vendor tools have
            # unique names, so sos simply skips them when not installed.
            if self._is_supermicro():
                self.add_cmd_output([
                    "sum -c GetCurrentBiosCfg",
                    "sum -c GetBiosInfo",
                ], tags="supermicro_sum", timeout=60)

    def postproc(self):
        # Scrub any serial numbers from the output
        self.do_cmd_output_sub(
            "dmidecode",
            r"(Serial Number:).*",
            r"\1 ********"
        )

        # fwupdmgr reports a per-device serial number for attached hardware
        # (disks, displays, USB devices). Match only horizontal whitespace so
        # the expression cannot run past the end of the line.
        self.do_cmd_output_sub(
            "fwupdmgr",
            r"(Serial Number:)[ \t]*.*",
            r"\1 ********"
        )

        # dmidecode also exposes the system UUID and site asset tags. Both
        # identify the machine (and its owner) as directly as a serial does,
        # so they are scrubbed alongside it.
        self.do_cmd_output_sub(
            "dmidecode",
            r"(UUID:)[ \t]*.*",
            r"\1 ********"
        )
        self.do_cmd_output_sub(
            "dmidecode",
            r"(Asset Tag:)[ \t]*.*",
            r"\1 ********"
        )

        # ilorest returns BIOS data as JSON. The system serial, asset tag
        # and admin contact fields are identifying but not relevant to
        # certification. Only the quoted value is replaced, so the JSON
        # remains well-formed for downstream parsing.
        self.do_cmd_output_sub(
            "ilorest",
            r'("(?:SerialNumber|ServiceName'
            r'|Admin(?:Email|Name|Phone|OtherInfo)'
            r'|Server(?:Name|OtherInfo|AssetTag))"\s*:\s*)"[^"]*"',
            r'\1"********"'
        )


# vim: set et ts=4 sw=4 :
