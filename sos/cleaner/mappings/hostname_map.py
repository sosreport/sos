# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re

from sos.cleaner.mappings import SoSMap


class SoSHostnameMap(SoSMap):
    """Mapping store for hostnames and domain names

    Hostnames are obfuscated using an incrementing counter based on the total
    number of hosts matched regardless of domain name.

    Domain names are obfuscated based on the host's hostname, plus any user
    defined domains passed in by the `--domains` options.

    Domains are obfuscated as whole units, meaning the domains 'example.com'
    and 'host.foo.example.com' will be separately obfuscated with no relation
    for example as 'obfuscatedomdain1.com' and 'obfuscatedomain2.com'.

    Top-level domains are left untouched.
    """

    ignore_matches = [
        'localhost',
        '.*localdomain.*',
        '^com..*'
    ]

    host_count = 0
    domain_count = 0
    _domains = {}
    hosts = {}

    def __init__(self, opt_domains):
        super(SoSHostnameMap, self).__init__()
        self.load_domains_from_options(opt_domains)

    def load_domains_from_options(self, domains):
        for domain in domains:
            self.sanitize_domain(domain.split('.'))

    def domain_name_in_loaded_domains(self, domain):
        """Check if a potential domain is in one of the domains we've loaded
        and should be obfuscated
        """
        host = domain.split('.')
        if len(host) == 1:
            # don't block on host's shortname
            return True
        if len(host) < 2:
            return False
        else:
            domain = host[0:-1]
            for known_domain in self._domains:
                if known_domain in domain:
                    return True
        return False

    def get(self, item):
        if item.startswith(('.', '_')):
            item = item.lstrip('._')
        item = item.strip()
        if not self.domain_name_in_loaded_domains(item):
            return item
        return super(SoSHostnameMap, self).get(item)

    def sanitize_item(self, item):
        host = item.split('.')
        if len(host) == 1:
            # we have a shortname for a host
            return self.sanitize_short_name(host[0])
        if len(host) == 2:
            # we have just a domain name, e.g. example.com
            return self.sanitize_domain(host)
        if len(host) > 2:
            # we have an FQDN, e.g. foo.example.com
            hostname = host[0]
            domain = host[1:]
            # obfuscate the short name
            ob_hostname = self.sanitize_short_name(hostname)
            ob_domain = self.sanitize_domain(domain)
            return '.'.join([ob_hostname, ob_domain])

    def sanitize_short_name(self, hostname):
        """Obfuscate the short name of the host with an incremented counter
        based on the total number of obfuscated host names
        """
        if hostname not in self.hosts:
            ob_host = "host%s" % self.host_count
            self.hosts[hostname] = ob_host
            self.host_count += 1
        return self.hosts[hostname]

    def sanitize_domain(self, domain):
        """Obfuscate the domainname, broken out into subdomains. Top-level
        domains are ignored.
        """
        for _skip in self.ignore_matches:
            # don't obfuscate vendor domains
            if re.match(_skip, '.'.join(domain)):
                return '.'.join(domain)
        top_domain = domain[-1]
        dname = '.'.join(domain[0:-1])
        ob_domain = self._new_obfuscated_domain(dname)
        ob_domain = '.'.join([ob_domain, top_domain])
        return ob_domain

    def _new_obfuscated_domain(self, dname):
        """Generate an obfuscated domain for each subdomain name given
        """
        if dname not in self._domains:
            self._domains[dname] = "obfuscateddomain%s" % self.domain_count
            self.domain_count += 1
        return self._domains[dname]
