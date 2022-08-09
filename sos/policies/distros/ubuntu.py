# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import UbuntuPlugin
from sos.policies.distros.debian import DebianPolicy

import os


class UbuntuPolicy(DebianPolicy):
    distro = "Ubuntu"
    vendor = "Canonical"
    vendor_urls = [
        ('Community Website', 'https://www.ubuntu.com/'),
        ('Commercial Support', 'https://www.canonical.com')
    ]
    PATH = "/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games" \
           + ":/usr/local/sbin:/usr/local/bin:/snap/bin"
    _upload_url = "https://files.support.canonical.com/uploads/"
    _upload_user = "ubuntu"
    _upload_password = "ubuntu"
    _upload_method = 'put'

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super(UbuntuPolicy, self).__init__(sysroot=sysroot, init=init,
                                           probe_runtime=probe_runtime,
                                           remote_exec=remote_exec)
        self.valid_subclasses += [UbuntuPlugin]

    @classmethod
    def check(cls, remote=''):
        """This method checks to see if we are running on Ubuntu.
           It returns True or False."""

        if remote:
            return cls.distro in remote

        try:
            with open('/etc/lsb-release', 'r') as fp:
                return "Ubuntu" in fp.read()
        except IOError:
            return False

    def dist_version(self):
        """ Returns the version stated in DISTRIB_RELEASE
        """
        try:
            with open('/etc/lsb-release', 'r') as fp:
                lines = fp.readlines()
                for line in lines:
                    if "DISTRIB_RELEASE" in line:
                        return int(line.split("=")[1].strip())
            return False
        except (IOError, ValueError):
            return False

    def get_upload_https_auth(self):
        if self.upload_url.startswith(self._upload_url):
            return (self._upload_user, self._upload_password)
        else:
            return super(UbuntuPolicy, self).get_upload_https_auth()

    def get_upload_url_string(self):
        if self.upload_url.startswith(self._upload_url):
            return "Canonical Support File Server"
        else:
            return self.get_upload_url()

    def get_upload_url(self):
        if not self.upload_url or self.upload_url.startswith(self._upload_url):
            if not self.upload_archive_name:
                return self._upload_url
            fname = os.path.basename(self.upload_archive_name)
            return self._upload_url + fname
        super(UbuntuPolicy, self).get_upload_url()

# vim: set et ts=4 sw=4 :
