# Copyright 2023 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.cleaner.preppers import SoSPrepper


class UsernamePrepper(SoSPrepper):
    """
    This prepper is used to source usernames from various `last` output content
    as well as a couple select files. This prepper will also leverage the
    --usernames option.
    """

    name = 'username'

    skip_list = [
        'core',
        'nobody',
        'nfsnobody',
        'shutdown',
        'stack',
        'reboot',
        'root',
        'timeout:',
        'ubuntu',
        'username',
        'wtmp'
    ]

    def _get_items_for_username(self, archive):
        items = set()
        _files = [
            'sos_commands/login/lastlog_-u_1000-60000',
            'sos_commands/login/lastlog_-u_60001-65536',
            'sos_commands/login/lastlog_-u_65537-4294967295',
            'sos_commands/login/lastlog2',
            # AD users will be reported here, but favor the lastlog files since
            # those will include local users who have not logged in
            'sos_commands/login/last',
            'sos_commands/login/last_-F',
            'sos_commands/login/lslogins',
            'etc/cron.allow',
            'etc/cron.deny'
        ]
        for _file in _files:
            content = archive.get_file_content(_file)
            if not content:
                continue
            for line in content.splitlines():
                try:
                    user = line.split()[0].lower()
                    if "lslogins" in _file:
                        if int(line.split()[0]) >= 1000:
                            user = line.split()[1].lower()
                        else:
                            continue
                    if user and user not in self.skip_list:
                        items.add(user)
                        if '\\' in user:
                            items.add(user.split('\\')[-1])
                except Exception:
                    # empty line or otherwise unusable for name sourcing
                    pass

        for opt_user in self.opts.usernames:
            if opt_user not in self.skip_list:
                items.add(opt_user)

        return items

# vim: set et ts=4 sw=4 :
