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


class SoSMacMap(SoSMap):
    """Mapping store for MAC addresses

    MAC addresses added to this map will be broken into two halves, vendor and
    device like how MAC addresses are normally crafted. For the vendor hextets,
    obfuscation will take the form of 53:4f:53, or 'SOS' in hex. The following
    device hextets will be obfuscated by a series of suffixes starting from
    zeroes. For example a MAC address of '60:55:cb:4b:c9:27' may be obfuscated
    into '53:4f:53:00:00:1a' or similar.

    This map supports both 48-bit and 64-bit MAC addresses.

    48-bit address may take the form of either:

            MM:MM:MM:SS:SS:SS
            MM-MM-MM-SS-SS-SS

    For 64-bit addresses, the identifier injected by IPv6 standards is
    used in obfuscated returns. These addresses may take either of these forms:

        MM:MM:MM:FF:FE:SS:SS:SS
        MMMM:MMFF:FESS:SSSS

    All mapped mac addresses are converted to lower case.
    Dash delimited styles will be converted to colon-delimited style.
    """

    ignore_matches = [
        'ff:ff:ff:ff:ff:ff',
        '00:00:00:00:00:00'
    ]

    mac_template = '53:4f:53:%s:%s:%s'
    mac6_template = '53:4f:53:ff:fe:%s:%s:%s'
    mac6_quad_template = '534f:53ff:fe%s:%s%s'
    compile_regexes = False
    ob_hextets_cnt = 0

    def add(self, item):
        item = item.replace('-', ':').lower().strip('=.,').strip()
        return super().add(item)

    def get(self, item):
        item = item.replace('-', ':').lower().strip('=.,').strip()
        return super().get(item)

    def sanitize_item(self, item):
        """Obfuscate the device hextets, and append those to our 'vendor'
        hextet
        """
        hexdigits = "0123456789abdcef"
        self.ob_hextets_cnt += 1
        # we need to convert the counter to a triple of double hex-digits
        hextets = [
            self.ob_hextets_cnt >> 16,
            (self.ob_hextets_cnt >> 8) % 256,
            self.ob_hextets_cnt % 256
        ]
        hextets = tuple(f'{hexdigits[i//16]}{hexdigits[i % 16]}'
                        for i in hextets)

        # match 64-bit IPv6 MAC addresses matching MM:MM:MM:FF:FE:SS:SS:SS
        if re.match('(([0-9a-fA-F]{2}:){7}[0-9a-fA-F]{2})', item):
            return self.mac6_template % hextets
        # match 64-bit IPv6 MAC addresses matching MMMM:MMFF:FESS:SSSS
        if re.match('(([0-9a-fA-F]{4}:){3}([0-9a-fA-F]){4})', item):
            return self.mac6_quad_template % hextets
        # match 48-bit IPv4 MAC addresses
        if re.match('([0-9a-fA-F][:_]?){12}', item):
            return self.mac_template % hextets
        return None
