# Copyright 2023 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
            hostln = line.split()[1:]
            for host in hostln:
                if len(host.split('.')) == 1:
                    self.regex_items['hostname'].add(host)
                else:
                    items.append(host)

        for domain in self.opts.domains:
            items.append(domain)

        return items
