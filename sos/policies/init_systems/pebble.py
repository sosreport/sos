# Copyright (C) 2024 Canonical Ltd., Arif Ali <arif.ali@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.policies.init_systems import InitSystem
from sos.utilities import shell_out


class PebbleInit(InitSystem):
    """InitSystem abstraction for Pebble systems"""

    def __init__(self, chroot=None):
        super(PebbleInit, self).__init__(
            init_cmd='pebble',
            list_cmd='services',
            query_cmd='pebble services',
            chroot=chroot
        )
        self.load_all_services()

    def parse_query(self, output):
        for line in output.splitlines()[1:]:
            if line.split()[2] == 'active':
                return 'active'
        return 'unknown'

    def load_all_services(self):
        svcs = shell_out(self.list_cmd, chroot=self.chroot).splitlines()[1:]
        for line in svcs:
            try:
                name = line.split()[0]
                config = line.split()[1]
                self.services[name] = {
                    'name': name,
                    'config': config,
                }
            except IndexError:
                pass

    def is_running(self, name, default=False):
        try:
            svc = self.get_service_status(name)
            return svc['status'] == 'active'
        except Exception:
            return default

# vim: set et ts=4 sw=4 :
