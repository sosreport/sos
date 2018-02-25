# Copyright (C) 2018 Red Hat, Inc.,

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
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
