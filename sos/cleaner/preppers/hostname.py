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


class HostnamePrepper(SoSPrepper):
    """
    Prepper for providing domain and hostname information to the hostname
    mapping.

    The items from hostname sources are handled manually via the _get_items
    method, rather than passing the file directly, as the parser does not know
    what hostnames or domains to match on initially.

    This will also populate the regex_items list with local short names.
    """

    name = 'hostname'
    audit_logs_re = r'\shostname=(\S+)'

    sssd_conf_patterns = [
        'etc/sssd/sssd.conf*',
        'etc/sssd/conf.d/*'
    ]

    sssd_config_keys = {
        'domains',
        'krb5_realm',
        'ad_domain',
        'ipa_domain',
        'dns_discovery_domain',
        'default_domain_suffix',
        'ad_server',
        'ipa_server',
        'krb5_server',
        'krb5_kpasswd',
        'krb5_backup_kpasswd',
        'ldap_uri',
        'ldap_backup_uri',
        'dyndns_server'
    }

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
        items = []

        paths = self._get_conf_files(archive)

        for path in sorted(paths):
            content = archive.get_file_content(path)
            if not content:
                continue
            for line in content.splitlines():
                line = line.lstrip()

                # Commented lines may contain sensitive data, so we should
                # still process them to extract any domains or hostnames
                # but we need to strip the comment character first.
                while line.startswith('#') or line.startswith(';'):
                    line = line[1:].lstrip()

                # Inline comment after directives are not likely to contain
                # sensitive data and may be unstructured, so we can ignore them
                line = line.split('#', 1)[0].split(';', 1)[0].strip()

                if not line or line.startswith('[') or '=' not in line:
                    continue
                key, value = [x.strip() for x in line.split('=', 1)]
                key = key.lower()
                if key in self.sssd_config_keys:
                    for domain in value.split(','):
                        domain = domain.strip().strip('"').strip("'")
                        if domain:
                            items.append(domain)
                            if '.' in domain:
                                self.regex_items['hostname'].add(domain)
        return items

    def _get_items_for_hostname(self, archive):
        items = []
        _file = 'hostname'
        if archive.is_sos:
            _file = 'sos_commands/host/hostname_-f'
        elif archive.is_insights:
            _file = 'data/insights_commands/hostname_-f'

        content = archive.get_file_content(_file)
        if content and content != 'localhost':
            domains = content.split('.')
            if len(domains) > 1:
                items.append(domains[0])
                self.regex_items['hostname'].add((domains[0]))
            if len(domains) > 3:
                # make sure we get example.com if the system's hostname
                # is something like foo.bar.example.com
                top_domain = '.'.join(domains[-2:])
                items.append(top_domain.strip())
            items.append(content.strip())

        _hosts = archive.get_file_content('etc/hosts')
        for line in _hosts.splitlines():
            if line.startswith('#') or 'localhost' in line:
                continue
            # strip inline comments before processing
            line = line.split('#')[0].strip()
            if not line:
                continue
            hostln = line.split()[1:]
            for host in hostln:
                if len(host.split('.')) == 1:
                    self.regex_items['hostname'].add(host)
                # unconditionally append host to items to avoid
                # missing short hostnames like 'my-computer'
                items.append(host)

        for domain in self.opts.domains:
            items.append(domain)

        items.extend(self._get_items_from_sssd_conf(archive))

        return items
