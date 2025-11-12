# Copyright (c) 2024 Lucas Benedito <lbenedit@redhat.com>
# Copyright (c) 2025 Nagoor Shaik <nshaik@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class AAPGatewayPlugin(Plugin, RedHatPlugin):
    short_desc = 'AAP Gateway plugin'
    plugin_name = 'aap_gateway'
    profiles = ('sysmgmt', 'ansible',)

    packages = ('automation-gateway',
                'automation-gateway-config')
    commands = ('aap-gateway-manage',)
    services = ('automation-gateway',)

    def setup(self):
        self.add_copy_spec([
            "/var/log/supervisor",
            "/etc/ansible-automation-platform",
            "/etc/supervisord.d/",
            "/var/log/ansible-automation-platform/gateway/",
        ])

        self.add_forbidden_path([
            "/etc/ansible-automation-platform/gateway/SECRET_KEY",
            "/etc/ansible-automation-platform/gateway/*.key",
            "/etc/ansible-automation-platform/gateway/*.cert",
        ])

        self.add_cmd_output([
            "automation-gateway-service status",
            "aap-gateway-manage print_settings",
            "aap-gateway-manage authenticators",
            "aap-gateway-manage showmigrations",
            "aap-gateway-manage list_services",
            "aap-gateway-manage feature_flags --list",
            "aap-gateway-manage --version",
        ])
        self.add_dir_listing("/etc/ansible-automation-platform/",
                             recursive=True)

    def postproc(self):
        # remove database password
        jreg = r"(\s*'PASSWORD'\s*:\s*)('.*')"
        repl = r"\1********"
        self.do_path_regex_sub(
            "/etc/ansible-automation-platform/gateway/settings.py",
            jreg,
            repl)

        # Mask PASSWORD from print_settings command
        jreg = r'((["\']?PASSWORD["\']?\s*[:=]\s*)[rb]?["\'])(.*?)(["\'])'
        self.do_cmd_output_sub(
            "aap-gateway-manage print_settings",
            jreg,
            r'\1**********\4')

        # Mask SECRET_KEY from print_settings command
        jreg = r'((SECRET_KEY\s*=\s*)([rb]?["\']))(.*?)(["\'])'
        self.do_cmd_output_sub(
            "aap-gateway-manage print_settings",
            jreg,
            r'\1**********\5')

# vim: set et ts=4 sw=4 :
