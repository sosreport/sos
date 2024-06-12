# Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import pwd
from glob import glob
from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Ssh(Plugin, IndependentPlugin):

    short_desc = 'Secure shell service'

    plugin_name = 'ssh'
    profiles = ('services', 'security', 'system', 'identity')

    option_list = [
        PluginOpt('userconfs', default=True, val_type=str,
                  desc=('Changes whether module will '
                        'collect user .ssh configs'))
    ]

    def setup(self):

        self.add_file_tags({
            '/etc/ssh/sshd_config$': 'sshd_config',
            '/etc/ssh/ssh_config$': 'ssh_config'
        })

        sshcfgs = [
            "/etc/ssh/ssh_config",
            "/etc/ssh/sshd_config",
            "/etc/ssh/sshd_config.d/*",
            ]

        # Include main config files
        self.add_copy_spec(sshcfgs)

        self.included_configs(sshcfgs)

        # If userconfs option is set to False, skips this
        if self.get_option('userconfs'):
            self.user_ssh_files_permissions()

    def included_configs(self, sshcfgs):
        """ Include subconfig files """
        # Read configs for any includes and copy those
        try:
            cfgfiles = [
                f for files in [
                    glob(copyspec, recursive=True) for copyspec in sshcfgs
                ] for f in files
            ]
            for sshcfg in cfgfiles:
                tag = sshcfg.split('/')[-1]
                with open(self.path_join(sshcfg), 'r',
                          encoding='UTF-8') as cfgfile:
                    for line in cfgfile:
                        # skip empty lines and comments
                        if len(line.split()) == 0 or line.startswith('#'):
                            continue
                        # ssh_config keywords are allowed as case-insensitive
                        if line.lower().startswith('include'):
                            confarg = line.split()
                            self.add_copy_spec(confarg[1], tags=tag)
        except Exception:  # pylint: disable=broad-except
            pass

    def user_ssh_files_permissions(self):
        """
        Iterate over .ssh folders in user homes to see their permissions.

        Bad permissions can prevent SSH from allowing access to given user.
        """
        users_data = pwd.getpwall()

        # Read the home paths of users in the system and check the ~/.ssh dirs
        for user in users_data:
            home_dir = self.path_join(user.pw_dir, '.ssh')
            if self.path_isdir(home_dir):
                self.add_cmd_output(f"ls -laZ {home_dir}")

# vim: set et ts=4 sw=4 :
