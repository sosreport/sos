# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


class OpenStackMasakari(Plugin, UbuntuPlugin):

    short_desc = 'OpenStack Masakari'
    plugin_name = "openstack_masakari"
    profiles = ('openstack', 'openstack_controller')

    packages = (
        'masakari-engine',
        'masakari-api',
        'python3-masakari',
    )

    services = ('masakari-engine', )

    config_dir = "/etc/masakari"

    def setup(self):

        masakari_cmd = "masakari-manage --config-dir"\
                       f"{self.config_dir} db version"
        self.add_cmd_output(
            masakari_cmd,
            suggest_filename="masakari_db_version"
        )

        self.add_copy_spec([
            self.config_dir,
        ])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/masakari/*",
                "/var/log/apache2/masakari*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/masakari/*.log",
                "/var/log/apache2/masakari*.log",
            ])

        self.add_file_tags({
            f"{self.config_dir}/masakari.conf": "masakari_conf"
        })

    def postproc(self):
        protect_keys = [".*password.*", "transport_url",
                        "memcache_secret_key", "rabbit_password"]
        connection_keys = ["connection", "sql_connection"]

        join_con_keys = "|".join(connection_keys)

        self.do_path_regex_sub(
            f"{self.config_dir}/*",
            fr"(^\s*({'|'.join(protect_keys)})\s*=\s*)(.*)",
            r"\1*********"
        )
        self.do_path_regex_sub(
            f"{self.config_dir}/*",
            fr"(^\s*({join_con_keys})\s*=\s*(.*)://(\w*):)(.*)(@(.*))",
            r"\1*********\6"
        )


# vim: et ts=4 sw=4
