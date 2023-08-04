# Copyright (C) 2023 Red Hat, Inc., Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Coredump(Plugin, IndependentPlugin):

    short_desc = 'Retrieve coredump information'

    plugin_name = "coredump"
    profiles = ('system', 'debug')
    packages = ('systemd-udev', 'systemd-coredump')

    option_list = [
        PluginOpt("detailed", default=False,
                  desc="collect detailed information for every report")
    ]

    def setup(self):
        self.add_copy_spec([
            "/etc/systemd/coredump.conf",
            "/etc/systemd/coredump.conf.d/",
            "/run/systemd/coredump.conf.d/",
            "/usr/lib/systemd/coredump.conf.d/"
        ])

        self.add_cmd_output("coredumpctl dump")

        coredump_list = self.collect_cmd_output("coredumpctl list")
        if self.get_option("detailed") and coredump_list['status'] == 0:
            for line in coredump_list["output"].splitlines()[1:]:
                self.add_cmd_output("coredumpctl info "
                                    f"{line.split()[4]}")

# vim: set et ts=4 sw=4 :
