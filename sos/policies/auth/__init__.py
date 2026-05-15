# Copyright (C) 2023 Red Hat, Inc., Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import logging
try:
    import requests
    REQUESTS_LOADED = True
except ImportError:
    REQUESTS_LOADED = False
import time
from datetime import datetime, timedelta, timezone
import os
import json

from sos.utilities import TIMEOUT_DEFAULT, path_join

DEVICE_AUTH_CLIENT_ID = "sos-tools"
GRANT_TYPE_DEVICE_CODE = "urn:ietf:params:oauth:grant-type:device_code"
OIDC_TOKEN_FILE = ".sos-redhat-oidc-token.json"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class DeviceAuthorizationClass:
    """
    Device Authorization Class
    """

    def __init__(self, client_identifier_url, token_endpoint, token_dir):

        self._access_token = None
        self._access_expires_at = None
        self.__device_code = None
        self._token_dir = f"{token_dir}/"

        self.client_identifier_url = client_identifier_url
        self.token_endpoint = token_endpoint
        self.ui_log = logging.getLogger('sos_ui')
        self._use_device_code_grant()

    def try_read_refresh_token(self, base_path):
        """
        Try to read locally stored refresh token

        Args:
            base_path (str): Local path where OIDC token is stored

        Returns:
            str: Returns OIDC refresh token information if found,
            otherwise None
        """
        token_file_path = path_join(base_path, OIDC_TOKEN_FILE)
        if not os.path.exists(token_file_path):
            self.ui_log.info("Cannot find "
                             f"{OIDC_TOKEN_FILE} file using {base_path} "
                             "path, so we'll request a new token.")
            return None

        self.ui_log.info("Retrieving OIDC token information from local "
                         f"{OIDC_TOKEN_FILE} file")
        try:
            with open(token_file_path, "r", encoding='utf-8') as fileobj:
                read_in = fileobj.read()
        except OSError as err:
            self.ui_log.error("There was an exception while reading "
                              f"the token file - {err}")
            raise

        if not read_in.strip():
            self.ui_log.info(f"The {OIDC_TOKEN_FILE} file was empty.")
            return None

        try:
            token_data = json.loads(read_in)
        except json.JSONDecodeError:
            self.ui_log.error("There was an issue decoding the JSON file "
                              f"while loading {OIDC_TOKEN_FILE}")
            os.remove(f"{token_file_path}")
            return None

        refresh_token = token_data.get("refresh_token")
        dt_str = token_data.get("refresh_expires_at")
        if not refresh_token or not dt_str:
            self.ui_log.error(
                "Locally cached offline token is missing required fields "
                f"in {OIDC_TOKEN_FILE}. We will request a new token."
            )
            os.remove(f"{token_file_path}")
            return None

        try:
            refresh_expires_at = datetime.strptime(dt_str, DATETIME_FORMAT)
            refresh_expires_at = refresh_expires_at.replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            self.ui_log.error(
                f"Invalid refresh_expires_at in {OIDC_TOKEN_FILE}: "
                f"{dt_str!r}"
            )
            os.remove(f"{token_file_path}")
            return None

        if refresh_expires_at - timedelta(seconds=300) <= \
                datetime.now(timezone.utc):
            self.ui_log.error("Locally cached offline token has expired. "
                              "We will remove the old file and"
                              " request a new token.")
            os.remove(f"{token_file_path}")
            return None

        return refresh_token

    def _use_device_code_grant(self, force=False):
        """
        Start the device auth flow.
        """
        stored_refresh_token = None if force else \
            self.try_read_refresh_token(self._token_dir)
        if force or not stored_refresh_token:
            self._request_device_code()
            self.ui_log.info(
                "Please visit the following URL to authenticate this"
                f" device: {self._verification_uri_complete}"
            )
            self.poll_for_auth_completion()
        else:
            self._use_refresh_token_grant(stored_refresh_token)

    def _request_device_code(self):
        """
        Initialize new Device Authorization Grant attempt by
        requesting a new device code.

        """
        data = f"client_id={DEVICE_AUTH_CLIENT_ID}"
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        if not REQUESTS_LOADED:
            raise Exception("python3-requests is not installed and is required"
                            " for obtaining device auth token.")
        try:
            res = requests.post(
                self.client_identifier_url,
                data=data,
                headers=headers,
                timeout=TIMEOUT_DEFAULT)
            res.raise_for_status()
            response = res.json()
            self._user_code = response.get("user_code")
            self._verification_uri = response.get("verification_uri")
            self._interval = response.get("interval")
            self.__device_code = response.get("device_code")
            self._verification_uri_complete = response.get(
                "verification_uri_complete")
        except requests.HTTPError as e:
            raise requests.HTTPError("HTTP request failed "
                                     "while attempting to acquire the tokens."
                                     f"Error returned was {res.status_code} "
                                     f"{e}")

    def poll_for_auth_completion(self):
        """
        Continuously poll OIDC token endpoint until the user is successfully
        authenticated or an error occurs.

        """
        token_data = {'grant_type': GRANT_TYPE_DEVICE_CODE,
                      'client_id': DEVICE_AUTH_CLIENT_ID,
                      'device_code': self.__device_code}

        if not REQUESTS_LOADED:
            raise Exception("python3-requests is not installed and is required"
                            " for obtaining device auth token.")
        while self._access_token is None:
            time.sleep(self._interval)
            try:
                check_auth_completion = requests.post(self.token_endpoint,
                                                      data=token_data,
                                                      timeout=TIMEOUT_DEFAULT)

                status_code = check_auth_completion.status_code

                if status_code == 200:
                    self.ui_log.info("The SSO authentication is successful")
                    self._set_token_data(check_auth_completion.json())
                if status_code not in [200, 400]:
                    raise Exception(status_code, check_auth_completion.text)
                if status_code == 400 and \
                    check_auth_completion.json()['error'] not in \
                        ("authorization_pending", "slow_down"):
                    raise Exception(status_code, check_auth_completion.text)
            except requests.exceptions.RequestException as e:
                self.ui_log.error("An error was found while posting a request:"
                                  f" {e}")

    def _set_token_data(self, token_data):
        """
        Set the class attributes as per the input token_data received.

        :param token_data: Token data containing access_token, refresh_token
        and their expiry etc.
        """
        self._access_token = token_data.get("access_token")
        self._access_expires_at = datetime.now(timezone.utc) + \
            timedelta(seconds=token_data.get("expires_in"))
        self._refresh_token = token_data.get("refresh_token")
        self._refresh_expires_in = token_data.get("refresh_expires_in")
        if self._refresh_expires_in == 0:
            self._refresh_expires_at = datetime.max
        else:
            self._refresh_expires_at = datetime.now(timezone.utc) + \
                timedelta(seconds=self._refresh_expires_in)
        self.persist_refresh_token(self._token_dir)
        self.ui_log.info(f"Token data stored in: {self._token_dir}")

    def get_access_token(self):
        """
        Get the valid access_token at any given time.
        :return: Access_token
        :rtype: string
        """
        if self.is_access_token_valid():
            return self._access_token
        if self.is_refresh_token_valid():
            self._use_refresh_token_grant()
            return self._access_token
        self._use_device_code_grant()
        return self._access_token

    def is_access_token_valid(self):
        """
        Check the validity of access_token. We are considering it invalid 180
        sec. prior to it's exact expiry time.
        :return: True/False

        """
        return self._access_token and self._access_expires_at and \
            self._access_expires_at - timedelta(seconds=180) > \
            datetime.now(timezone.utc)

    def is_refresh_token_valid(self):
        """
        Check the validity of refresh_token. We are considering it invalid
        180 sec. prior to it's exact expiry time.

        :return: True/False

        """
        return self._refresh_token and self._refresh_expires_at and \
            self._refresh_expires_at - timedelta(seconds=180) > \
            datetime.now(timezone.utc)

    def _use_refresh_token_grant(self, refresh_token=None):
        """
        Fetch the new access_token and refresh_token using the existing
        refresh_token and persist it.
        :param refresh_token: optional param for refresh_token

        """
        if not REQUESTS_LOADED:
            raise Exception("python3-requests is not installed and is required"
                            " for obtaining device auth token.")
        refresh_token_data = {'client_id': DEVICE_AUTH_CLIENT_ID,
                              'grant_type': 'refresh_token',
                              'refresh_token': self._refresh_token if not
                              refresh_token else refresh_token}

        refresh_token_res = requests.post(self.token_endpoint,
                                          data=refresh_token_data,
                                          timeout=TIMEOUT_DEFAULT)
        try:
            refresh_token_res_json = refresh_token_res.json()
        except ValueError:
            refresh_token_res_json = {}

        if refresh_token_res.status_code == 200:
            self._set_token_data(refresh_token_res_json)

        elif refresh_token_res.status_code == 400 and 'invalid' in\
                (refresh_token_res_json.get('error') or ''):
            self.ui_log.warning("Problem while fetching the new tokens "
                                f"from refresh token grant "
                                f"- {refresh_token_res.status_code} "
                                f"{refresh_token_res_json.get('error')}."
                                " New Device code will be requested!")
            token_file_path = path_join(self._token_dir, OIDC_TOKEN_FILE)
            try:
                os.remove(token_file_path)
            except FileNotFoundError:
                self.ui_log.warning(
                    "Cached token file was not found while attempting to "
                    f"remove it: {token_file_path}"
                )
            except OSError as err:
                self.ui_log.warning(
                    "Unable to remove invalid cached token file "
                    f"{token_file_path}: {err}"
                )
            self._use_device_code_grant(force=True)
        else:
            raise Exception(
                "Something went wrong while using the "
                "Refresh token grant for fetching tokens:"
                f" Returned status code {refresh_token_res.status_code}"
                f" and error {refresh_token_res_json.get('error')}")

    def persist_refresh_token(self, base_path):
        """
        Persist current refresh token to a local file
        Args:
            base_path (str): Local path to a directory where token
            should be stored

        Returns:
            bool: True if refresh token was successfully persisted,
            otherwise False
        """
        if self.is_refresh_token_valid():
            # ToDo: While now we'll use the user's home directory
            # in the future we may want to offer the possibility
            # of specifying the directory (making sure the user knows
            # the security implications of this decision)
            if not os.path.exists(base_path):
                os.mkdir(base_path)
            token_data = {
                "refresh_token": self._refresh_token,
                "refresh_expires_at": self._refresh_expires_at.strftime(
                    DATETIME_FORMAT
                    )
            }
            token_file_path = path_join(base_path, OIDC_TOKEN_FILE)
            fd = os.open(
                token_file_path,
                os.O_CREAT | os.O_WRONLY | os.O_TRUNC,
                0o600,
            )
            with os.fdopen(fd, 'w', encoding='utf-8') as fileobj:
                json.dump(token_data, fileobj)
            os.chmod(token_file_path, 0o600)
            self.ui_log.info("The new refresh token was successfully saved to"
                             f" {token_file_path}")
            return True
        self.ui_log.error("Cannot save invalid refresh token")
        return False

# vim: set et ts=4 sw=4 :
