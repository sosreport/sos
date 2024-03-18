# Copyright (c) 2024 Pavel Moravec <pmoravec@redhat.com>
# Copyright (c) 2024 Lucas Benedito <lbenedit@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class AAPControllerPlugin(Plugin, RedHatPlugin):
    short_desc = 'AAP Automation Controller plugin'
    plugin_name = 'aap_controller'
    profiles = ('sysmgmt', 'ansible',)

    packages = ('automation-controller-venv-tower',
                'automation-controller-server',
                'automation-controller-ui',
                'automation-controller')
    commands = ('awx-manage',)
    services = ('automation-controller',)

    def setup(self):
        self.add_copy_spec([
            "/etc/tower/",
            "/etc/supervisord.conf",
            "/etc/supervisord.d/*",
            "/var/log/tower",
            "/var/log/nginx/automationcontroller.access.log*",
            "/var/log/nginx/automationcontroller.error.log*",
            "/var/log/supervisor",
            "/var/log/unattended-upgrades",
        ])

        self.add_forbidden_path([
            "/etc/tower/SECRET_KEY",
            "/etc/tower/*.key",
            "/etc/tower/*.cert",
            "/var/log/tower/profile",
        ])

        self.add_cmd_output([
            "awx-manage --version",
            "awx-manage list_instances",
            "awx-manage run_dispatcher --status",
            "awx-manage run_callback_receiver --status",
            "awx-manage check_license --data",
            "awx-manage run_wsbroadcast --status",
            "awx-manage run_wsrelay --status",
            "supervisorctl status",
            "/var/lib/awx/venv/awx/bin/pip freeze",
            "/var/lib/awx/venv/awx/bin/pip freeze -l",
            "/var/lib/awx/venv/ansible/bin/pip freeze",
            "/var/lib/awx/venv/ansible/bin/pip freeze -l",
            "tree -d /var/lib/awx",
            "ls -ll /var/lib/awx",
            "ls -ll /var/lib/awx/venv",
            "ls -ll /etc/tower",
            "umask -p",
        ])

    def postproc(self):
        # remove database password
        jreg = r"(\s*\'PASSWORD\'\s*:(\s))(?:\"){1,}(.+)(?:\"){1,}"
        repl = r"\1********"
        self.do_path_regex_sub("/etc/tower/conf.d/postgres.py", jreg, repl)

        # remove email password
        jreg = r"(EMAIL_HOST_PASSWORD\s*=)\'(.+)\'"
        repl = r"\1********"
        self.do_path_regex_sub("/etc/tower/settings.py", jreg, repl)

        # remove email password (if customized)
        jreg = r"(EMAIL_HOST_PASSWORD\s*=)\'(.+)\'"
        repl = r"\1********"
        self.do_path_regex_sub("/etc/tower/conf.d/custom.py", jreg, repl)

        # remove websocket secret
        jreg = r"(BROADCAST_WEBSOCKET_SECRET\s*=\s*)\"(.+)\""
        repl = r"\1********"
        self.do_path_regex_sub("/etc/tower/conf.d/channels.py", jreg, repl)


# vim: set et ts=4 sw=4 :
