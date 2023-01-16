# Copyright (C) 2023 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class ForemanOpenSCAP(Plugin, IndependentPlugin):

    short_desc = 'Foreman OpenSCAP client'

    plugin_name = 'foreman_openscap'
    profiles = ('sysmgmt',)

    packages = ('rubygem-foreman_scap_client', 'ruby-foreman-scap-client')

    def setup(self):
        self.add_copy_spec("/etc/foreman_scap_client/config.yaml")

# vim: set et ts=4 sw=4 :
