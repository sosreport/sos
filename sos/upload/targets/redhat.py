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
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urlparse

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
    RH_HYDRA_ATTACHMENTS_PATH = "/api/v1/hydra/support/attachments"

    def __init__(self, parser=None, args=None, cmdline=None):

        super().__init__(parser=parser, args=args, cmdline=cmdline)
        self._upload_session_details = {}

    RH_API_HOST = "https://api.access.redhat.com"
    RH_SFTP_HOST = "sftp://sftp.access.redhat.com"
    _upload_url = RH_SFTP_HOST
    _upload_method = 'post'
    _device_token = None
    # Max size for an http single request is 5Gb
    _max_size_request = 5368709120
    _chunk_size = 128 * 1024 * 1024  # 128 MiB
    # Uploads smaller than 5Gb can be processed
    # with one simple HTTP PUT request. Bigger
    # than 5Gb will need to be uploaded in chunks
    _upload_multipart = False
    _upload_thread_count = 4  # Default number of threads for multipart upload

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
        rh_case_api = self.RH_HYDRA_ATTACHMENTS_PATH
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

    def _build_abort_data(self):
        """Build the payload for aborting an upload session."""
        return {
            'attachmentId': self._upload_session_details.get('attachmentId'),
            'caseNumber': self.commons['cmdlineopts'].case_id,
            'uploadId': self._upload_session_details.get('uploadId')
        }

    def _abort_upload(self):
        """Cancel an ongoing upload."""
        abort_data = self._build_abort_data()
        base = f"{self.RH_API_HOST}{self.RH_HYDRA_ATTACHMENTS_PATH}"
        abort_url = f"{base}/upload/abort"
        self.ui_log.debug(
            f"Aborting upload: attachmentId="
            f"{abort_data.get('attachmentId')}, "
            f"uploadId={abort_data.get('uploadId')}")

        try:
            response_abort = requests.post(
                abort_url,
                headers=self._get_upload_https_auth(),
                json=abort_data,
                timeout=TIMEOUT_DEFAULT)
            if response_abort.status_code == 200:
                self.ui_log.info("Upload cancelled successfully.")
            else:
                self.ui_log.error(
                    "An error occurred while attempting to cancel upload: "
                    f"{response_abort.status_code}")
        except requests.exceptions.RequestException as e:
            self.ui_log.error(f"Error cancelling upload: {e}")

    def _complete_upload(self, complete_data):
        """Complete an upload session

        :param complete_data: Information about the upload session
        :returns: Response object on success, None on failure
        """
        base = f"{self.RH_API_HOST}{self.RH_HYDRA_ATTACHMENTS_PATH}"
        complete_url = f"{base}/upload/complete"
        self.ui_log.debug(
            "Completing upload: attachmentId="
            f"{complete_data.get('attachmentId')}, "
            f"parts={len(complete_data.get('parts', []))}")

        try:
            response_complete = requests.post(
                complete_url,
                headers=self._get_upload_https_auth(),
                json=complete_data,
                timeout=TIMEOUT_DEFAULT)
            if response_complete.status_code == 200:
                self.ui_log.info("Upload completed successfully.")
                return response_complete
            if response_complete.status_code == 400:
                self.ui_log.error(
                    "Upload completion rejected (400): "
                    f"{response_complete.text}")
            elif response_complete.status_code == 401:
                self.ui_log.error(
                    "Upload completion auth failed (401): "
                    f"{response_complete.text}")
            elif response_complete.status_code == 500:
                self.ui_log.error(
                    "S3 multipart completion failed (500): "
                    f"{response_complete.text}")
            else:
                self.ui_log.error(
                    "Upload completion failed "
                    f"({response_complete.status_code}): "
                    f"{response_complete.text}")
            return None
        except requests.exceptions.RequestException as e:
            self.ui_log.error("An exception occurred while "
                              f"completing upload: {e}")
            return None

    def _get_upload_session_details(self, archive, archive_size, total_chunks):
        """Get the details of the upload session like attachmentId,
        uploadStrategy, presigned URLs, and expiration time.
        Stores the result in self._upload_session_details.

        :param archive: The file object for the archive
        :param archive_size: Size of the archive in bytes
        :param total_chunks: Number of chunks for multipart (0 for simple)
        """
        # Let's reset session details before each attempt so that stale or
        # expired presigned URLs from a previous call are not reused
        # if this request fails and upload_archive retries.
        self._upload_session_details = {}

        data = {
            'caseNumber': self.commons['cmdlineopts'].case_id,
            'fileName': archive.name.split('/')[-1],
            'fileSize': archive_size,
            'totalChunks': total_chunks,
            'clientId': "sos-tools"
        }

        self.ui_log.debug(
            f"Requesting upload session: "
            f"file={data['fileName']}, "
            f"size={data['fileSize']}, "
            f"chunks={data['totalChunks']}")
        try:
            headers = self._get_upload_https_auth()
            base = f"{self.RH_API_HOST}{self.RH_HYDRA_ATTACHMENTS_PATH}"
            upload_url = f"{base}/upload"
            response = requests.post(
                upload_url,
                headers=headers,
                json=data,
                timeout=TIMEOUT_DEFAULT)
            self.ui_log.debug("Upload session response: "
                              f"{response.status_code}")
            status_code = response.status_code
            if status_code == 200:
                self._upload_session_details = response.json()
                details = self._upload_session_details
                self.ui_log.debug(
                    "Upload session initialized: "
                    f"attachmentId="
                    f"{details.get('attachmentId')}"
                    f", strategy="
                    f"{details.get('uploadStrategy')}"
                    f", parts="
                    f"{len(details.get('parts', []))}")
            else:
                self.ui_log.error(
                    f"Failed to initialize upload session: "
                    f"{status_code} {response.text}")
        except requests.exceptions.RequestException as e:
            self.ui_log.error(f"Error was found while posting a request: {e}")

    # Clarification: "part" refers to the S3/API concept (partNumber,
    # presignedUrl, parts in completion request). "Chunk" refers to
    # the local file splitting and upload tracking. They map 1:1 but
    # are kept distinct because the API contract may change
    # independently from our local chunking strategy.
    def get_file_chunks(self, archive_size, chunk_size):
        """Given a file, generate chunks for the multipart upload

        :param archive_size: The size of the archive we are dealing with
        :param chunk_size: The chunk size we are returning
        """
        part_number = 1
        offset = 0
        while offset < archive_size:
            size = min(chunk_size, archive_size - offset)
            yield {
                "part_number": part_number,
                "size": size,
                "offset": offset
            }
            offset += size
            part_number += 1

    def _upload_chunk(self, file_path, chunk_info, presigned_url,
                      max_retries=3):
        """Upload a single chunk

        :param file_path: The path to the file to upload
        :param chunk_info: Information about the chunk we are uploading
        :param presigned_url: Corresponding presigned URL to use for this chunk
        :param max_retries: Max number of retries in case of error
        """
        part_number = chunk_info["part_number"]
        size = chunk_info["size"]
        offset = chunk_info["offset"]
        # Timeout: at least TIMEOUT_DEFAULT, scaled for slow links (512 KiB/s)
        chunk_timeout = max(TIMEOUT_DEFAULT, size // (512 * 1024))
        etag = None
        for attempt in range(max_retries):
            try:
                with open(file_path, 'rb') as f:
                    f.seek(offset)
                    chunk_data = f.read(size)

                result = requests.put(presigned_url,
                                      data=chunk_data,
                                      headers={'Content-Type':
                                               'application/octet-stream'},
                                      timeout=chunk_timeout)
                if result.status_code == 200:
                    etag = result.headers.get("ETag", '').strip('"')
                    self.ui_log.debug(
                        f"Part {part_number} uploaded successfully")
                    return {"partNumber": part_number,
                            "ETag": etag,
                            "success": True}
                self.ui_log.warning(f"Part number {part_number} "
                                    "failed with status: "
                                    f"{result.status_code}.\n"
                                    f"Attempt {attempt+1}"
                                    f" of {max_retries}")
                if attempt < max_retries - 1:
                    backoff = 2 ** attempt
                    self.ui_log.info(
                        f"Part {part_number}: retrying in {backoff}s")
                    time.sleep(backoff)
            except requests.exceptions.RequestException as e:
                sanitized = str(e)
                try:
                    parsed = urlparse(presigned_url)
                    sanitized = sanitized.replace(
                        presigned_url,
                        f"{parsed.scheme}://{parsed.hostname}/***")
                except Exception as err:
                    self.ui_log.debug(
                        f"Could not sanitize presigned URL: {err}")
                self.ui_log.warning(f"Part {part_number} "
                                    f"failed with error {sanitized} "
                                    f"Attempt {attempt+1} of {max_retries} ")
                if attempt < max_retries - 1:
                    backoff = 2 ** attempt
                    self.ui_log.info(
                        f"Part {part_number}: retrying in {backoff}s")
                    time.sleep(backoff)
            # If we hit an I/O error, lets assume it's not a transient
            # one and immediately return after informing user
            except IOError as ioe:
                self.ui_log.error(f"Failed to read chunk {part_number}: {ioe}")
                return {"partNumber": part_number,
                        "ETag": None,
                        "success": False}

        # All retries failed
        self.ui_log.error(f"Upload of chunk {part_number} failed after "
                          f"{max_retries} attempts")
        return {"partNumber": part_number,
                "ETag": etag,
                "success": False}

    def multipart_upload(self, archive):
        """Manage the multipart upload for files exceeding _max_size_request.

        :param archive: The open archive file object
        :returns: Response object on success, None on failure
        """
        file_path = archive.name

        thread_count = getattr(
            self.commons.get('cmdlineopts', None),
            'upload_threads', self._upload_thread_count)
        self._upload_thread_count = thread_count

        # Calculate number of chunks for the multipart upload
        archive_size = os.path.getsize(file_path)
        total_chunks = ((archive_size + self._chunk_size - 1)
                        // self._chunk_size)

        self.ui_log.debug(
            f"Multipart upload parameters: "
            f"archive_size={archive_size}, "
            f"chunk_size={self._chunk_size}, "
            f"total_chunks={total_chunks}")
        self._get_upload_session_details(archive=archive,
                                         archive_size=archive_size,
                                         total_chunks=total_chunks)

        if not self._upload_session_details:
            self.ui_log.error("Failed to get upload session details.")
            return None

        # Get session metadata
        # The format of the upload session metadata is:
        # {
        # "attachmentId": "abcdefghijk-lmn1opq2",
        # "uploadStrategy": "MULTIPART",
        # "uploadId": "s3-multipart-upload-id",
        # "expirationTime": "2026-05-08T00:15:28.463915Z",
        # "parts": [
        #       { "partNumber": 1, "presignedUrl": "https://..." },
        #       { "partNumber": 2, "presignedUrl": "https://..." }
        #        ]
        # }
        attachment_id = self._upload_session_details.get('attachmentId')
        upload_id = self._upload_session_details.get('uploadId')
        presigned_parts = self._upload_session_details.get('parts', [])

        if len(presigned_parts) != total_chunks:
            self.ui_log.error(
                f"Presigned URL count mismatch: expected {total_chunks}, "
                f"got {len(presigned_parts)}")
            self._abort_upload()
            return None

        # Map of part_number to presigned_url
        presigned_urls = {
            part['partNumber']: part['presignedUrl']
            for part in presigned_parts
        }

        expiration = None
        expiration_str = self._upload_session_details.get('expirationTime')
        if expiration_str:
            try:
                # Python 3.11+ handles 'Z' natively, any distribution
                # that uses a version before this one will not work with
                # this, so let's amend it
                expiration = datetime.fromisoformat(
                    expiration_str.replace('Z', '+00:00'))
            except (ValueError, TypeError) as e:
                self.ui_log.warning(
                    f"Could not parse expirationTime "
                    f"'{expiration_str}': {e}")

        if expiration and datetime.now(timezone.utc) >= expiration:
            self.ui_log.error(
                "Upload session already expired "
                f"(expired at {expiration_str}).")
            self._abort_upload()
            return None

        # Get chunk info
        chunks = list(self.get_file_chunks(
            archive_size=archive_size,
            chunk_size=self._chunk_size))

        # Initialize lists of chunks for upload
        uploaded_chunks = []
        failed_chunks = []

        self.ui_log.info(
            f"Starting multipart upload: {total_chunks} chunks with "
            f"{self._upload_thread_count} threads."
        )

        executor = ThreadPoolExecutor(max_workers=self._upload_thread_count)
        try:
            future_to_chunk = {}
            for chunk_info in chunks:
                part_num = chunk_info['part_number']
                presigned_url = presigned_urls.get(part_num)
                if not presigned_url:
                    self.ui_log.error(
                        f"No presigned URL for part {part_num}")
                    failed_chunks.append(chunk_info)
                    continue

                future = executor.submit(
                    self._upload_chunk,
                    file_path,
                    chunk_info,
                    presigned_url
                )

                future_to_chunk[future] = chunk_info

            # Process completed uploads
            completed = 0
            for future in as_completed(future_to_chunk):
                chunk_info = future_to_chunk[future]
                try:
                    result = future.result()
                    if result and result.get("success"):
                        uploaded_chunks.append({
                            'partNumber': result['partNumber'],
                            'eTag': result['ETag']
                        })
                        completed += 1
                        self.ui_log.info(
                            f"Progress: {completed}/"
                            f"{total_chunks} chunks "
                            "uploaded")
                    else:
                        failed_chunks.append(chunk_info)
                except Exception as e:
                    self.ui_log.error(
                        f"Unexpected error while uploading chunk: {e}")
                    failed_chunks.append(chunk_info)

                if (expiration
                        and completed < total_chunks
                        and datetime.now(timezone.utc) >= expiration):
                    self.ui_log.error(
                        "Upload session expired during upload "
                        f"(expired at {expiration_str}). "
                        f"{completed}/{total_chunks} chunks "
                        "uploaded before expiration.")
                    self._abort_upload()
                    return None
        except KeyboardInterrupt:
            self.ui_log.warning("Upload interrupted by user.")
            self._abort_upload()
            return None
        finally:
            try:
                executor.shutdown(wait=False)
            except Exception as e:
                self.ui_log.debug(
                    f"Error during executor shutdown: {e}")

        # Check upload results
        if failed_chunks:
            self.ui_log.error(
                f"Upload incomplete: {len(failed_chunks)} chunks failed."
            )
            for chunk in failed_chunks:
                self.ui_log.error(
                    f"Failed chunk {chunk['part_number']}: "
                    f"offset {chunk['offset']}, size {chunk['size']}"
                )
            self._abort_upload()
            return None

        uploaded_chunks.sort(key=lambda x: x['partNumber'])

        # Prepare the data about the completion
        complete_data = {
            'attachmentId': attachment_id,
            'caseNumber': self.commons['cmdlineopts'].case_id,
            'uploadId': upload_id,
            'parts': uploaded_chunks
        }

        return self._complete_upload(complete_data)

    def simple_http_upload(self, archive, verify=True):
        """Simple request http upload. This is used for files that
        have a size less than _max_size_request.

        We don't need to call _complete_upload in this case:
        the server auto-completes simple (non-multipart) uploads.
        The complete/abort lifecycle only applies to multipart
        uploads for files exceeding _max_size_request.

        :param archive: The open archive file object
        :param verify: Whether to verify SSL certificates
        :returns: Response object on success, None on failure
        """
        archive_size = os.path.getsize(archive.name)
        self.ui_log.debug(
            f"Simple upload: file={archive.name.split('/')[-1]}, "
            f"size={archive_size}")
        self._get_upload_session_details(archive=archive,
                                         archive_size=archive_size,
                                         total_chunks=0)
        if self._upload_session_details:
            presigned_url = self._upload_session_details.get("presignedUrl")
            if not presigned_url:
                self.ui_log.error(
                        "No presigned URL in upload session response")
                return None
            # Sanitize presigned URL before logging to avoid exposing
            # temporary credentials and path identifiers in sos logs.
            # We still log the scheme and hostname to provide enough
            # data in debug output to diagnose upload issues.
            parsed_url = urlparse(presigned_url)
            self.ui_log.debug(
                f"Uploading to URL: {parsed_url.scheme}://"
                f"{parsed_url.hostname}/***")
            # The API requires simple uploads for files under 5 GB,
            # multipart is not an option. Large files near the limit may
            # still be slow on constrained links — monitor for timeouts.
            upload_timeout = max(
                TIMEOUT_DEFAULT, archive_size // (512 * 1024))
            try:
                response = requests.put(presigned_url, data=archive,
                                        headers={'Content-Type':
                                                 'application/octet-stream'},
                                        verify=verify,
                                        timeout=upload_timeout)
            except requests.exceptions.RequestException as e:
                self.ui_log.error(
                    f"Simple upload failed with error: {e}")
                return None
            self.ui_log.info(f"Response status: {response.status_code}")
            return response
        self.ui_log.error(
            "Error while trying to start the upload session."
        )
        return None

    def _upload_https_post(self, archive, verify=True):
        """If upload_https() needs to use requests.post(), use this method.

        Policies should override this method instead of the base upload_https()

        :param archive:     The open archive file object
        """
        # Get the access token at this point. With this,
        # we cover the cases where report generation takes
        # longer than the token timeout
        RHELAuth = DeviceAuthorizationClass(
                self.client_identifier_url,
                self.token_endpoint,
                Path.home()
            )
        self._device_token = RHELAuth.get_access_token()
        self.ui_log.info("Device authorized correctly. Uploading file to "
                         f"{self.get_upload_url_string()}")

        strategy = 'multipart' if self._upload_multipart \
            else 'simple'
        self.ui_log.debug(
            f"Upload strategy: {strategy}")
        archive_size = os.path.getsize(archive.name)
        if self._upload_multipart:
            thread_count = self._upload_thread_count
            self.ui_log.info(
                f"Upload will split the {convert_bytes(archive_size)} "
                f"report into multiple parts and send {thread_count} "
                f"chunk(s) in parallel"
            )
            response = self.multipart_upload(archive=archive)
        else:
            self.ui_log.info(
                f"Uploading {convert_bytes(archive_size)} report in a "
                f"single request"
            )
            response = self.simple_http_upload(archive=archive, verify=verify)
        if response is None:
            raise Exception(
                f"Failed to complete the {strategy} upload of "
                f"{convert_bytes(archive_size)} archive {archive.name}"
            )
        return response

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
        """Override the base upload_sftp to allow for checking if a
        device token already exists and generating if needed.
        """
        if self.RH_SFTP_HOST.split('//')[1] not in self.get_upload_url():
            return super().upload_sftp()

        if not REQUESTS_LOADED:
            raise Exception("python3-requests is not installed and is required"
                            " for obtaining SFTP auth token.")
        _token = None
        _user = None
        _user_dir = None

        # We may have a device token already if we attempted
        # to upload via http but the upload failed. So
        # lets check first if there isn't one.
        if not self._device_token:
            try:
                RHELAuth = DeviceAuthorizationClass(
                    self.client_identifier_url,
                    self.token_endpoint,
                    Path.home()
                )
            except Exception as e:
                # We end up here if the user cancels the device
                # authentication in the web interface
                if "end user denied" in str(e):
                    self.ui_log.info(
                        "Device token authorization failed or "
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
                _user_dir = f"/users/{_user}"
            else:
                self.ui_log.debug(
                    f"DEBUG: auth attempt failed (status: {ret.status_code}): "
                    f"{ret.json()}"
                )
                self.ui_log.error(
                    "Unable to retrieve Red Hat auth token using provided "
                    "credentials."
                )
        else:
            self.ui_log.debug(
                "DEBUG: Authentication failed or cancelled by user. "
                "Anonymous upload no longer allowed."
            )
        if _user and _token:
            return super().upload_sftp(user=_user, password=_token,
                                       user_dir=_user_dir)
        raise Exception("Could not retrieve valid credentials. "
                        "Upload cancelled.")

    def check_file_too_big(self, archive):
        size = os.path.getsize(archive)
        # Lets check if the size is bigger than the limit.
        # There's really no need to transform the size to Gb,
        # so we don't need to call any size converter implemented
        # in tools.py
        if size >= self._max_size_request:
            self.ui_log.debug(
                _("Size of archive is bigger than Red Hat Customer Portal "
                  "limit for simple uploads of "
                  f"{convert_bytes(self._max_size_request)}. "
                  "Using multi-part upload.\n")
                  )
            self._upload_multipart = True

    def upload_archive(self, archive):
        """Override the base upload_archive to provide for automatic failover
        from RHCP failures to the public RH dropbox
        """
        self._upload_multipart = False
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
