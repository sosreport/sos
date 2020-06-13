from sos.report.plugins import DebianPlugin
from sos.policies import PackageManager, LinuxPolicy


class DebianPolicy(LinuxPolicy):
    distro = "Debian"
    vendor = "the Debian project"
    vendor_url = "https://www.debian.org/"
    ticket_number = ""
    _debq_cmd = "dpkg-query -W -f='${Package}|${Version}\\n'"
    _debv_cmd = "dpkg --verify"
    _debv_filter = ""
    name_pattern = 'friendly'
    valid_subclasses = [DebianPlugin]
    PATH = "/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games" \
           + ":/usr/local/sbin:/usr/local/bin"
    sos_pkg_name = 'sosreport'
    sos_bin_path = '/usr/bin/sosreport'

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super(DebianPolicy, self).__init__(sysroot=sysroot, init=init,
                                           probe_runtime=probe_runtime)
        self.ticket_number = ""
        self.package_manager = PackageManager(query_command=self._debq_cmd,
                                              verify_command=self._debv_cmd,
                                              verify_filter=self._debv_filter,
                                              chroot=sysroot,
                                              remote_exec=remote_exec)

        self.valid_subclasses = [DebianPlugin]

    def _get_pkg_name_for_binary(self, binary):
        # for binary not specified inside {..}, return binary itself
        return {
            "xz": "xz-utils"
        }.get(binary, binary)

# vim: set et ts=4 sw=4 :
