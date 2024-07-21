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
from datetime import datetime, timedelta

DEVICE_AUTH_CLIENT_ID = "sos-tools"
GRANT_TYPE_DEVICE_CODE = "urn:ietf:params:oauth:grant-type:device_code"

logger = logging.getLogger("sos")


class DeviceAuthorizationClass:
    """
    Device Authorization Class
    """

    def __init__(self, client_identifier_url, token_endpoint):

        self._access_token = None
        self._access_expires_at = None
        self.__device_code = None

        self.client_identifier_url = client_identifier_url
        self.token_endpoint = token_endpoint
        self._use_device_code_grant()

    def _use_device_code_grant(self):
        """
        Start the device auth flow. In the future we will
        store the tokens in an in-memory keyring.

        """

        self._request_device_code()
        print(
            "Please visit the following URL to authenticate this"
            f" device: {self._verification_uri_complete}"
        )
        self.poll_for_auth_completion()

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
                headers=headers)
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
                                                      data=token_data)

                status_code = check_auth_completion.status_code

                if status_code == 200:
                    logger.info("The SSO authentication is successful")
                    self._set_token_data(check_auth_completion.json())
                if status_code not in [200, 400]:
                    raise Exception(status_code, check_auth_completion.text)
                if status_code == 400 and \
                    check_auth_completion.json()['error'] not in \
                        ("authorization_pending", "slow_down"):
                    raise Exception(status_code, check_auth_completion.text)
            except requests.exceptions.RequestException as e:
                logger.error(f"Error was found while posting a request: {e}")

    def _set_token_data(self, token_data):
        """
        Set the class attributes as per the input token_data received.
        In the future we will persist the token data in a local,
        in-memory keyring, to avoid visting the browser frequently.
        :param token_data: Token data containing access_token, refresh_token
        and their expiry etc.
        """
        self._access_token = token_data.get("access_token")
        self._access_expires_at = datetime.utcnow() + \
            timedelta(seconds=token_data.get("expires_in"))
        self._refresh_token = token_data.get("refresh_token")
        self._refresh_expires_in = token_data.get("refresh_expires_in")
        if self._refresh_expires_in == 0:
            self._refresh_expires_at = datetime.max
        else:
            self._refresh_expires_at = datetime.utcnow() + \
                timedelta(seconds=self._refresh_expires_in)

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
            datetime.utcnow()

    def is_refresh_token_valid(self):
        """
        Check the validity of refresh_token. We are considering it invalid
        180 sec. prior to it's exact expiry time.

        :return: True/False

        """
        return self._refresh_token and self._refresh_expires_at and \
            self._refresh_expires_at - timedelta(seconds=180) > \
            datetime.utcnow()

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
                                          data=refresh_token_data)

        if refresh_token_res.status_code == 200:
            self._set_token_data(refresh_token_res.json())

        elif refresh_token_res.status_code == 400 and 'invalid' in\
                refresh_token_res.json()['error']:
            logger.warning("Problem while fetching the new tokens from refresh"
                           f" token grant - {refresh_token_res.status_code} "
                           f"{refresh_token_res.json()['error']}."
                           " New Device code will be requested !")
            self._use_device_code_grant()
        else:
            raise Exception(
                "Something went wrong while using the "
                "Refresh token grant for fetching tokens:"
                f" Returned status code {refresh_token_res.status_code}"
                f" and error {refresh_token_res.json()['error']}")
