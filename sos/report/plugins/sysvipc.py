# Copyright (C) 2007-2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class SysVIPC(Plugin, IndependentPlugin):

    short_desc = 'SysV IPC'

    plugin_name = "sysvipc"
    profiles = ('system', 'services')

    def setup(self):
        self.add_copy_spec([
            "/proc/sysvipc/msg",
            "/proc/sysvipc/sem",
            "/proc/sysvipc/shm"
        ])
        self.add_cmd_output([
            "ipcs",
            "ipcs -u"
        ])

# vim: set et ts=4 sw=4 :
