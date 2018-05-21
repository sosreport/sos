# Copyright (C) 2018 Red Hat, Inc.,

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class OvirtProviderOvn(Plugin, RedHatPlugin):
    """oVirt OVN Provider
    """

    packages = ('ovirt-provider-ovn',)
    plugin_name = 'ovirt_provider_ovn'
    profiles = ('virt',)

    provider_conf = '/etc/ovirt-provider-ovn/ovirt-provider-ovn.conf'

    def setup(self):
        self.add_copy_spec(self.provider_file)
        self.add_copy_spec('/etc/ovirt-provider-ovn/conf.d/*')

        spec = '/var/log/ovirt-provider-ovn.log'
        if self.get_option('all_logs'):
            spec += '*'
        self.add_copy_spec(spec, sizelimit=self.get_option('log_size'))

    def postproc(self):
        self.do_file_sub(self.provider_conf,
                         r'(ovirt-sso-client-secret\s*=\s*)(.*)',
                         r'\1*************')

# vim: set et ts=4 sw=4 :
