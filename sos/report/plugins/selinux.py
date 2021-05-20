# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class SELinux(Plugin, RedHatPlugin):

    short_desc = 'SELinux access control'

    plugin_name = 'selinux'
    profiles = ('container', 'system', 'security', 'openshift')

    option_list = [("fixfiles", 'Print incorrect file context labels',
                    'slow', False)]
    packages = ('libselinux',)

    def setup(self):
        self.add_copy_spec([
            '/etc/sestatus.conf',
            '/etc/selinux'
        ])
        # capture this with a higher log limit since #2035 may limit this
        # collection
        self.add_copy_spec('/var/lib/selinux', sizelimit=50)
        self.add_cmd_output('sestatus')

        state = self.exec_cmd('getenforce')['output']
        if state != 'Disabled':
            self.add_cmd_output([
                'ps auxZww',
                'sestatus -v',
                'sestatus -b',
                'selinuxdefcon root',
                'selinuxconlist root',
                'selinuxexeccon /bin/passwd',
                'semanage -o'  # deprecated, may disappear at some point
            ])

            subcmds = [
                'fcontext',
                'user',
                'port',
                'login',
                'node',
                'interface',
                'module'
            ]

            for subcmd in subcmds:
                self.add_cmd_output("semanage %s -l" % subcmd)

            if self.get_option('fixfiles'):
                self.add_cmd_output("restorecon -Rvn /", stderr=False,
                                    priority=100)

# vim: set et ts=4 sw=4 :
