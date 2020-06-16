# Copyright (C) Red Hat, Inc. 2020

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import CosPlugin
from sos.policies import LinuxPolicy


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
    distro = "Container-Optimized OS"
    vendor = "Google Cloud Platform"
    vendor_url = "https://cloud.google.com/container-optimized-os/"
    valid_subclasses = [CosPlugin]
    PATH = "/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin"

    @classmethod
    def check(cls, remote=''):
        if remote:
            return cls.distro in remote

        try:
            with open('/etc/os-release', 'r') as fp:
                os_release = dict(line.strip().split('=') for line in fp
                                  if not _blank_or_comment(line))
                id = os_release.get('ID')
                return id == 'cos'
        except IOError:
            return False

# vim: set et ts=4 sw=4 :
