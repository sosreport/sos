# Copyright 2023 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.cleaner.preppers import SoSPrepper


class IPPrepper(SoSPrepper):
    """
    This prepper is for IP network addresses. The aim of this prepper is to
    provide the file path for where the output of `ip addr` is saved.
    """

    name = 'ip'

    def _get_ipv6_file_list(self, archive):
        return self._get_ip_file_list(archive)

    def _get_ip_file_list(self, archive):
        _files = []
        if archive.is_sos:
            _files = ['sos_commands/networking/ip_-o_addr']
        elif archive.is_insights:
            _files = ['data/insights_commands/ip_addr']

        return _files

# vim: set et ts=4 sw=4 :
