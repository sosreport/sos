# Copyright (C) Eric Desrochers <edesrochers@microsoft.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import AzurePlugin
from sos.policies.distros.redhat import RedHatPolicy


class AzurePolicy(RedHatPolicy):
    vendor = "Microsoft"
    vendor_urls = [
        ('Distribution Website', 'https://github.com/microsoft/azurelinux')
    ]
    os_release_name = 'Microsoft Azure Linux'
    os_release_file = ''

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super().__init__(sysroot=sysroot, init=init,
                         probe_runtime=probe_runtime,
                         remote_exec=remote_exec)
        self.valid_subclasses += [AzurePlugin]


class CBLMarinerPolicy(AzurePolicy):
    os_release_name = 'Common Base Linux Mariner'

# vim: set et ts=4 sw=4 :
