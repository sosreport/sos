# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re
from sos.cleaner.parsers import SoSCleanerParser
from sos.cleaner.mappings.ip_map import SoSIPMap


class SoSIPParser(SoSCleanerParser):
    """Handles parsing for IP addresses"""

    name = 'IP Parser'
    regex_pattern = re.compile(
        # IPv4 with or without CIDR
        # A slash followed by a non-CIDR suffix is used by some diagnostic
        # formats for address/port-service fields.  Limit the optional CIDR
        # to prefixes 0-32 so an invalid prefix cannot consume the first
        # port digits and cause the complete address match to be rejected.
        r'((?<!(-|\.|\d))([0-9]{1,3}\.){3}([0-9]){1,3}'
        r'(?:\/(?:[0-9]|[12][0-9]|3[0-2]))?(?![0-9]))'
    )
    skip_line_patterns = [
        # don't match package versions recorded in journals
        r'.*dnf\[.*\]:'
    ]

    parser_skip_files = [
        # skip these as version numbers will frequently look like IP addresses
        # when using regex matching
        'installed-debs',
        'installed-rpms',
        'sos_commands/dpkg',
        'sos_commands/python/pip_list',
        'sos_commands/rpm',
        'sos_commands/yum/.*list.*',
        'sos_commands/snappy/snap_list_--all',
        'sos_commands/vulkan/vulkaninfo',
        'etc/rhsm/facts/satellite.facts',
        'var/log/.*dnf.*',
        'var/log/.*packag.*',  # get 'packages' and 'packaging' logs
        '.*(version|release)(\\.txt)?$',  # obvious version files
    ]

    map_file_key = 'ip_map'
    compile_regexes = False

    def __init__(self, config, workdir, skip_cleaning_files=[]):
        self.mapping = SoSIPMap(workdir, self.regex_pattern)
        super().__init__(config, skip_cleaning_files)
