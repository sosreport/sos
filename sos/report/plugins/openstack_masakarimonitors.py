# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


class OpenStackMasakariMonitors(Plugin, UbuntuPlugin):

    short_desc = 'OpenStack Masakari Monitors'
    plugin_name = "openstack_masakarimonitors"
    profiles = ('openstack', 'openstack_controller')

    packages = ('masakari-monitors-common', )

    services = (
        'masakari-host-monitor',
        'masakari-instance-monitor',
        'masakari-process-monitor',
    )

    config_dir = "/etc/masakarimonitors"

    def setup(self):

        self.add_copy_spec([
            self.config_dir,
        ])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/masakarimonitors/*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/masakarimonitors/*.log",
            ])

        self.add_file_tags({
            f"{self.config_dir}/masakarimonitors.conf": "masakarimonitors_conf"
        })

    def postproc(self):
        protect_keys = [".*password.*"]

        self.do_path_regex_sub(
            f"{self.config_dir}/*",
            r"(^\s*(%s)\s*=\s*)(.*)" % "|".join(protect_keys),
            r"\1*********"
        )


# vim: et ts=4 sw=4
