# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.cleaner.parsers import SoSCleanerParser
from sos.cleaner.mappings.hostname_map import SoSHostnameMap


class SoSHostnameParser(SoSCleanerParser):

    name = 'Hostname Parser'
    map_file_key = 'hostname_map'
    regex_patterns = [
        r'(((\b|_)[a-zA-Z0-9-\.]{1,200}\.[a-zA-Z]{1,63}(\b|_)))'
    ]

    def __init__(self, config, opt_domains=None):
        self.mapping = SoSHostnameMap()
        super(SoSHostnameParser, self).__init__(config)
        self.mapping.load_domains_from_map()
        self.mapping.load_domains_from_options(opt_domains)
        self.short_names = []
        self.load_short_names_from_mapping()
        self.mapping.set_initial_counts()

    def load_short_names_from_mapping(self):
        """When we load the mapping file into the hostname map, we have to do
        some dancing to get those loaded properly into the "intermediate" dicts
        that the map uses to hold hosts and domains. Similarly, we need to also
        extract shortnames known to the map here.
        """
        for hname in self.mapping.dataset.keys():
            if len(hname.split('.')) == 1:
                # we have a short name only with no domain
                if hname not in self.short_names:
                    self.short_names.append(hname)

    def load_hostname_into_map(self, hostname_string):
        """Force add the domainname found in /sos_commands/host/hostname into
        the map. We have to do this here since the normal map prep approach
        from the parser would be ignored since the system's hostname is not
        guaranteed
        """
        if 'localhost' in hostname_string:
            return
        domains = hostname_string.split('.')
        if len(domains) > 1:
            self.short_names.append(domains[0])
        else:
            self.short_names.append(hostname_string)
        if len(domains) > 3:
            # make sure we implicitly get example.com if the system's hostname
            # is something like foo.bar.example.com
            high_domain = '.'.join(domains[-2:])
            self.mapping.add(high_domain)
        self.mapping.add(hostname_string)

    def load_hostname_from_etc_hosts(self, content):
        """Parse an archive's copy of /etc/hosts, which requires handling that
        is separate from the output of the `hostname` command. Just like
        load_hostname_into_map(), this has to be done explicitly and we
        cannot rely upon the more generic methods to do this reliably.
        """
        lines = content.splitlines()
        for line in lines:
            if line.startswith('#') or 'localhost' in line:
                continue
            hostln = line.split()[1:]
            for host in hostln:
                if len(host.split('.')) == 1:
                    # only generate a mapping for fqdns but still record the
                    # short name here for later obfuscation with parse_line()
                    self.short_names.append(host)
                    self.mapping.add_regex_item(host)
                else:
                    self.mapping.add(host)
