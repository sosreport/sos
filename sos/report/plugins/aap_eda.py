# Copyright (c) 2023 Rudnei Bertol Jr <rudnei@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class AAPEDAControllerPlugin(Plugin, RedHatPlugin):
    short_desc = 'AAP EDA Controller plugin'
    plugin_name = 'aap_eda'
    profiles = ('sysmgmt', 'ansible')
    packages = ('automation-eda-controller',
                'automation-eda-controller-server')

    def setup(self):
        self.add_copy_spec([
            "/etc/ansible-automation-platform/",
            "/var/log/ansible-automation-platform/eda/worker.log*",
            "/var/log/ansible-automation-platform/eda/scheduler.log*",
            "/var/log/ansible-automation-platform/eda/gunicorn.log*",
            "/var/log/ansible-automation-platform/eda/activation.log*",
            "/var/log/nginx/automationedacontroller.access.log*",
            "/var/log/nginx/automationedacontroller.error.log*",
        ])

        self.add_forbidden_path([
            "/etc/ansible-automation-platform/eda/SECRET_KEY",
            "/etc/ansible-automation-platform/eda/server.cert",
            "/etc/ansible-automation-platform/eda/server.key",
        ])

        self.add_cmd_output("aap-eda-manage --version")
        self.add_dir_listing([
            "/etc/ansible-automation-platform/",
            "/var/log/ansible-automation-platform/",
        ], recursive=True)

        self.add_cmd_output("su - eda -c 'export'",
                            suggest_filename="eda_export")

    def postproc(self):
        self.do_path_regex_sub(
            "/etc/ansible-automation-platform/eda/environment",
            r"(EDA_SECRET_KEY|EDA_DB_PASSWORD)(\s*)(=|:)(\s*)(.*)",
            r'\1\2\3\4********')

# vim: set et ts=4 sw=4 :
