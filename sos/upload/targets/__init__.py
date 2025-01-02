# Copyright 2024, Jake Hunsaker <jacob.r.hunsaker@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import getpass
import logging
import os

from inspect import getmembers, ismethod


class SoSUploadTarget:
    """
    This class abstracts destinations for upload into 'targets' that are more
    human-friendly for reference. An upload target will handle all necessary
    logic for uploading a given archive/file to the intended destination. The
    most common of targets will be to vendors that provide end-user support,
    and in those cases an upload target class should handle any necessary
    gating as well as authentication or filtering.

    By default, targets will attempt to determine a set of username/password
    credentials based off the following order:

        1. The setting of `--upload-user` and `--upload-pass` in either the
           commandline execution of sos or a given config file.
        2. The setting of the SOSUPLOADUSER and SOSUPLOADPASS env vars
        3. A prompt for user input, iff the target has set the
           `prompt_for_credentials` class var to `True`. This prompt will be
           skipped if `--batch` is set.

    The results of the credential prompt will be saved in
    `self.opts.upload_user` and `self.opts.upload_pass` respectively - this is
    done for consistency's sake. While subclasses are not required to use these
    values for their own credential operations, it is recommended.

    There is a hook mechanism for collecting user input at the _beginning_ of
    an sos execution, but not before upload. Any method with a name pattern of
    `prompt_for_*` will be executed to solicit user input.

    :cvar target_id:    The reference used by end-users to specify the target
                        to use via the `--target`/`--upload-target` option,
                        e.g. 'canonical'.
    :vartype target_id: ``str``

    :cvar target_name:  The more descriptive string users see in place of the
                        target_id value, e.g. 'Canonical Technical Support'.
    :vartype target_name:   ``str``

    :cvar target_protocols: The protocols the target may be enabled by based on
                            the protocol prefix of the destination url.
    :vartype target_protocols:  ``list``

    :cvar prompt_for_credentials: Should the target prompt for a username and
                                  password if one is not set by commandline,
                                  config file, or env var value? Default False.
    :vartype prompt_for_credentials: ``bool``
    """
    target_id = ''
    target_name = ''
    target_protocols = []
    prompt_for_credentials = False

    def __init__(self, options):
        self.opts = options
        self.soslog = logging.getLogger('sos')
        self.ui_log = logging.getLogger('sos_ui')
        self._get_upload_username()
        self._get_upload_password()
        self._handle_prompts_for_input()
        self.upload_file = self.opts.upload_file

    def _handle_prompts_for_input(self):
        """Find and execute any methods in an upload target that begin with
        `prompt_for_` so that those targets may collect whatever end user
        input is needed for the target. This method does not do any validation
        of the received inputs at all - that is for the target-specific methods
        to handle.
        """
        prompts = [
            (m[0], m[1]) for m in getmembers(self, predicate=ismethod)
            if m[0].startswith('prompt_for_')
        ]
        for prompt, pmethod in prompts:
            try:
                pmethod()
            except Exception as err:
                raise Exception(
                    f"Error while handling {prompt} prompt: {err}"
                ) from err

    def _get_upload_username(self):
        if self.opts.upload_user:
            return
        if _user := os.getenv('SOSUPLOADUSER', None):
            self.opts.upload_user = _user
        else:
            if not self.opts.batch and self.prompt_for_credentials:
                self.opts.upload_user = input(
                    f"Provide username for "
                    f"{self.target_name or self.opts.upload_url}: "
                )

    def _get_upload_password(self):
        if self.opts.upload_pass:
            return
        if _pass := os.getenv('SOSUPLOADPASS', None):
            self.opts.upload_pass = _pass
        else:
            if not self.opts.batch and self.prompt_for_credentials:
                self.opts.upload_pass = getpass.getpass(
                    f"Provide password for "
                    f"{self.opts.upload_user or 'authentication'}: "
                )

    def upload(self):
        raise NotImplementedError
