# Copyright 2025, Jake Hunsaker <jacob.r.hunsaker@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import requests

from sos.upload.targets import SoSUploadTarget
from sos.utilities import TIMEOUT_DEFAULT


class HttpUpload(SoSUploadTarget):
    """
    Generic handler for HTTP(S) uploads. This target can be used standalone
    for adhoc uploads from user-provided addresses, and also be used as the
    backend for a vendor-provided target, so that individual vendors do not
    need to (but still may) rewrite http upload mechanisms in their own target.
    """
    target_id = 'http'
    target_protocols = ['http', 'https']
    prompt_for_credentials = True

    def __init__(self, options, url=None, username=None, password=None,
                 method=None, no_ssl_verify=None):
        if username:
            options.upload_user = username
        if password:
            options.upload_pass = password
        if url:
            options.upload_url = url
        if no_ssl_verify:
            options.upload_no_ssl_verify = no_ssl_verify
        self.method = method or options.upload_http_method
        self.http_headers = {}
        super().__init__(options)

    def set_http_auth_headers(self, headers):
        if not isinstance(headers, dict):
            raise TypeError(
                f"Headers for http(s) upload must be provided as a dict, got "
                f"{headers.__class__}"
            )
        self.http_headers = headers

    def set_http_method(self, method):
        """Set the http method to use from the requests library"""
        if method not in ['put', 'post']:
            raise ValueError(
                f"HTTP(S) upload method must be 'put' or 'post', not "
                f"'{method}'"
            )
        self.method = method

    def get_http_auth(self):
        return requests.auth.HTTPBasicAuth(self.opts.upload_user,
                                           self.opts.upload_pass)

    def upload(self):
        if self.method == 'put':
            ret = self._upload_with_put()
        else:
            ret = self._upload_with_post()
        if ret.status_code not in (200, 201):
            if ret.status_code == 401:
                raise Exception(
                    "Authentication failed: invalid user credentials"
                )
            raise Exception(
                f"Upload request returned {ret.status_code}: {ret.reason}"
            )
        return True

    def _upload_with_put(self):
        """Attempt an upload to an http(s) endpoint via a PUT"""
        return requests.put(
            self.opts.upload_url, data=self.upload_file,
            auth=self.get_http_auth(),
            verify=self.opts.upload_no_ssl_verify,
            timeout=TIMEOUT_DEFAULT
        )

    def _upload_with_post(self):
        files = {
            'file': (self.upload_file.split('/')[-1], self.upload_file,
                     self.http_headers)
        }
        return requests.post(
            self.opts.upload_url, files=files, auth=self.get_http_auth(),
            verify=self.opts.upload_no_ssl_verify, timeout=TIMEOUT_DEFAULT
        )
