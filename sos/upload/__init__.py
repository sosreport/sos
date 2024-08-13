# Copyright 2024 Red Hat, Inc. Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import sys
from sos.component import SoSComponent
from sos import _sos as _
from sos import __version__


class SoSUpload(SoSComponent):
    """
    This class is designed to upload files to a distribution
    defined location. These files can be either sos reports,
    sos collections, or other kind of files like: vmcores,
    application cores, logs, etc.

    """

    desc = """
            Upload a file (can be a sos report, a must-gather, or others) to
             a distribution defined remote location
            """

    arg_defaults = {
        'upload_url': None,
        'upload_method': 'auto',
        'upload_no_ssl_verify': False,
        'upload_protocol': 'auto',
        'upload_file': '',
        'case_id': '',
        'upload_directory': None,
    }

    def __init__(self, parser, args, cmdline):
        # we are running `sos upload` directly
        # To Do: Work pending on hooking SoSReport or SoSCollector
        # to this subsystem
        super().__init__(parser, args, cmdline)

        # add manifest section for upload
        self.manifest.components.add_section('upload')

    @classmethod
    def add_parser_options(cls, parser):
        parser.usage = 'sos upload FILE [options]'
        upload_grp = parser.add_argument_group(
            'Upload Options',
            'These options control how upload manages files'
            )
        upload_grp.add_argument("upload_file", metavar="FILE",
                                help="The file or archive to upload")
        upload_grp.add_argument("--case-id", action="store", dest="case_id",
                                help="specify case identifier")
        upload_grp.add_argument("--upload-url", default=None,
                                help="Upload the archive to specified server")
        upload_grp.add_argument("--upload-user", default=None,
                                help="Username to authenticate with")
        upload_grp.add_argument("--upload-pass", default=None,
                                help="Password to authenticate with")
        upload_grp.add_argument("--upload-directory", action="store",
                                dest="upload_directory",
                                help="Specify upload directory for archive")
        upload_grp.add_argument("--upload-method", default='auto',
                                choices=['auto', 'put', 'post'],
                                help="HTTP method to use for uploading")
        upload_grp.add_argument("--upload-protocol", default='auto',
                                choices=['auto', 'https', 'ftp', 'sftp'],
                                help="Manually specify the upload protocol")
        upload_grp.add_argument("--upload-no-ssl-verify", default=False,
                                action='store_true',
                                help="Disable SSL verification for upload url")

    @classmethod
    def display_help(cls, section):
        section.set_title('SoS Upload Detailed Help')

        section.add_text(
            'The upload command is designed to upload already existing '
            'sos reports, as well as other files like logs and vmcores '
            'to a distribution specific location.'
        )

    def intro(self):
        """Print the intro message and prompts for a case ID if one is not
        provided on the command line
        """
        disclaimer = """\
This utility is used to upload files to a policy-default location.

The archive to be uploaded may contain data considered sensitive \
and its content should be reviewed by the originating \
organization before being passed to any third party.

No configuration changes will be made to the system running \
this utility.
"""
        self.ui_log.info(f"\nsos upload (version {__version__})")
        intro_msg = self._fmt_msg(disclaimer)
        self.ui_log.info(intro_msg)

        prompt = "\nPress ENTER to continue, or CTRL-C to quit\n"
        if not self.opts.batch:
            try:
                input(prompt)
                self.ui_log.info("")
            except KeyboardInterrupt:
                self._exit("Exiting on user cancel", 130)
            except Exception as e:
                self._exit(e, 1)

    def get_commons(self):
        return {
            'cmdlineopts': self.opts,
            'policy': self.policy,
            'case_id': self.opts.case_id,
            'upload_directory': self.opts.upload_directory
        }

    def execute(self):

        self.intro()
        archive = self.opts.upload_file
        self.policy.set_commons(self.get_commons())
        try:
            if os.stat(archive).st_size > 0:
                if os.path.isfile(archive):
                    try:
                        self.ui_log.info(
                            _(f"Attempting to upload file {archive} "
                                f"to case {self.opts.case_id}")
                        )

                        self.policy.upload_archive(archive)
                        self.ui_log.info(
                            _(f"File {archive} uploaded successfully")
                        )
                    except Exception as err:
                        self.ui_log.error(_(f"Upload attempt failed: {err}"))
                        sys.exit(1)
                else:
                    self.ui_log.error(_(f"{archive} is not a file."))
            else:
                self.ui_log.error(_(f"File {archive} is empty."))
        except Exception as e:
            self.ui_log.error(_(f"Cannot upload {archive}: {e} "))
