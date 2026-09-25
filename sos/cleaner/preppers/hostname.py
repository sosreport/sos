# Copyright 2023 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import fnmatch
import os
import re
import yaml

from sos.cleaner.preppers import SoSPrepper


class HostnamePrepper(SoSPrepper):
    """
    Prepper for providing domain and hostname information to the hostname
    mapping.

    The items from hostname sources are handled manually via the _get_items
    method, rather than passing the file directly, as the parser does not know
    what hostnames or domains to match on initially.

    In addition to the system hostname, /etc/hosts, and any user-provided
    --domains, this prepper also mines netplan configuration for DNS search
    domains and requested hostnames. These values are not necessarily the
    system's own hostname or present in /etc/hosts, and so would otherwise
    not be obfuscated by ``sos clean``.

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

    netplan_dirs = [
        'etc/netplan',
        'lib/netplan',
        'run/netplan',
    ]

    def _iter_archive_relpaths(self, archive):
        """Yield archive-relative paths for every regular file in the archive,
        working both before and after extraction.

        Preppers run *before* the archive is extracted, so during prep the
        archive is still a tarball and ``extracted_path`` does not yet exist.
        In that case we read the member list directly from the tarball. Once
        the archive has been extracted (or is a plain directory), we fall back
        to walking the extracted tree.

        :param archive: The archive we are currently operating on
        :type archive:  ``SoSObfuscationArchive``

        :returns: Archive-relative file paths
        :rtype:   generator of ``str``
        """
        # not-yet-extracted tarball: enumerate members from the tarball object
        if not getattr(archive, 'is_extracted', False) \
                and getattr(archive, 'is_tarfile', False) \
                and getattr(archive, 'tarobj', None) is not None:
            if not archive.archive_root:
                archive.archive_root = archive.get_archive_root()
            root = archive.archive_root
            for member in archive.tarobj.getmembers():
                if not member.isfile():
                    continue
                rel = os.path.relpath(member.name, root) if root \
                    else member.name
                yield rel
            return

        # otherwise walk a directory on disk. For an already-extracted tarball
        # this is ``extracted_path``; for a report/collect *directory* archive
        # (e.g. ``sos report --clean`` in-line obfuscation), prep runs before
        # extract() is called so ``extracted_path`` is not set yet - in that
        # case the on-disk root is the archive_path itself.
        root = getattr(archive, 'extracted_path', None) \
            or getattr(archive, 'archive_path', None)
        if not root:
            return

        # if the archive exposes get_files() (extracted tarball archives do),
        # prefer it and translate the absolute paths it yields into paths that
        # are relative to the archive root
        if hasattr(archive, 'get_files'):
            try:
                for _file in archive.get_files():
                    yield os.path.relpath(_file, root)
                return
            except (AttributeError, TypeError):
                pass

        # directory archive during prep: walk the tree ourselves
        if not root or not os.path.isdir(root):
            return
        for dirname, _, files in os.walk(str(root)):
            for filename in files:
                _fname = os.path.join(dirname, filename)
                if os.path.islink(_fname):
                    continue
                yield os.path.relpath(_fname, str(root))

    def _get_conf_files(self, archive):
        paths = set()
        for pattern in self.sssd_conf_patterns:
            _regex = re.compile(fnmatch.translate(pattern.lstrip('/')))
            for rel in self._iter_archive_relpaths(archive):
                if _regex.match(rel):
                    paths.add(rel)
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

    def _get_netplan_items(self, archive):
        """Extract DNS search domains and requested hostnames from any netplan
        YAML configuration present in the archive.

        :param archive: The archive we are currently operating on
        :type archive:  ``SoSObfuscationArchive``

        :returns: The distinct domains and hostnames found in netplan config
        :rtype:   ``set``
        """
        items = set()
        for rel in self._iter_archive_relpaths(archive):
            if not (any(rel.startswith(d) for d in self.netplan_dirs)
                    and rel.endswith(('.yaml', '.yml'))):
                continue
            content = archive.get_file_content(rel)
            if not content:
                continue
            try:
                for doc in yaml.safe_load_all(content):
                    self._walk_netplan(doc, items)
            except yaml.YAMLError as err:
                self.log_debug(f"Could not parse netplan file {rel}: {err}")

        return {item for item in items if item}

    @staticmethod
    def _walk_netplan(node, out):
        """Recursively collect `search` domains and requested `hostname`
        values from a parsed netplan document.
        """
        if isinstance(node, dict):
            for key, val in node.items():
                if key == 'search' and isinstance(val, list):
                    out.update(str(v).strip() for v in val)
                elif key == 'hostname' and isinstance(val, str):
                    out.add(val.strip())
                else:
                    HostnamePrepper._walk_netplan(val, out)
        elif isinstance(node, list):
            for item in node:
                HostnamePrepper._walk_netplan(item, out)

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

        for item in self._get_netplan_items(archive):
            if len(item.split('.')) == 1:
                self.regex_items['hostname'].add(item)
            items.append(item)

        return items

# vim: set et ts=4 sw=4 :
