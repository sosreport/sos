# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
"""Shared fixtures for the upload test modules.

Imported by both upload_tests.py and upload_transfer_tests.py so that a
change in the upload source only has to be reflected in one place.
"""
import copy
import os
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from sos.upload import SoSUpload


# Taken from the component rather than hand-copied, so a new option
# cannot silently go missing here. Deep-copied because callers mutate
# the result.
UPLOAD_ARG_DEFAULTS = copy.deepcopy(SoSUpload.arg_defaults)
# Options that are set by the caller rather than argparse.
UPLOAD_ARG_DEFAULTS.update({
    'batch': True,
    'quiet': False,
})

# The only environment variables the get_upload_*() helpers consult.
# Tests scope just these so that everything else in os.environ stays
# available to the code under test.
SOS_UPLOAD_ENV_VARS = (
    'SOSUPLOADUSER',
    'SOSUPLOADPASSWORD',
    'SOSUPLOADS3ACCESSKEY',
    'SOSUPLOADS3SECRETKEY',
)


@contextmanager
def upload_env(**overrides):
    """Scope the upload credential variables without clearing os.environ.

    Removes only the variables listed in SOS_UPLOAD_ENV_VARS so a
    developer's shell cannot influence a result, applies any overrides,
    and restores the previous environment on exit.
    """
    with patch.dict(os.environ):
        for name in SOS_UPLOAD_ENV_VARS:
            os.environ.pop(name, None)
        os.environ.update(overrides)
        yield


def scope_upload_env(case):
    """setUp()-friendly form of upload_env(), undone on test teardown."""
    patcher = patch.dict(os.environ)
    patcher.start()
    case.addCleanup(patcher.stop)
    for name in SOS_UPLOAD_ENV_VARS:
        os.environ.pop(name, None)


def force_loaded(case, flag):
    """Pretend an optional upload dependency is importable.

    The transfer methods bail out early unless their library loaded, so
    tests that mock the library have to flip the corresponding module
    flag as well. Doing so keeps the suite's coverage identical on hosts
    that do not ship python3-requests or python3-boto3.
    """
    patcher = patch(flag, True)
    patcher.start()
    case.addCleanup(patcher.stop)


def make_opts(**overrides):
    """Build a stand-in for the parsed cmdline options.

    A bare MagicMock() would make every option attribute truthy, which
    quietly sends the code down the wrong branch in get_upload_url()
    and _determine_upload_type().
    """
    opts = MagicMock()
    for name, value in {**UPLOAD_ARG_DEFAULTS, **overrides}.items():
        setattr(opts, name, value)
    return opts


def make_target(cls, opts=None, **attrs):
    """Build an upload target without running __init__.

    Follows the RedHatCoreOSArchiveNameTests precedent: the instance is
    created via __new__, and the attributes that pre_work() would
    normally populate are set by hand.
    """
    target = cls.__new__(cls)
    target.ui_log = MagicMock()
    target.commons = {
        'cmdlineopts': opts if opts is not None else make_opts(),
        'policy': MagicMock(),
    }
    target.upload_url = None
    target.upload_user = None
    target.upload_password = None
    target.upload_directory = None
    target.upload_archive_name = ''
    target.upload_s3_access_key = None
    target.upload_s3_bucket = None
    target.upload_s3_endpoint = None
    target.upload_s3_object_prefix = None
    target.upload_s3_region = None
    target.upload_s3_secret_key = None
    for name, value in attrs.items():
        setattr(target, name, value)
    return target


def make_upload_component(**attrs):
    """Build a SoSUpload component without running __init__."""
    comp = SoSUpload.__new__(SoSUpload)
    comp.args = None
    comp.cmdline = None
    comp.parser = None
    comp.opts = make_opts()
    comp.policy = MagicMock()
    comp.ui_log = MagicMock()
    comp.upload_target = None
    for name, value in attrs.items():
        setattr(comp, name, value)
    return comp

# vim: set et ts=4 sw=4 :
