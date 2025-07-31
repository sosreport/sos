# Copyright 2024 Red Hat, Inc. Jose Castillo <jcastillo@redhat.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import os
import json
from sos.upload.targets import UploadTarget
from sos.utilities import convert_bytes, TIMEOUT_DEFAULT
from sos.policies.auth import DeviceAuthorizationClass
from sos.policies.distros.redhat import RHELPolicy
from sos import _sos as _

try:
    import requests
    REQUESTS_LOADED = True
except ImportError:
    REQUESTS_LOADED = False


class RHELUploadTarget(UploadTarget):

    client_identifier_url = "https://sso.redhat.com/auth/"\
        "realms/redhat-external/protocol/openid-connect/auth/device"
    token_endpoint = "https://sso.redhat.com/auth/realms/"\
        "redhat-external/protocol/openid-connect/token"
    upload_target_name = 'Red Hat Upload Target'
    upload_target_id = "redhat"

    def __init__(self, parser=None, args=None, cmdline=None):

        super().__init__(parser=parser, args=args, cmdline=cmdline)

    RH_API_HOST = "https://api.access.redhat.com"
    RH_SFTP_HOST = "sftp://sftp.access.redhat.com"
    _upload_url = RH_SFTP_HOST
    _upload_method = 'post'
    _device_token = None
    # Max size for an http single request is 1Gb
    _max_size_request = 1073741824

    def check_distribution(self):
        """Return true if we are running in a RHEL system"""
        return isinstance(self.commons['policy'], RHELPolicy)

    def pre_work(self, hook_commons):

        super().pre_work(hook_commons)

        self.upload_directory = self.commons['cmdlineopts'].upload_directory

    def prompt_for_upload_user(self):
        if self.commons['cmdlineopts'].upload_user:
            self.ui_log.info(
                _("The option --upload-user has been deprecated in favour"
                  " of device authorization in RHEL")
            )
        if not self.commons['cmdlineopts'].case_id:
            # no case id provided => failover to SFTP
            self.upload_url = self.RH_SFTP_HOST
            self.ui_log.info("No case id provided, uploading to SFTP")

    def prompt_for_upload_password(self):
        # With OIDC we don't ask for user/pass anymore
        if self.commons['cmdlineopts'].upload_pass:
            self.ui_log.info(
                _("The option --upload-pass has been deprecated in favour"
                  " of device authorization in RHEL")
            )

    def get_upload_url(self):
        rh_case_api = "/support/v1/cases/"\
                     f"{self.commons['cmdlineopts'].case_id}/attachments"
        try:
            if self.upload_url:
                return self.upload_url
            if self.commons['cmdlineopts'].upload_url:
                return self.commons['cmdlineopts'].upload_url
            if self.commons['cmdlineopts'].upload_protocol == 'sftp':
                return self.RH_SFTP_HOST
            if not self.commons['cmdlineopts'].case_id:
                return self.RH_SFTP_HOST

        except Exception as e:
            self.ui_log.info(
                "There was a problem while setting the "
                f"remote upload target:  {e}"
            )
        return f"{self.RH_API_HOST}{rh_case_api}"

    def _get_upload_https_auth(self):
        str_auth = f"Bearer {self._device_token}"
        return {'Authorization': str_auth}

    def _upload_https_post(self, archive, verify=True):
        """If upload_https() needs to use requests.post(), use this method.

        Policies should override this method instead of the base upload_https()

        :param archive:     The open archive file object
        """
        files = {
            'file': (archive.name.split('/')[-1], archive,
                     self._get_upload_headers())
        }
        # Get the access token at this point. With this,
        # we cover the cases where report generation takes
        # longer than the token timeout
        RHELAuth = DeviceAuthorizationClass(
                self.client_identifier_url,
                self.token_endpoint
            )
        self._device_token = RHELAuth.get_access_token()
        self.ui_log.info("Device authorized correctly. Uploading file to "
                         f"{self.get_upload_url_string()}")
        return requests.post(self.get_upload_url(), files=files,
                             headers=self._get_upload_https_auth(),
                             verify=verify, timeout=TIMEOUT_DEFAULT)

    def _get_upload_headers(self):
        if self.get_upload_url().startswith(self.RH_API_HOST):
            return {'isPrivate': 'false', 'cache-control': 'no-cache'}
        return {}

    def get_upload_url_string(self):
        if self.get_upload_url().startswith(self.RH_API_HOST):
            return "Red Hat Customer Portal"
        if self.get_upload_url().startswith(self.RH_SFTP_HOST):
            return "Red Hat Secure FTP"
        return self._get_obfuscated_upload_url(self.upload_url)

    def _get_sftp_upload_name(self):
        """The RH SFTP server will only automatically connect file uploads to
        cases if the filename _starts_ with the case number
        """
        fname = self.upload_archive_name.split('/')[-1]

        if self.commons['cmdlineopts'].case_id:
            fname = f"{self.commons['cmdlineopts'].case_id}_{fname}"
        if self.upload_directory:
            fname = os.path.join(self.upload_directory, fname)
        return fname

    # pylint: disable=too-many-branches
    def upload_sftp(self, user=None, password=None, user_dir=None):
        """Override the base upload_sftp to allow for setting an on-demand
        generated anonymous login for the RH SFTP server if a username and
        password are not given
        """
        if self.RH_SFTP_HOST.split('//')[1] not in self.get_upload_url():
            return super().upload_sftp()

        if not REQUESTS_LOADED:
            raise Exception("python3-requests is not installed and is required"
                            " for obtaining SFTP auth token.")
        _token = None
        _user = None

        # We may have a device token already if we attempted
        # to upload via http but the upload failed. So
        # lets check first if there isn't one.
        if not self._device_token:
            try:
                RHELAuth = DeviceAuthorizationClass(
                    self.client_identifier_url,
                    self.token_endpoint
                )
            except Exception as e:
                # We end up here if the user cancels the device
                # authentication in the web interface
                if "end user denied" in str(e):
                    self.ui_log.info(
                        "Device token authorization "
                        "has been cancelled by the user."
                    )
            else:
                self._device_token = RHELAuth.get_access_token()
        if self._device_token:
            self.ui_log.info("Device authorized correctly. Uploading file to"
                             f" {self.get_upload_url_string()}")

        url = self.RH_API_HOST + '/support/v2/sftp/token'
        ret = None
        if self._device_token:
            headers = self._get_upload_https_auth()
            ret = requests.post(url, headers=headers, timeout=10)
            if ret.status_code == 200:
                # credentials are valid
                _user = json.loads(ret.text)['username']
                _token = json.loads(ret.text)['token']
            else:
                self.ui_log.debug(
                    f"DEBUG: auth attempt failed (status: {ret.status_code}): "
                    f"{ret.json()}"
                )
                self.ui_log.error(
                    "Unable to retrieve Red Hat auth token using provided "
                    "credentials. Will try anonymous."
                )
        else:
            adata = {"isAnonymous": True}
            anon = requests.post(url, data=json.dumps(adata), timeout=10)
            if anon.status_code == 200:
                resp = json.loads(anon.text)
                _user = resp['username']
                _token = resp['token']
                self.ui_log.info(
                    _(f"User {_user} used for anonymous upload. Please inform "
                      f"your support engineer so they may retrieve the data.")
                )
            else:
                self.ui_log.debug(
                    f"DEBUG: anonymous request failed (status: "
                    f"{anon.status_code}): {anon.json()}"
                )
        if _user and _token:
            return super().upload_sftp(user=_user, password=_token,
                                       user_dir=_user)
        raise Exception("Could not retrieve valid or anonymous credentials")

    def check_file_too_big(self, archive):
        size = os.path.getsize(archive)
        # Lets check if the size is bigger than the limit.
        # There's really no need to transform the size to Gb,
        # so we don't need to call any size converter implemented
        # in tools.py
        if size >= self._max_size_request:
            self.ui_log.warning(
                _("Size of archive is bigger than Red Hat Customer Portal "
                  "limit for uploads of "
                  f"{convert_bytes(self._max_size_request)} "
                  " via sos http upload. \n")
                  )
            self.upload_url = self.RH_SFTP_HOST

    def upload_archive(self, archive):
        """Override the base upload_archive to provide for automatic failover
        from RHCP failures to the public RH dropbox
        """
        try:
            if self.get_upload_url().startswith(self.RH_API_HOST):
                self.check_file_too_big(archive)
            uploaded = super().upload_archive(archive)
        except Exception as e:
            uploaded = False
            if not self.upload_url.startswith(self.RH_API_HOST):
                raise
            self.ui_log.error(
                _(f"Upload to Red Hat Customer Portal failed due to "
                  f"{e}. Trying {self.RH_SFTP_HOST}")
                )
            self.upload_url = self.RH_SFTP_HOST
            uploaded = super().upload_archive(archive)
        return uploaded

# vim: set et ts=4 sw=4 :
