# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos.report.plugins import UbuntuPlugin
from sos.policies.distros.debian import DebianPolicy

from sos.policies.package_managers.snap import SnapPackageManager
from sos.policies.package_managers.dpkg import DpkgPackageManager
from sos.policies.package_managers import MultiPackageManager


class UbuntuPolicy(DebianPolicy):
    vendor = "Canonical"
    vendor_urls = [
        ('Community Website', 'https://www.ubuntu.com/'),
        ('Commercial Support', 'https://www.canonical.com')
    ]
    os_release_name = 'Ubuntu'
    os_release_file = ''
    PATH = "/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games" \
           + ":/usr/local/sbin:/usr/local/bin:/snap/bin"
    _upload_url = "https://files.support.canonical.com/uploads/"
    _upload_user = "ubuntu"
    _upload_password = "ubuntu"
    _upload_method = 'put'

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super().__init__(sysroot=sysroot, init=init,
                         probe_runtime=probe_runtime,
                         remote_exec=remote_exec)

        self.package_manager = MultiPackageManager(
            primary=DpkgPackageManager,
            fallbacks=[SnapPackageManager],
            chroot=self.sysroot,
            remote_exec=remote_exec)

        try:
            if self.package_manager.pkg_by_name(
                    'sosreport')['pkg_manager'] == 'snap':
                self.sos_bin_path = '/snap/bin'
        except TypeError:
            # Use the default sos_bin_path
            pass

        self.valid_subclasses += [UbuntuPlugin]

    def dist_version(self):
        """ Returns the version stated in DISTRIB_RELEASE
        """
        try:
            with open('/etc/lsb-release', 'r', encoding='utf-8') as fp:
                lines = fp.readlines()
                for line in lines:
                    if "DISTRIB_RELEASE" in line:
                        return float(line.split("=")[1].strip())
            return False
        except (IOError, ValueError):
            return False


# vim: set et ts=4 sw=4 :
