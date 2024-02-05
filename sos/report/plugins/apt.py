# Copyright (C) 2013 Louis Bouchard <louis.bouchard@ubuntu.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin, DebianPlugin


class Apt(Plugin, DebianPlugin, UbuntuPlugin):

    short_desc = 'APT - advanced packaging tool'

    plugin_name = 'apt'
    profiles = ('system', 'sysmgmt', 'packagemanager')

    def setup(self):
        self.add_copy_spec([
            "/etc/apt",
            "/var/log/apt",
            "/var/log/unattended-upgrades"
        ])

        self.add_forbidden_path("/etc/apt/auth.conf")
        self.add_forbidden_path("/etc/apt/auth.conf.d/")

        self.add_cmd_output([
            "apt-get check",
            "apt-config dump",
            "apt-cache stats",
            "apt-cache policy"
        ])
        dpkg_result = self.exec_cmd(
            "dpkg-query -W -f='${binary:Package}\t${status}\n'"
        )
        dpkg_output = dpkg_result['output'].splitlines()
        pkg_list = ' '.join(
            [v.split('\t')[0] for v in dpkg_output if 'ok installed' in v])
        self.add_cmd_output(
            f"apt-cache policy {pkg_list}",
            suggest_filename="apt-cache_policy_details"
        )

    def postproc(self):
        super(Apt, self).postproc()
        self.do_file_sub(
            "/etc/apt/sources.list",
            r"(deb\shttp(s)?://)\S+:\S+(@.*)",
            r"\1******:******\3"
        )
        self.do_path_regex_sub(
            "/etc/apt/sources.list.d/",
            r"(deb\shttp(s)?://)\S+:\S+(@.*)",
            r"\1******:******\3"
        )


# vim: set et ts=4 sw=4 :
