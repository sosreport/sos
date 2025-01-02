# Copyright 2024, Jake Hunsaker <jacob.r.hunsaker@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


import inspect
import os

from sos.component import SoSComponent
from sos.utilities import fmt_msg
from sos import __version__


class SoSUpload(SoSComponent):
    """
    The upload component is used to provide a mechanism by which users can
    upload sos archives, or other support-relevant data, to a known support
    vendor or other location.

    Users may invoke this either directly with `sos upload`, or in-line when
    generating a report or collector archive via the `--upload` option.

    By default, the upload target will be chosen based on the local system's
    distribution (e.g. a RHEL system will default to uploading to Red Hat's
    customer support portal) but may be directed to another location based on
    user configuration.
    """

    desc = 'Upload an archive or other data to a specified location or vendor'

    configure_logging = True
    load_probe = True
    upload_target = None

    arg_defaults = {
        'upload_file': None,
        'upload_url': None,
        'upload_port': None,
        'upload_directory': None,
        'upload_user': None,
        'upload_pass': None,
        'upload_http_method': 'put',
        'upload_no_ssl_verify': False,
        'upload_target': None,
        'upload_s3_endpoint': None,
        'upload_s3_region': None,
        'upload_s3_bucket': None,
        'upload_s3_access_key': None,
        'upload_s3_secret_key': None,
        'upload_s3_object_prefix': None
    }

    def __init__(self, parser, parsed_args, cmdline_args, commons=None):
        super().__init__(parser, parsed_args, cmdline_args)
        _do_intro = True
        if commons:
            _do_intro = False
            self.opts = commons['opts']
            self.policy = commons['policy']
        if _do_intro:
            self._intro()
        self.set_upload_target()
        if self.opts.upload_file:
            self.upload_file = self.opts.upload_file

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

        E.G. a path of 'clusters', and a modulename of 'ovirt' equates to
        importing sos.collector.clusters.ovirt
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
        mod_short_name = modname.split('.')[2]
        try:
            module = __import__(modname, globals(), locals(), [mod_short_name])
        except ImportError as e:
            print(f'Error while trying to load module {modname}: '
                  f' {e.__class__.__name__}')
            raise e
        modules = inspect.getmembers(module, inspect.isclass)
        for mod in modules.copy():
            if mod[0] in ('SoSUploadTarget', ):
                modules.remove(mod)
        return modules

    def _load_targets(self):
        import sos.upload.targets
        package = sos.upload.targets
        supported_targets = {}
        targets = self._load_modules(package, 'targets')
        for target in targets:
            _name = target[0].lower().replace('upload', '')
            supported_targets[_name] = target[1]
        return supported_targets

    @classmethod
    def add_parser_options(cls, parser):
        parser.usage = 'sos upload FILE [options]'
        upload_grp = parser.add_argument_group(
            'Upload options',
            'These options affect archive uploading'
        )

        upload_grp.add_argument('upload_file', metavar='FILE',
                                help='Path to the file to upload. REQUIRED.')
        upload_grp.add_argument('--target', '--upload-target',
                                dest='upload_target',
                                help=('target to use for uploads, defaults to '
                                      'distribution vendor')
                                )
        upload_grp.add_argument('--upload-url',
                                help='The destination url or API endpoint to '
                                     'upload to')
        upload_grp.add_argument('--upload-port', type=int, default=0,
                                help='Port to use for uploads, particularly '
                                     'sftp uploads')
        upload_grp.add_argument("--upload-directory", default=None,
                                help="Specify upload directory for archive")
        upload_grp.add_argument("--upload-user", default=None,
                                help="Username to authenticate with")
        upload_grp.add_argument("--upload-pass", default=None,
                                help="Password to authenticate with")
        upload_grp.add_argument("--upload-http-method", default='put',
                                choices=['put', 'post'],
                                help="HTTP method to use for uploading")
        upload_grp.add_argument("--upload-no-ssl-verify", default=False,
                                action='store_true',
                                help="Disable SSL verification for upload url"
                                )
        upload_grp.add_argument("--upload-s3-endpoint", default=None,
                                help="Endpoint to upload to for S3 bucket")
        upload_grp.add_argument("--upload-s3-region", default=None,
                                help="Region for the S3 bucket")
        upload_grp.add_argument("--upload-s3-bucket", default=None,
                                help="Name of the S3 bucket to upload to")
        upload_grp.add_argument("--upload-s3-access-key", default=None,
                                help="Access key for the S3 bucket")
        upload_grp.add_argument("--upload-s3-secret-key", default=None,
                                help="Secret key for the S3 bucket")
        upload_grp.add_argument("--upload-s3-object-prefix", default=None,
                                help="Prefix for the S3 object/key")

    def set_upload_target(self):
        """
        Set the target destination for where we're uploading to. If none of the
        various upload options are set, default to determining the target based
        on the policy that is loaded.
        """
        if self.opts.upload_target:
            _target = self._get_target_from_id(self.opts.upload_target)
        elif self.opts.upload_url or self.opts.upload_s3_endpoint:
            _target = self._get_target_from_url()
        else:
            _target = self._get_target_from_id(self.policy.os_release_id)
        try:
            self.upload_target = _target(self.opts)
            self.soslog.debug(
                f"Upload target set to {self.upload_target.__class__}"
            )
        except Exception as err:
            raise Exception(f"Error setting upload target: {err}") from err

    def _get_target_from_id(self, target_id):
        """
        Find the upload target to instantiate based on the provided ID. From
        the calling `set_upload_target()` method, this will default to being
        the `os_release_id` from the loaded policy. However, by using a target
        ID users can upload from workstations that are not the same OS as the
        system that generated the archive, and additionally allows users to
        upload to non-OS vendors.

        :param target_id: The name of the upload target to use
        :type target_id: ``str``
        """
        try:
            _targets = self._load_targets()
            return _targets[target_id]
        except KeyError:
            self._exit(f"No such upload target: {target_id}")
        except Exception as err:
            self._exit(f"Error discovering upload target {target_id}: {err}")
        return None

    def _get_target_from_url(self):
        """
        Determine the appropriate target to use based on the value given
        via one of the upload options, such as `upload-url` or
        `upload-s3-endpoint`.

        Note that this requires using a protocol prefix in the value given to
        the referenced options. For example, to upload to an FTP location the
        `--upload-url` option should be set to `ftp://example.com`. Previous
        versions of sos supported an `--upload-protocol` option that is no
        longer available as it is considered redundant with this new url
        syntax requirement.
        """
        try:
            _targets = self._load_targets()
            _proto = self.opts.upload_url.split('://')[0]
            for _, _target in _targets.items():
                if _proto in _target.target_protocols:
                    return _target
        except KeyError:
            self._exit(
                f"No matching upload target for protocol '{_proto}'"
            )
        except Exception as err:
            self._exit(f"Error determining upload protocol: {err}")
        return None

    def set_upload_file(self, fname):
        """
        Override the file to be uploaded. While users executing an `sos upload`
        command directly will specify the filename via the --upload-file
        option, this can be used for when other sos component need to perform
        an upload after an archive has been generated.
        """
        if not os.path.exists(fname):
            raise Exception(f"Provided filename '{fname}' does not exist")
        self.upload_file = fname
        return True

    def _intro(self):
        upload_banner = """\
This utility is designed to upload sos report archives, as well as other \
support-related data, to remote locations that may or may not be provided by \
well-known vendors.\n\

Users should only upload data using this utility to locations that are both \
well-known and trusted by them and/or their organizations. This utility does \
not accept any responsibility for the safety, security, or handling of any \
data transmitted with it to any location.\n\

If this is unacceptable to users or their organizations, quit this utility now.
        """
        self.ui_log.info(f"\nsos upload (version {__version__})\n")
        self.ui_log.info(fmt_msg(upload_banner))

        prompt = "\nPress ENTER to continue, or CTRL-C to quit\n"
        if not self.opts.batch:
            try:
                input(prompt)
                self.ui_log.info("")
            except KeyboardInterrupt:
                self._exit("Exiting on user cancel", 130)
            except Exception as e:
                self._exit(e, 1)

    def execute(self):
        """Trigger the upload to the discovered target."""
        try:
            self.ui_log.info(
                f"Attempting upload of {self.upload_file} to "
                f"{self.upload_target.target_name or self.opts.upload_url}"
            )
            if self.upload_target.upload():
                self.ui_log.info('Upload successful')
            else:
                self.ui_log.info('Upload unsuccessful')
        except Exception as err:
            self.ui_log.error(f"Failed to upload: {err}")
