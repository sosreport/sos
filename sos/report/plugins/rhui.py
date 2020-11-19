# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Rhui(Plugin, RedHatPlugin):

    short_desc = "RHUI Information"
    plugin_name = 'rhui'
    profiles = ('sysmgmt',)
    packages = ('rh-rhui-tools',)

    def setup(self):
        self.add_copy_spec([
            '/etc/rhui-installer/',
            '/etc/rhui/rhui-tools.conf',
            '/etc/pki/rhua',
            '/etc/pki/rhui',
            '/etc/pki/katello-certs-tools',
            '/root/ssl-build',
            '/root/.rhui',
            '/var/log/kafo',
            '/var/log/rhui-sub-sync.log'
        ])

        self.add_cmd_output([
            'rhui-manager status',
            'rhui-manager cert info',
            'ls /var/lib/rhui/remote_share'
        ])

    def postproc(self):
        self.do_file_sub(
            '/etc/rhui-installer/answers.yml',
            r'(.*_(password|key):)(.*)',
            r'\1 *******'
        )

# vim: set et ts=4 sw=4 :
