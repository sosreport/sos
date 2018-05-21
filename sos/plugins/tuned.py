# Copyright (C) 2014 Red Hat, Inc., Peter Portante <peter.portante@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Tuned(Plugin, RedHatPlugin):
    """Tuned system tuning daemon
    """
    packages = ('tuned',)
    profiles = ('system', 'performance')
    plugin_name = 'tuned'

    def setup(self):
        self.add_cmd_output([
            "tuned-adm list",
            "tuned-adm active",
            "tuned-adm recommend"
        ])
        self.add_copy_spec([
            "/etc/tuned.conf",
            "/etc/tune-profiles"
        ])
        self.add_copy_spec([
            "/etc/tuned",
            "/usr/lib/tuned",
            "/var/log/tuned/tuned.log"
        ])

# vim: set et ts=4 sw=4 :
