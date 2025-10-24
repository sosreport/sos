# Copyright (c) 2025 Rudnei Bertol Jr <rudnei@redhat.com>
# Copyright (c) 2025 Nagoor Shaik <nshaik@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin
from sos.utilities import sos_parse_version


class AAPEDAControllerPlugin(Plugin, RedHatPlugin):
    short_desc = 'AAP EDA Controller plugin'
    plugin_name = 'aap_eda'
    profiles = ('sysmgmt', 'ansible')
    packages = ('automation-eda-controller',
                'automation-eda-controller-server')

    def setup(self):

        pkg_name = 'automation-eda-controller'
        pkg = self.policy.package_manager.pkg_by_name(f'{pkg_name}')
        if pkg is not None:
            self.eda_pkg_ver = '.'.join(pkg['version'])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/etc/ansible-automation-platform/",
                "/var/log/ansible-automation-platform/eda/",
                "/var/log/nginx/automationedacontroller.access.log*",
                "/var/log/nginx/automationedacontroller.error.log*",
            ])
        else:
            self.add_copy_spec([
                "/etc/ansible-automation-platform/",
                "/var/log/ansible-automation-platform/eda/*.log",
                "/var/log/nginx/automationedacontroller.access.log",
                "/var/log/nginx/automationedacontroller.error.log",
            ])

        self.add_forbidden_path([
            "/etc/ansible-automation-platform/eda/SECRET_KEY",
            "/etc/ansible-automation-platform/eda/server.cert",
            "/etc/ansible-automation-platform/eda/server.key",
        ])

        self.add_cmd_output([
            "aap-eda-manage --version",
            "aap-eda-manage showmigrations",
        ])

        self.add_dir_listing([
            "/etc/ansible-automation-platform/",
            "/var/log/ansible-automation-platform/",
        ], recursive=True)

        self.add_cmd_output("su - eda -c 'env'",
                            suggest_filename="eda_environment")

        pkg_name = 'automation-eda-controller'
        pkg = self.policy.package_manager.pkg_by_name(f'{pkg_name}')

        # EDA version in 2.5 release starts with 1.1.0 version
        eda_pkg_ver = getattr(self, 'eda_pkg_ver', '0.0.0')
        if sos_parse_version(eda_pkg_ver) > sos_parse_version('1.0.99'):
            self.add_cmd_output([
                "automation-eda-controller-service status",
                "automation-eda-controller-event-stream-service status",
            ])
        else:
            # systemd service status which starts with "automation-eda"
            result = self.exec_cmd(
                'systemctl list-units --type=service \
                --no-legend automation-eda*'
            )
            if result['status'] == 0:
                for svc in result['output'].splitlines():
                    eda_svc = svc.split()
                    if not eda_svc:
                        continue
                    self.add_service_status(eda_svc[0])

    def postproc(self):
        # EDA Version in AAP 2.4 uses environment file to store configuration
        eda_pkg_ver = getattr(self, 'eda_pkg_ver', '0.0.0')
        if sos_parse_version(eda_pkg_ver) < sos_parse_version('1.0.99'):
            file_path = "/etc/ansible-automation-platform/eda/environment"
            regex = r"(EDA_SECRET_KEY|EDA_DB_PASSWORD)(\s*)(=|:)(\s*)(.*)"
            replacement = r'\1\2\3\4********'
        # EDA version in AAP 2.5 and above use yaml file for configuration
        else:
            file_path = "/etc/ansible-automation-platform/eda/settings.yaml"
            regex = r"(\s*)(PASSWORD|MQ_USER_PASSWORD|SECRET_KEY)(:\s*)(.*$)"
            replacement = r'\1\2\3********'

        self.do_path_regex_sub(file_path, regex, replacement)
# vim: set et ts=4 sw=4 :
