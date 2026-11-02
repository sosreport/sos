# Copyright (C) Red Hat, Inc. 2020

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import CosPlugin
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
    PATH = "/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin"

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super().__init__(sysroot=sysroot, init=init,
                         probe_runtime=probe_runtime,
                         remote_exec=remote_exec)
        self.valid_subclasses += [CosPlugin]

    def match_plugin(self, plugin_classes):
        """Prefer plugin classes that are tagged directly with CosPlugin.

        Plugin classes for other distributions may inherit CosPlugin from a
        shared base class, and the default matching would otherwise prefer
        an IndependentPlugin class over a CoS specific one.
        """
        for plugin_class in plugin_classes:
            if CosPlugin in plugin_class.__bases__:
                return plugin_class
        return super().match_plugin(plugin_classes)

# vim: set et ts=4 sw=4 :
