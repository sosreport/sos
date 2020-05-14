# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.cleaner.parsers import SoSCleanerParser
from sos.cleaner.mappings.mac_map import SoSMacMap


class SoSMacParser(SoSCleanerParser):
    """Handles parsing for MAC addresses"""

    name = 'MAC Parser'
    regex_patterns = [
        # IPv6
        r'(([^:|-])([0-9a-fA-F]{2}(:|-)){7}[0-9a-fA-F]{2}(\s|$))',
        r'(([^:|-])([0-9a-fA-F]{4}(:|-)){3}[0-9a-fA-F]{4}(\s|$))',
        # IPv4, avoiding matching a substring within IPv6 addresses
        r'(([^:|-])([0-9a-fA-F]{2}([:-])){5}([0-9a-fA-F]){2}(\s|$))'
    ]
    map_file_key = 'mac_map'
    prep_map_file = 'sos_commands/networking/ip_-d_address'

    def __init__(self, conf_file=None):
        self.mapping = SoSMacMap()
        super(SoSMacParser, self).__init__(conf_file)
