# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.cleaner.parsers import SoSCleanerParser
from sos.cleaner.mappings.ip_map import SoSIPMap


class SoSIPParser(SoSCleanerParser):
    """Handles parsing for IP addresses"""

    name = 'IP Parser'
    regex_patterns = [
        # IPv4 with or without CIDR
        r'((?<!(-|\.|\d))([0-9]{1,3}\.){3}([0-9]){1,3}(\/([0-9]{1,2}))?)'
    ]
    skip_line_patterns = [
        # don't match package versions recorded in journals
        r'.*dnf\[.*\]:'
    ]
    map_file_key = 'ip_map'
    prep_map_file = 'sos_commands/networking/ip_-o_addr'

    def __init__(self, conf_file=None):
        self.mapping = SoSIPMap()
        super(SoSIPParser, self).__init__(conf_file)
