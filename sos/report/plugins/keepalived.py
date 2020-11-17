# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Keepalived(Plugin, IndependentPlugin):

    short_desc = 'Keepalived routing server'

    plugin_name = 'keepalived'
    profiles = ('webserver', 'network', 'cluster')

    packages = ('keepalived',)

    def setup(self):
        self.add_copy_spec([
            "/etc/keepalived/keepalived.conf",
            "/etc/sysconfig/keepalived"
        ])

# vim: set et ts=4 sw=4 :
