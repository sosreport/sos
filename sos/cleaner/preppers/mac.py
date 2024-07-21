# Copyright 2023 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.cleaner.preppers import SoSPrepper


class MacPrepper(SoSPrepper):
    """
    Prepper for sourcing the host's MAC address in order to prep the mapping.
    """

    name = 'mac'

    def _get_mac_file_list(self, archive):
        if archive.is_sos:
            return ['sos_commands/networking/ip_-d_address']
        if archive.is_insights:
            return ['data/insights_commands/ip_addr']
        return []

# vim: set et ts=4 sw=4 :
