# Copyright Red Hat 2020, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.collector.hosts import SosHost


class DebianHost(SosHost):
    '''Base class for defining Debian based systems'''

    distribution = 'Debian'
    releases = ['ubuntu', 'debian']
    package_manager = {
        'name': 'dpkg',
        'query': "dpkg-query -W -f='${Package}-${Version}\\\n' "
    }
    sos_pkg_name = 'sosreport'
    sos_bin_path = '/usr/bin/sosreport'

    def check_enabled(self, rel_string):
        for release in self.releases:
            if release in rel_string:
                return True
        return False
# vim:ts=4 et sw=4
