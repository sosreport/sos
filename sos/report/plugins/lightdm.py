# Copyright (C) 2015 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class LightDm(Plugin, IndependentPlugin):

    short_desc = 'Light Display Manager'
    packages = ('lightdm', )
    profiles = ('desktop', )
    services = ('lightdm', )
    plugin_name = 'lightdm'

    def setup(self):
        self.add_copy_spec([
            "/etc/lightdm/lightdm.conf",
            "/etc/lightdm/users.conf"
        ])
        if not self.get_option("all_logs"):
            self.add_copy_spec("/var/log/lightdm/lightdm.log")
            self.add_copy_spec("/var/log/lightdm/x-0-greeter.log")
            self.add_copy_spec("/var/log/lightdm/x-0.log")
        else:
            self.add_copy_spec("/var/log/lightdm")

# vim: set et ts=4 sw=4 :
