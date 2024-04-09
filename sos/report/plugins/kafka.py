# Copyright (C) 2024 Alejandro Santoyo <alejandro.santoyo@canonical.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.report.plugins import Plugin, UbuntuPlugin


class Kafka(Plugin, UbuntuPlugin):
    """
    This plugin collects log and configuration files, and also basic
    installation information (e.g., `snap info`) for Apache Kafka.
    """

    short_desc = 'Apache Kafka plugin'
    plugin_name = 'kafka'
    profiles = ('services',)
    packages = ('charmed-kafka',)
    services = ('kafka',)
    is_snap = False

    def _is_snap_installed(self):
        kafka_pkg = self.policy.package_manager.pkg_by_name('charmed-kafka')
        if kafka_pkg:
            return kafka_pkg['pkg_manager'] == 'snap'
        return False

    def setup(self):
        self.is_snap = self._is_snap_installed()
        log_file_pattern = "*.log*" if self.get_option("all_logs") else "*.log"

        if self.is_snap:
            self.add_cmd_output('snap info charmed-kafka')

            log_path = "/var/snap/charmed-kafka/common/var/log/kafka/"
            config_path = "/var/snap/charmed-kafka/current/etc/kafka/"
        else:
            log_path = "/usr/local/kafka/logs/"
            config_path = "/usr/local/kafka/config/"

        self.add_copy_spec([
            log_path + log_file_pattern,
            config_path,
        ])

    def postproc(self):
        protect_keys = ["password", "username",]
        config_path = (
            "/var/snap/charmed-kafka/current/etc/kafka/"
            if self.is_snap
            else "/usr/local/kafka/config/"
        )

        # get the absolute paths for all files in the config dir
        # (considering nested directories) and run do_path_regex_sub()
        # on each file to obfuscate the keys in protect_keys
        regexp = fr"(^\s*({'|'.join(protect_keys)})\s*=\s*)(.*)"
        for root, _, files in os.walk(config_path):
            for file in files:
                self.do_path_regex_sub(os.path.join(root, file),
                                       regexp, r"\1*********")

# vim: set et ts=4 sw=4 :
