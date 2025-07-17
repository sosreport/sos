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
import logging
import inspect
import importlib

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

    desc = """Upload a file to a user or policy defined remote location"""

    arg_defaults = {
        'upload_file': '',
        'case_id': '',
        'low_priority': False,
        'upload_url': None,
        'upload_directory': None,
        'upload_user': None,
        'upload_pass': None,
        'upload_method': 'auto',
        'upload_no_ssl_verify': False,
        'upload_protocol': 'auto',
        'upload_s3_endpoint': 'https://s3.amazonaws.com',
        'upload_s3_region': None,
        'upload_s3_bucket': None,
        'upload_s3_access_key': None,
        'upload_s3_secret_key': None,
        'upload_s3_object_prefix': None,
        'upload_target': None
    }

    def __init__(self, parser=None, args=None, cmdline=None, in_place=False,
                 hook_commons=None, archive=None):
        if not in_place:
            # we are running `sos upload` directly
            super().__init__(parser, args, cmdline)
            self.from_cmdline = True
        else:
            # we are being hooked by either SoSReport or SoSCollector, don't
            # re-init everything as that will cause issues, but instead load
            # the needed bits from the calling component
            self.opts = hook_commons['options']
            self.policy = hook_commons['policy']
            self.manifest = hook_commons['manifest']
            self.parser = parser
            self.cmdline = cmdline
            self.args = args
            self._upload_file = archive

            self.ui_log = logging.getLogger('sos_ui')
            self.from_cmdline = False
            self.archive = archive
        self.upload_targets = self.load_upload_targets()
        self.upload_target = None

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
        upload_grp.add_argument("--upload-s3-endpoint", default=None,
                                help="Endpoint to upload to for S3 bucket")
        upload_grp.add_argument("--upload-s3-region", default=None,
                                help="Region to upload to for S3 bucket")
        upload_grp.add_argument("--upload-s3-bucket", default=None,
                                help="Name of the S3 bucket to upload to")
        upload_grp.add_argument("--upload-s3-access-key", default=None,
                                help="Access key for the S3 bucket")
        upload_grp.add_argument("--upload-s3-secret-key", default=None,
                                help="Secret key for the S3 bucket")
        upload_grp.add_argument("--upload-s3-object-prefix", default=None,
                                help="Prefix for the S3 object/key")
        upload_grp.add_argument("--upload-method", default='auto',
                                choices=['auto', 'put', 'post'],
                                help="HTTP method to use for uploading")
        upload_grp.add_argument("--upload-protocol", default='auto',
                                choices=['auto', 'https', 'ftp', 'sftp', 's3'],
                                help="Manually specify the upload protocol")
        upload_grp.add_argument("--upload-no-ssl-verify", default=False,
                                action='store_true',
                                help="Disable SSL verification for upload url")
        upload_grp.add_argument("--upload-target", default='local',
                                choices=[
                                    'redhat',
                                    'canonical',
                                    'generic',
                                    'local'],
                                help=("Manually specify vendor-specific "
                                      "target for uploads. Supported "
                                      "options are:\n"
                                      "redhat, canonical, "
                                      "generic, local"))

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
This utility is used to upload files to a target location \
based either on a command line option or detecting the local \
distribution.

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

    def set_commons(self, commons):
        """Set common host data for the Upload targets
            to reference
        """
        self.commons = commons

    def determine_upload_target(self):
        """This sets the upload target and loads that target's options.

        If no upload target is matched and no target is provided by
        the user, then we abort.

        If an upload target is provided in the command line,
        this will not run.
        """
        checks = list(self.upload_targets.values())
        for upload_target in self.upload_targets.values():
            checks.remove(upload_target)
            if upload_target.check_distribution():
                cname = upload_target.__class__.__name__
                self.ui_log.debug(f"Installation matches {cname}, checking for"
                                  " upload targets")
                self.upload_target = upload_target
                self.upload_name = upload_target.name()
        if not self.upload_target:
            self.upload_target = self.upload_targets["generic"]
            self.upload_name = self.upload_target.name()
        self.ui_log.info(
                    f"Upload target set to {self.upload_name}")

    def load_upload_targets(self):
        """Loads all upload targets supported by the local installation
        """
        import sos.upload.targets
        supported_upload_tgts = {}
        for upload_target in self._load_modules(sos.upload.targets, 'targets'):
            target_class = upload_target[1](
                            parser=self.parser,
                            args=self.args,
                            cmdline=self.cmdline
                            )
            target_class.set_commons(self.get_commons())
            supported_upload_tgts[target_class.get_target_id()] = target_class
        return supported_upload_tgts

    @classmethod
    def _load_modules(cls, package, submod):
        """Helper to import upload targets"""
        modules = []
        for path in package.__path__:
            if os.path.isdir(path):
                modules.extend(cls._find_modules_in_path(path, submod))
        return modules

    @classmethod
    def _find_modules_in_path(cls, path, modulename):
        """Given a path and a module name, find everything that can be imported
        and then import it

            path - the filesystem path of the package
            modulename - the name of the module in the package

        E.G. a path of 'targets', and a modulename of 'redhat' equates to
        importing sos.upload.targets.redhat
        """
        modules = []
        if os.path.exists(path):
            for pyfile in sorted(os.listdir(path)):
                if not pyfile.endswith('.py'):
                    continue
                if '__' in pyfile:
                    continue
                fname, _ = os.path.splitext(pyfile)
                modname = f'sos.upload.{modulename}.{fname}'
                modules.extend(cls._import_modules(modname))
        return modules

    @classmethod
    def _import_modules(cls, modname):
        """Import and return all found classes in a module"""
        module = importlib.import_module(modname)
        modules = [
            (name, cls)
            for name, cls in inspect.getmembers(module, inspect.isclass)
            if cls.__module__.startswith("sos.upload.targets")
        ]
        return modules

    def pre_work(self):
        # This method will be called before upload begins
        self.commons = self.get_commons()
        cmdline_opts = self.commons['cmdlineopts']

        if cmdline_opts.low_priority:
            self.policy._configure_low_priority()

    def execute(self):
        try:
            self.pre_work()
            if self.from_cmdline:
                self.intro()
                self.archive = self.opts.upload_file
                self.caseid = self.policy.prompt_for_case_id(
                    cmdline_opts=self.opts
                )
            cmdline_target = self.opts.upload_target
            if cmdline_target and cmdline_target != 'local':
                self.upload_target = self.upload_targets[cmdline_target]
            else:
                self.determine_upload_target()
            if not self.upload_target:
                # There was no upload target set, so we'll throw
                # an error here and exit
                self.ui_log.error(
                    "No upload target set via command line options or"
                    " autodetected.\n"
                    "Please specify one using the option --upload-target.\n"
                    "Exiting."
                )
                sys.exit(1)
            self.upload_target.pre_work(self.get_commons())
            try:
                if os.stat(self.archive).st_size > 0:
                    if os.path.isfile(self.archive):
                        try:
                            self.upload_target.upload_archive(self.archive)
                            self.ui_log.info(
                                _(f"File {self.archive} uploaded successfully")
                            )
                        except Exception as err:
                            self.ui_log.error(_(
                                f"Upload attempt failed: {err}"))
                            sys.exit(1)
                    else:
                        self.ui_log.error(_(f"{self.archive} is not a file."))
                else:
                    self.ui_log.error(_(f"File {self.archive} is empty."))
            except Exception as e:
                self.ui_log.error(_(f"Cannot upload {self.archive}: {e} "))
        except KeyboardInterrupt:
            self._exit("Exiting on user cancel", 130)


# vim: set et ts=4 sw=4 :
