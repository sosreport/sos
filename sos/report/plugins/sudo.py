# Copyright (C) 2018 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Sudo(Plugin, IndependentPlugin):

    short_desc = 'Sudo command execution'
    plugin_name = 'sudo'
    profiles = ('identity', 'system')
    packages = ('sudo',)

    def setup(self):
        self.add_copy_spec("/etc/sudo*")

        config_file = "/etc/sudo.conf"
        log_files = ['/var/log/sudo_debug', '/var/log/sudoers_debug']
        try:
            with open(config_file, 'r', encoding='UTF-8') as cfile:
                for line in cfile:
                    if line.startswith('Debug'):
                        log_files.append(line.split()[2])
        except IOError as error:
            self._log_error(f'Could not open conf file {config_file}: '
                            f'{error}')

        if not self.get_option('all_logs'):
            self.add_copy_spec(log_files)
        else:
            self.add_copy_spec([f"{log}*" for log in log_files])

    def postproc(self):
        regexp = r"(\s*bindpw\s*)\S+"
        self.do_file_sub("/etc/sudo-ldap.conf", regexp, r"\1********")


# vim: set et ts=4 sw=4 :
