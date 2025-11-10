# Copyright 2022 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.cleaner.parsers import SoSCleanerParser
from sos.cleaner.mappings.ipv6_map import SoSIPv6Map


class SoSIPv6Parser(SoSCleanerParser):
    """Parser for handling IPv6 networks and addresses"""

    name = 'IPv6 Parser'
    map_file_key = 'ipv6_map'
    regex_patterns = [
        # Attention: note that this is a single long regex, not several entries
        # This is initially based off of two regexes from the Java library
        # for validating an IPv6 string. However, this is modified to begin and
        # end with a negative lookbehind to ensure that a substring of 'ed::'
        # is not extracted from a log message such as 'SomeFuncUsed::ADiffFunc'
        # that come components may log with. Further, we optionally try to grab
        # a trailing prefix for the network bits.
        r"(?<![:\\.\\-a-z0-9])((([0-9a-f]{1,4})(:[0-9a-f]{1,4}){7})|"
        r"(([0-9a-f]{1,4}(:[0-9a-f]{0,4}){0,5}))([^.])::(([0-9a-f]{1,4}"
        r"(:[0-9a-f]{1,4}){0,5})?)(\/\d{1,3})?)(?!([a-z0-9]|:[a-z0-9]))"
    ]
    parser_skip_files = [
        'etc/dnsmasq.conf.*',
        '.*modinfo.*',
    ]
    compile_regexes = False

    def __init__(self, config, workdir, skip_cleaning_files=[]):
        self.mapping = SoSIPv6Map(workdir)
        super().__init__(config, skip_cleaning_files)

    def get_map_contents(self):
        """Structure the dataset contents properly so that they can be reloaded
        on subsequent runs correctly.
        """
        _d = {
            'version': self.mapping.version,
            'networks': {}
        }
        for _, _net in self.mapping.networks.items():
            _d['networks'][_net.original_address] = {
                'obfuscated': _net.obfuscated_address,
                'hosts': {}
            }
            for host in _net.hosts:
                _ob_host = _net.hosts[host]
                _d['networks'][_net.original_address]['hosts'][host] = _ob_host

        return _d
