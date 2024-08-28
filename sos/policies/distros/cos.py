# Copyright (C) Red Hat, Inc. 2020

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import CosPlugin, IndependentPlugin
from sos.policies.distros import LinuxPolicy


def _blank_or_comment(line):
    """Test whether line is empty of contains a comment.

        Test whether the ``line`` argument is either blank, or a
        whole-line comment.

        :param line: the line of text to be checked.
        :returns: ``True`` if the line is blank or a comment,
                  and ``False`` otherwise.
        :rtype: bool
    """
    return not line.strip() or line.lstrip().startswith('#')


class CosPolicy(LinuxPolicy):
    vendor = "Google Cloud Platform"
    vendor_urls = [
        ('Distribution Website',
         'https://cloud.google.com/container-optimized-os/')
    ]
    os_release_name = 'Container-Optimized OS'
    os_release_id = 'cos'
    valid_subclasses = [CosPlugin, IndependentPlugin]
    PATH = "/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin"

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super().__init__(sysroot=sysroot, init=init,
                         probe_runtime=probe_runtime,
                         remote_exec=remote_exec)
        self.valid_subclasses += [CosPolicy]

# vim: set et ts=4 sw=4 :
