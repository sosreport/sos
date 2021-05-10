# Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Ssh(Plugin, IndependentPlugin):

    short_desc = 'Secure shell service'

    plugin_name = 'ssh'
    profiles = ('services', 'security', 'system', 'identity')

    def setup(self):

        self.add_file_tags({
            '/etc/ssh/sshd_config': 'sshd_config',
            '/etc/ssh/ssh_config': 'ssh_config'
        })

        sshcfgs = [
            "/etc/ssh/ssh_config",
            "/etc/ssh/sshd_config"
            ]

        # Include main config files
        self.add_copy_spec(sshcfgs)

        # Read configs for any includes and copy those
        try:
            for sshcfg in sshcfgs:
                tag = sshcfg.split('/')[-1]
                with open(sshcfg, 'r') as cfgfile:
                    for line in cfgfile:
                        # skip empty lines and comments
                        if len(line.split()) == 0 or line.startswith('#'):
                            continue
                        # ssh_config keywords are allowed as case-insensitive
                        if line.lower().startswith('include'):
                            confarg = line.split()
                            self.add_copy_spec(confarg[1], tags=tag)
        except Exception:
            pass


# vim: set et ts=4 sw=4 :
