# Copyright (C) Eric Desrochers <edesrochers@microsoft.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.report.plugins import AzurePlugin
from sos.policies.distros.redhat import RedHatPolicy, OS_RELEASE


class AzurePolicy(RedHatPolicy):

    distro = "Azure Linux"
    vendor = "Microsoft"
    vendor_urls = [
        ('Distribution Website', 'https://github.com/microsoft/azurelinux')
    ]

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super().__init__(sysroot=sysroot, init=init,
                         probe_runtime=probe_runtime,
                         remote_exec=remote_exec)
        self.valid_subclasses += [AzurePlugin]

    @classmethod
    def check(cls, remote=''):

        if remote:
            return cls.distro in remote

        if not os.path.exists(OS_RELEASE):
            return False

        with open(OS_RELEASE, 'r') as f:
            for line in f:
                if line.startswith('NAME'):
                    if 'Common Base Linux Mariner' in line:
                        return True
                    if 'Microsoft Azure Linux' in line:
                        return True
        return False

# vim: set et ts=4 sw=4 :
