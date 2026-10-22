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
import re

from sos.cleaner.preppers import SoSPrepper

# RHSM subscription hostname that is a well-known public endpoint and must
# never be treated as a customer-specific domain.
_RHSM_PUBLIC_HOSTNAME = 'subscription.rhsm.redhat.com'


class HostnamePrepper(SoSPrepper):
    """
    Prepper for providing domain and hostname information to the hostname
    mapping.

    The items from hostname sources are handled manually via the _get_items
    method, rather than passing the file directly, as the parser does not know
    what hostnames or domains to match on initially.

    This will also populate the regex_items list with local short names.

    In addition to the system hostname and /etc/hosts, domains are seeded from
    SSSD, LDAP client configuration, Samba, IPA, RHSM, /etc/resolv.conf and
    /etc/krb5.conf so that internal/customer-specific FQDNs are obfuscated
    even when they appear only in configuration files and not in the system
    hostname itself.
    """

    name = 'hostname'

    hostname_re = re.compile(
        r'(?=\S*[a-zA-Z])[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)+'
    )
    audit_logs_re = r'\shostname=(' + hostname_re.pattern + r')'

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

    def _get_items_from_resolv_conf(self, archive):
        """Extract search domains and domain directives from /etc/resolv.conf.

        Both 'domain' (single search domain) and 'search' (space-separated
        list of domains) are collected so that short names appearing in config
        files are recognised as part of customer infrastructure.
        """
        items = []
        try:
            content = archive.get_file_content('etc/resolv.conf')
            if not content:
                return items
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#') or line.startswith(';'):
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                directive = parts[0].lower()
                if directive in ('domain', 'search'):
                    for domain in parts[1:]:
                        if self.hostname_re.fullmatch(domain.strip()):
                            items.append(domain.strip())
        except Exception as pump_up_the_jam:
            self.log_debug(
                f"Failed to parse etc/resolv.conf: {pump_up_the_jam}"
            )
        return items

    def _get_items_from_krb5_conf(self, archive):
        """Extract realm names and KDC/admin_server hostnames from Kerberos
        configuration files (/etc/krb5.conf and /etc/krb5.conf.d/*).

        Collected values include:
        - default_realm and realm names from [realms] and [domain_realm]
        - kdc, admin_server, kpasswd_server directives (FQDNs, stripping
          any trailing port specification)
        - [domain_realm] suffix mappings (values that begin with a dot are
          domain suffixes; the leading dot is stripped before seeding)
        """
        items = []
        krb5_files = ['etc/krb5.conf']

        # Collect supplementary drop-in files
        archive_root = None
        if getattr(archive, 'is_extracted', False):
            archive_root = archive.extracted_path
        elif os.path.isdir(getattr(archive, 'archive_path', '')):
            archive_root = archive.archive_path

        if archive_root:
            drop_in_dir = os.path.join(archive_root, 'etc', 'krb5.conf.d')
            if os.path.isdir(drop_in_dir):
                for fname in sorted(os.listdir(drop_in_dir)):
                    krb5_files.append(
                        os.path.join('etc', 'krb5.conf.d', fname)
                    )

        kdc_keys = {'kdc', 'admin_server', 'kpasswd_server'}
        realm_keys = {'default_realm'}

        for path in krb5_files:
            try:
                content = archive.get_file_content(path)
                if not content:
                    continue
                in_domain_realm = False
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith('#') or \
                            line.startswith(';'):
                        continue
                    # Track which section we are in
                    if line.startswith('['):
                        section = line.strip('[]').lower()
                        in_domain_realm = 'domain_realm' == section
                        continue
                    if '=' not in line:
                        continue
                    key, _, value = line.partition('=')
                    key = key.strip().lower()
                    value = value.strip().strip('"').strip("'")
                    if not value:
                        continue
                    if in_domain_realm:
                        # Values are realm names (customer Kerberos realms)
                        # Keys starting with '.' are domain suffixes – seed
                        # both with and without the leading dot.
                        domain = value.strip()
                        if domain:
                            items.append(domain)
                        key_part = key.lstrip('.')
                        if self.hostname_re.fullmatch(key_part):
                            items.append(key_part)
                    elif key in realm_keys:
                        items.append(value)
                    elif key in kdc_keys:
                        # Strip optional port suffix (host:port)
                        host = value.split(':')[0].strip()
                        if self.hostname_re.fullmatch(host):
                            items.append(host)
            except Exception as hackers:
                self.log_debug(
                    f"Failed to parse {path}: {hackers}"
                )
        return items

    def _get_items_from_ldap_conf(self, archive):
        """Extract LDAP server hostnames and base DNs from common LDAP client
        configuration files.

        Supported files:
        - etc/openldap/ldap.conf
        - etc/ldap/ldap.conf
        - etc/nslcd.conf
        - etc/pam_ldap.conf

        The URI directive is parsed for the host portion.  The BASE directive
        is parsed and DC components are reassembled into a domain name.
        """
        items = []
        ldap_files = [
            'etc/openldap/ldap.conf',
            'etc/ldap/ldap.conf',
            'etc/nslcd.conf',
            'etc/pam_ldap.conf',
        ]
        uri_re = re.compile(
            r'ldaps?://([a-zA-Z0-9._-]+)', re.IGNORECASE
        )
        dc_re = re.compile(r'\bdc=([a-zA-Z0-9_-]+)', re.IGNORECASE)

        for path in ldap_files:
            try:
                content = archive.get_file_content(path)
                if not content:
                    continue
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split(None, 1)
                    if len(parts) < 2:
                        continue
                    directive = parts[0].lower()
                    value = parts[1].strip()
                    if directive == 'uri':
                        for match in uri_re.finditer(value):
                            host = match.group(1)
                            if self.hostname_re.fullmatch(host):
                                items.append(host)
                    elif directive == 'base':
                        dc_parts = dc_re.findall(value)
                        if dc_parts:
                            domain = '.'.join(dc_parts)
                            if self.hostname_re.fullmatch(domain):
                                items.append(domain)
            except Exception as exc:
                self.log_debug(
                    f"Failed to parse {path}: {exc}"
                )
        return items

    def _get_items_from_samba_conf(self, archive):
        """Extract realm and password server values from /etc/samba/smb.conf.

        'realm' typically holds the Kerberos realm / AD domain name.
        'password server' may hold the FQDN of a domain controller.
        """
        items = []
        try:
            content = archive.get_file_content('etc/samba/smb.conf')
            if not content:
                return items
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#') or \
                        line.startswith(';'):
                    continue
                if '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip().lower()
                value = value.strip().strip('"').strip("'")
                if key == 'realm' and value:
                    items.append(value)
                elif key == 'password server' and \
                        self.hostname_re.fullmatch(value):
                    items.append(value)
        except Exception as exc:
            self.log_debug(
                f"Failed to parse etc/samba/smb.conf: {exc}"
            )
        return items

    def _get_items_from_ipa_conf(self, archive):
        """Extract domain, server and realm values from /etc/ipa/default.conf.

        All three keys map directly to customer-specific infrastructure names
        and must be obfuscated.
        """
        items = []
        ipa_keys = {'domain', 'server', 'realm'}
        try:
            content = archive.get_file_content('etc/ipa/default.conf')
            if not content:
                return items
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#') or \
                        line.startswith(';'):
                    continue
                if '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip().lower()
                value = value.strip().strip('"').strip("'")
                if key in ipa_keys and value:
                    items.append(value)
        except Exception as exc:
            self.log_debug(
                f"Failed to parse etc/ipa/default.conf: {exc}"
            )
        return items

    def _get_items_from_rhsm_conf(self, archive):
        """Extract the RHSM server hostname from /etc/rhsm/rhsm.conf.

        Only the 'hostname' key under the [server] section is collected.
        The well-known public endpoint 'subscription.rhsm.redhat.com' is
        explicitly skipped because it is not customer-specific infrastructure.
        """
        items = []
        try:
            content = archive.get_file_content('etc/rhsm/rhsm.conf')
            if not content:
                return items
            in_server_section = False
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#') or \
                        line.startswith(';'):
                    continue
                if line.startswith('['):
                    section = line.strip('[]').lower()
                    in_server_section = 'server' == section
                    continue
                if not in_server_section or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip().lower()
                value = value.strip().strip('"').strip("'")
                # Inline comment strip
                value = value.split('#')[0].strip()
                if key == 'hostname' and value:
                    if value == _RHSM_PUBLIC_HOSTNAME:
                        continue
                    items.append(value)
        except Exception as exc:
            self.log_debug(
                f"Failed to parse etc/rhsm/rhsm.conf: {exc}"
            )
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
        items.extend(self._get_items_from_resolv_conf(archive))
        items.extend(self._get_items_from_krb5_conf(archive))
        items.extend(self._get_items_from_ldap_conf(archive))
        items.extend(self._get_items_from_samba_conf(archive))
        items.extend(self._get_items_from_ipa_conf(archive))
        items.extend(self._get_items_from_rhsm_conf(archive))

        return items
