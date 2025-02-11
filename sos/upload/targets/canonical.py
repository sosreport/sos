# Copyright 2025, Jake Hunsaker <jacob.r.hunsaker@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.upload.targets import SoSUploadTarget
from sos.upload.targets.http import HttpUpload


class CanonicalUpload(SoSUploadTarget):
    """
    The upload target for providing archives to the Canonical support team.
    """
    target_id = 'canonical'
    target_name = 'Canonical Support File Server'
    prompt_for_credentials = False

    def upload(self):
        _uploader = HttpUpload(
            self.opts,
            url='https://files.support.canonical.com/uploads/',
            username='ubuntu',
            password='ubuntu',
            method='put'
        )
        return _uploader.upload()
