# Copyright 2023 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import glob
import os

from sos.cleaner.preppers import SoSPrepper


class UsernamePrepper(SoSPrepper):
    """
    This prepper is used to source usernames from various `last` output content
    as well as a couple select files. This prepper will also leverage the
    --usernames option.
    """

    name = 'username'

    sssd_conf_patterns = [
        'etc/sssd/sssd.conf*',
        'etc/sssd/conf.d/*'
    ]

    sssd_username_keys = {
        'users',
        'excluded_users',
        'pam_trusted_users',
        'simple_allow_users',
        'simple_deny_users',
    }

    skip_list = [
        'ceilometer',
        'ceph',
        'cloud-admin',
        'core',
        'libvirt',
        'nobody',
        'nfsnobody',
        'nova',
        'openvswitch',
        'shutdown',
        'stack',
        'reboot',
        'root',
        'test',
        'timeout:',
        'ubuntu',
        'username',
        'wtmp',
    ]

    audit_logs_re = r'(?:UID|AUID)=(?:")?(\w+)(?:")?'

    def _get_conf_files(self, archive):
        paths = set()
        archive_root = None
        if getattr(archive, 'is_extracted', False):
            archive_root = archive.extracted_path
        elif os.path.isdir(getattr(archive, 'archive_path', '')):
            archive_root = archive.archive_path

        if archive_root:
            for pattern in self.sssd_conf_patterns:
                full_pattern = os.path.join(archive_root, pattern.lstrip('/'))
                for full_path in glob.glob(full_pattern):
                    if os.path.isfile(full_path):
                        paths.add(
                            os.path.relpath(full_path, start=archive_root)
                        )

        return paths

    def _get_items_from_sssd_conf(self, archive):
        items = set()

        paths = self._get_conf_files(archive)

        for path in sorted(paths):
            content = archive.get_file_content(path)
            if not content:
                continue
            for line in content.splitlines():
                line = line.lstrip()

                # Commented lines may still contain sensitive login names, so
                # strip any leading comment markers before parsing them.
                while line.startswith('#') or line.startswith(';'):
                    line = line[1:].lstrip()

                # Inline comments following a directive are unlikely to hold
                # sensitive data and may be unstructured, so drop them.
                line = line.split('#', 1)[0].split(';', 1)[0].strip()

                if not line or line.startswith('[') or '=' not in line:
                    continue
                key, value = [x.strip() for x in line.split('=', 1)]
                key = key.lower()
                if key not in self.sssd_username_keys:
                    continue
                for user in value.split(','):
                    user = user.strip().strip('"').strip("'").lower()
                    # pam_trusted_users may list numeric UIDs, which are not
                    # login names and must not be obfuscated as such.
                    if not user or user.isdigit():
                        continue
                    if user not in self.skip_list:
                        items.add(user)
                    # handle fully-qualified names such as DOMAIN\user or
                    # user@domain by also sourcing the bare login name
                    if '\\' in user:
                        bare = user.split('\\')[-1]
                        if bare and bare not in self.skip_list:
                            items.add(bare)
                    if '@' in user:
                        bare = user.split('@')[0]
                        if bare and bare not in self.skip_list:
                            items.add(bare)
        return items

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

        items.update(self._get_items_from_sssd_conf(archive))

        return items

# vim: set et ts=4 sw=4 :
