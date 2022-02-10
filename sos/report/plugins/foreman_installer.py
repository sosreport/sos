# Copyright (C) 2021 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin)


class ForemanInstaller(Plugin, DebianPlugin, UbuntuPlugin):

    short_desc = 'Foreman installer and maintainer'

    plugin_name = 'foreman_installer'
    profiles = ('sysmgmt',)
    packages = ('foreman-installer', 'rubygem-foreman_maintain')

    def setup(self):
        self.add_copy_spec([
            "/etc/foreman-installer/*",
            "/var/log/foreman-installer/*",
            "/var/log/foreman-maintain/*",
            "/var/lib/foreman-maintain/data.yml",
            "/etc/foreman-maintain/foreman_maintain.yml",
            # specifically collect .applied files
            # that would be skipped otherwise as hidden files
            "/etc/foreman-installer/scenarios.d/*/.applied",
        ])

        # skip collecting individual migration scripts;
        # .applied file in each dir is still
        self.add_forbidden_path(
                "/etc/foreman-installer/scenarios.d/*.migrations/*.rb"
        )

        self.add_cmd_output([
            'foreman-maintain service status',
        ])

    def postproc(self):
        install_logs = "/var/log/foreman-installer/"
        logsreg = r"((foreman.*)?(\"::(foreman(.*?)|katello).*)?((::(.*)::.*" \
                  r"(passw|cred|token|secret|key).*(\")?:)|(storepass )" \
                  r"|(password =)))(.*)"
        self.do_path_regex_sub(install_logs, logsreg, r"\1 ********")
        # need to do two passes here, debug output has different formatting
        logs_debug_reg = (r"(\s)+(Found key: (\"(foreman(.*?)|katello)"
                          r"::(.*(token|secret|key|passw).*)\") value:) "
                          r"(.*)")
        self.do_path_regex_sub(install_logs, logs_debug_reg, r"\1 \2 ********")
        # also hide passwords in yet different formats
        self.do_path_regex_sub(
            install_logs,
            r"(\.|_|-)password(=\'|=|\", \")(\w*)",
            r"\1password\2********")
        self.do_path_regex_sub(
            "/var/log/foreman-installer/foreman-proxy*",
            r"(\s*proxy_password\s=) (.*)",
            r"\1 ********")
        self.do_path_regex_sub(
            "/var/log/foreman-maintain/foreman-maintain.log*",
            r"(((passw|cred|token|secret)=)|(password ))(.*)",
            r"\1********")
        # all scrubbing applied to configs must be applied to installer logs
        # as well, since logs contain diff of configs
        self.do_path_regex_sub(
            r"(/etc/foreman-(installer|maintain)/(.*)((conf)(.*)?))|(%s)"
            % install_logs,
            r"((\:|\s*)(passw|cred|token|secret|key).*(\:\s|=))(.*)",
            r"\1********")
        # yaml values should be alphanumeric
        self.do_path_regex_sub(
            r"(/etc/foreman-(installer|maintain)/(.*)((yaml|yml)(.*)?))|(%s)"
            % install_logs,
            r"((\:|\s*)(passw|cred|token|secret|key).*(\:\s|=))(.*)",
            r'\1"********"')


# Add Red Hat Insights tags for RedHatPlugin only

class RedHatForemanInstaller(ForemanInstaller, RedHatPlugin):

    def setup(self):

        self.add_file_tags({
            '/var/log/foreman-installer/satellite.log.*':
                ['insights_satellite_log' 'satellite_installer_log'],
            '/var/log/foreman-installer/capsule.log.*':
                ['insights_capsule_log' 'capsule_installer_log'],
        })

        super(RedHatForemanInstaller, self).setup()


# vim: set et ts=4 sw=4 :
