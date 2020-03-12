from __future__ import with_statement

from sos.plugins import UbuntuPlugin, DebianPlugin
from sos.policies.debian import DebianPolicy

import os


class UbuntuPolicy(DebianPolicy):
    distro = "Ubuntu"
    vendor = "Canonical"
    vendor_url = "https://www.ubuntu.com/"
    PATH = "/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games" \
           + ":/usr/local/sbin:/usr/local/bin:/snap/bin"
    _upload_url = "https://files.support.canonical.com/uploads/"
    _upload_user = "ubuntu"
    _upload_password = "ubuntu"
    _use_https_streaming = True

    def __init__(self, sysroot=None):
        super(UbuntuPolicy, self).__init__(sysroot=sysroot)
        self.valid_subclasses = [UbuntuPlugin, DebianPlugin]

    @classmethod
    def check(cls):
        """This method checks to see if we are running on Ubuntu.
           It returns True or False."""
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
                        return line.split("=")[1].strip()
            return False
        except IOError:
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
            fname = os.path.basename(self.upload_archive)
            return self._upload_url + fname
        super(UbuntuPolicy, self).get_upload_url()

# vim: set et ts=4 sw=4 :
