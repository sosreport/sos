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

    skip_keys = [
        'www',
        'api'
    ]

    strip_exts = ('.yaml', '.yml', '.crt', '.key', '.pem', '.log', '.repo',
                  '.rules')

    host_count = 0
    domain_count = 0
    _domains = {}
    hosts = {}

    def load_domains_from_map(self):
        """Because we use 'intermediary' dicts for host names and domain names
        in this parser, we need to re-inject entries from the map_file into
        these dicts and not just the underlying 'dataset' dict
        """
        for domain, ob_pair in self.dataset.items():
            if len(domain.split('.')) == 1:
                self.hosts[domain.split('.')[0]] = self.dataset[domain]
            else:
                if ob_pair.startswith('obfuscateddomain'):
                    # directly exact domain matches
                    self._domains[domain] = ob_pair.split('.')[0]
                    continue
                # strip the host name and trailing top-level domain so that
                # we in inject the domain properly for later string matching

                # note: this is artificially complex due to our stance on
                # preserving TLDs. If in the future the project decides to
                # obfuscate TLDs as well somehow, then this will all become
                # much simpler
                _domain_to_inject = '.'.join(domain.split('.')[1:-1])
                if not _domain_to_inject:
                    continue
                for existing_domain in self.dataset.keys():
                    _existing = '.'.join(existing_domain.split('.')[:-1])
                    if _existing == _domain_to_inject:
                        _ob_domain = '.'.join(
                            self.dataset[existing_domain].split('.')[:-1]
                        )
                        self._domains[_domain_to_inject] = _ob_domain
        self.set_initial_counts()

    def load_domains_from_options(self, domains):
        for domain in domains:
            self.sanitize_domain(domain.split('.'))

    def get_regex_result(self, item):
        """Override the base get_regex_result() to provide a regex that, if
        this is an FQDN or a straight domain, will include an underscore
        formatted regex as well.
        """
        if '.' in item:
            item = item.replace('.', '(\\.|_)')
        return re.compile(item, re.I)

    def set_initial_counts(self):
        """Set the initial counter for host and domain obfuscation numbers
        based on what is already present in the mapping.
        """
        # hostnames/short names
        try:
            h = sorted(self.hosts.values(), reverse=True)[0].split('host')[1]
            self.host_count = int(h) + 1
        except IndexError:
            # no hosts loaded yet
            pass

        # domain names
        try:
            d = sorted(self._domains.values(), reverse=True)[0].split('domain')
            self.domain_count = int(d[1].split('.')[0]) + 1
        except IndexError:
            # no domains loaded yet
            pass

    def domain_name_in_loaded_domains(self, domain):
        """Check if a potential domain is in one of the domains we've loaded
        and should be obfuscated
        """
        if domain in self._domains:
            return True
        host = domain.split('.')
        no_tld = '.'.join(domain.split('.')[0:-1])
        if len(host) == 1:
            # don't block on host's shortname
            return host[0] in self.hosts
        elif any([no_tld.endswith(_d) for _d in self._domains]):
            return True

        return False

    def get(self, item):
        prefix = ''
        suffix = ''
        final = None
        # The regex pattern match may include a leading and/or trailing '_'
        # character due to the need to use word boundary matching, so we need
        # to strip these from the string during processing, but still keep them
        # in the returned string to not mangle the string replacement in the
        # context of the file or filename
        while item.startswith(('.', '_')):
            prefix += item[0]
            item = item[1:]
        while item.endswith(('.', '_')):
            suffix += item[-1]
            item = item[0:-1]
        if item in self.dataset:
            return self.dataset[item]
        if not self.domain_name_in_loaded_domains(item.lower()):
            return item
        if item.endswith(self.strip_exts):
            ext = '.' + item.split('.')[-1]
            item = item.replace(ext, '')
            suffix += ext
        if item not in self.dataset.keys():
            # try to account for use of '-' in names that include hostnames
            # and don't create new mappings for each of these
            for _existing in sorted(self.dataset.keys(), reverse=True,
                                    key=lambda x: len(x)):
                _host_substr = False
                _test = item.split(_existing)
                _h = _existing.split('.')
                # avoid considering a full FQDN match as a new match off of
                # the hostname of an existing match
                if _h[0] and _h[0] in self.hosts.keys():
                    _host_substr = True
                if len(_test) == 1 or not _test[0]:
                    # does not match existing obfuscation
                    continue
                elif not _host_substr and (_test[0].endswith('.') or
                                           item.endswith(_existing)):
                    # new hostname in known domain
                    final = super(SoSHostnameMap, self).get(item)
                    break
                elif item.split(_test[0]):
                    # string that includes existing FQDN obfuscation substring
                    # so, only obfuscate the FQDN part
                    try:
                        itm = item.split(_test[0])[1]
                        final = _test[0] + super(SoSHostnameMap, self).get(itm)
                        break
                    except Exception:
                        # fallback to still obfuscating the entire item
                        pass

        if not final:
            final = super(SoSHostnameMap, self).get(item)
        return prefix + final + suffix

    def sanitize_item(self, item):
        host = item.split('.')
        if len(host) == 1:
            # we have a shortname for a host
            return self.sanitize_short_name(host[0].lower())
        if len(host) == 2:
            # we have just a domain name, e.g. example.com
            dname = self.sanitize_domain(host)
            if all([h.isupper() for h in host]):
                dname = dname.upper()
            return dname
        if len(host) > 2:
            # we have an FQDN, e.g. foo.example.com
            hostname = host[0]
            domain = host[1:]
            # obfuscate the short name
            if len(hostname) > 2:
                ob_hostname = self.sanitize_short_name(hostname.lower())
            else:
                # by best practice it appears the host part of the fqdn was cut
                # off due to some form of truncating, as such don't obfuscate
                # short strings that are likely to throw off obfuscation of
                # unrelated bits and paths
                ob_hostname = 'unknown'
            ob_domain = self.sanitize_domain(domain)
            self.dataset[item] = ob_domain
            _fqdn = '.'.join([ob_hostname, ob_domain])
            if all([h.isupper() for h in host]):
                _fqdn = _fqdn.upper()
            return _fqdn

    def sanitize_short_name(self, hostname):
        """Obfuscate the short name of the host with an incremented counter
        based on the total number of obfuscated host names
        """
        if not hostname or hostname in self.skip_keys:
            return hostname
        if hostname not in self.dataset:
            ob_host = "host%s" % self.host_count
            self.hosts[hostname] = ob_host
            self.host_count += 1
            self.dataset[hostname] = ob_host
            self.add_regex_item(hostname)
        return self.dataset[hostname]

    def sanitize_domain(self, domain):
        """Obfuscate the domainname, broken out into subdomains. Top-level
        domains are ignored.
        """
        for _skip in self.ignore_matches:
            # don't obfuscate vendor domains
            if re.match(_skip, '.'.join(domain)):
                return '.'.join(domain)
        top_domain = domain[-1].lower()
        dname = '.'.join(domain[0:-1]).lower()
        ob_domain = self._new_obfuscated_domain(dname)
        ob_domain = '.'.join([ob_domain, top_domain])
        self.dataset['.'.join(domain)] = ob_domain
        return ob_domain

    def _new_obfuscated_domain(self, dname):
        """Generate an obfuscated domain for each subdomain name given
        """
        if dname not in self._domains:
            self._domains[dname] = "obfuscateddomain%s" % self.domain_count
            self.domain_count += 1
        return self._domains[dname]
