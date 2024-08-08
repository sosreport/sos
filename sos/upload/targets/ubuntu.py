# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import os
from sos.upload.targets import UploadTarget
from sos.policies.distros.ubuntu import UbuntuPolicy


class UbuntuUploadTarget(UploadTarget):

    upload_target_name = 'Ubuntu Upload Target'
    upload_target_id = "canonical"
    _upload_url = "https://files.support.canonical.com/uploads/"
    _upload_user = "ubuntu"
    _upload_password = "ubuntu"
    _upload_method = "put"

    def __init__(self, parser=None, args=None, cmdline=None):
        super().__init__(parser=parser, args=args, cmdline=cmdline)

    def check_distribution(self):
        """ Return true if we are running in a Ubuntu system"""
        return isinstance(self.commons['policy'], UbuntuPolicy)

    def get_upload_https_auth(self, user=None, password=None):
        if self.upload_url.startswith(self._upload_url):
            return (self._upload_user, self._upload_password)
        return super().get_upload_https_auth()

    def get_upload_url_string(self):
        if self.upload_url.startswith(self._upload_url):
            return "Canonical Support File Server"
        return self._get_obfuscated_upload_url(self.get_upload_url())

    def get_upload_url(self):
        if not self.upload_url or self.upload_url.startswith(self._upload_url):
            if not self.upload_archive_name:
                return self._upload_url
            fname = os.path.basename(self.upload_archive_name)
            return self._upload_url + fname
        return super().get_upload_url()

# vim: set et ts=4 sw=4 :
