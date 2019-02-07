# Copyright (C) 2014 Red Hat, Inc., Sandro Bonazzola <sbonazzo@redhat.com>
# Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
# Copyright (C) 2010 Red Hat, Inc.

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import re
import signal


from sos.plugins import Plugin, RedHatPlugin
from sos.utilities import is_executable


# Class name must be the same as file name and method names must not change
class Ovirt(Plugin, RedHatPlugin):
    """oVirt Engine"""

    plugin_name = "ovirt"
    profiles = ('virt',)

    packages = (
        'ovirt-engine',
        'ovirt-engine-dwh',
        'ovirt-engine-reports',
        'ovirt-scheduler-proxy',
        'rhevm',
        'rhevm-dwh',
        'rhevm-reports'
    )

    DB_PASS_FILES = re.compile(
        flags=re.VERBOSE,
        pattern=r"""
        ^/etc/
        (rhevm|ovirt-engine|ovirt-engine-dwh)/
        (engine.conf|ovirt-engine-dwhd.conf)
        (\.d/.+.conf.*?)?$
        """
    )

    DEFAULT_SENSITIVE_KEYS = (
        'ENGINE_DB_PASSWORD:ENGINE_PKI_TRUST_STORE_PASSWORD:'
        'ENGINE_PKI_ENGINE_STORE_PASSWORD:DWH_DB_PASSWORD'
    )

    option_list = [
        ('jbosstrace', 'Enable oVirt Engine JBoss stack trace collection',
         '', True),
        ('sensitive_keys', 'Sensitive keys to be masked',
         '', DEFAULT_SENSITIVE_KEYS),
        ('heapdump', 'Collect heap dumps from /var/log/ovirt-engine/dump/',
         '', False)
    ]

    def setup(self):
        if self.get_option('jbosstrace') and self.is_installed('ovirt-engine'):
            engine_pattern = r"^ovirt-engine\ -server.*jboss-modules.jar"
            pgrep = "pgrep -f '%s'" % engine_pattern
            lines = self.call_ext_prog(pgrep)['output'].splitlines()
            engine_pids = [int(x) for x in lines]
            if not engine_pids:
                self.soslog.error('Unable to get ovirt-engine pid')
                self.add_alert('Unable to get ovirt-engine pid')
            for pid in engine_pids:
                try:
                    # backtrace written to '/var/log/ovirt-engine/console.log
                    os.kill(pid, signal.SIGQUIT)
                except OSError as e:
                    self.soslog.error('Unable to send signal to %d' % pid, e)

        self.add_forbidden_path([
            '/etc/ovirt-engine/.pgpass',
            '/etc/rhevm/.pgpass'
        ])

        if not self.get_option('heapdump'):
            self.add_forbidden_path('/var/log/ovirt-engine/dump')
            self.add_cmd_output('ls -l /var/log/ovirt-engine/dump/')

        self.add_cmd_output([
            # Copy all engine tunables and domain information
            "engine-config --all",
            # clearer diff from factory defaults (only on ovirt>=4.2.8)
            "engine-config -d"
        ])

        # 3.x line uses engine-manage-domains, 4.x uses ovirt-aaa-jdbc-tool
        manage_domains = 'engine-manage-domains'
        extensions_tool = 'ovirt-engine-extensions-tool'
        jdbc_tool = 'ovirt-aaa-jdbc-tool'

        if is_executable(manage_domains):
            self.add_cmd_output('%s list' % manage_domains)
        if is_executable(extensions_tool):
            self.add_cmd_output('%s info list-extensions' % extensions_tool)
        if is_executable('ovirt-aaa-jdbc-tool'):
            subcmds = [
                'query --what=user',
                'query --what=group',
                'settings show'
            ]

            self.add_cmd_output(['%s %s' % (jdbc_tool, sc) for sc in subcmds])

        # Copy engine config files.
        self.add_copy_spec([
            "/etc/ovirt-engine",
            "/etc/rhevm/",
            "/etc/ovirt-engine-dwh",
            "/etc/ovirt-engine-reports",
            "/var/log/ovirt-engine",
            "/var/log/ovirt-engine-dwh",
            "/var/log/ovirt-engine-reports",
            "/var/log/ovirt-scheduler-proxy",
            "/var/log/rhevm",
            "/etc/sysconfig/ovirt-engine",
            "/usr/share/ovirt-engine/conf",
            "/var/log/ovirt-guest-agent",
            "/var/lib/ovirt-engine/setup-history.txt",
            "/var/lib/ovirt-engine/setup/answers",
            "/var/lib/ovirt-engine/external_truststore",
            "/var/tmp/ovirt-engine/config",
            "/var/lib/ovirt-engine/jboss_runtime/config",
            "/var/lib/ovirt-engine-reports/jboss_runtime/config"
        ])

    def postproc(self):
        """
        Obfuscate sensitive keys.
        """
        self.do_file_sub(
            "/etc/ovirt-engine/engine-config/engine-config.properties",
            r"Password.type=(.*)",
            r"Password.type=********"
        )
        self.do_file_sub(
            "/etc/rhevm/rhevm-config/rhevm-config.properties",
            r"Password.type=(.*)",
            r"Password.type=********"
        )

        engine_files = (
            'ovirt-engine.xml',
            'ovirt-engine_history/current/ovirt-engine.v1.xml',
            'ovirt-engine_history/ovirt-engine.boot.xml',
            'ovirt-engine_history/ovirt-engine.initial.xml',
            'ovirt-engine_history/ovirt-engine.last.xml',
        )
        for filename in engine_files:
            self.do_file_sub(
                "/var/tmp/ovirt-engine/config/%s" % filename,
                r"<password>(.*)</password>",
                r"<password>********</password>"
            )

        self.do_file_sub(
            "/etc/ovirt-engine/redhatsupportplugin.conf",
            r"proxyPassword=(.*)",
            r"proxyPassword=********"
        )

        passwd_files = [
            "logcollector.conf",
            "imageuploader.conf",
            "isouploader.conf"
        ]
        for conf_file in passwd_files:
            conf_path = os.path.join("/etc/ovirt-engine", conf_file)
            self.do_file_sub(
                conf_path,
                r"passwd=(.*)",
                r"passwd=********"
            )
            self.do_file_sub(
                conf_path,
                r"pg-pass=(.*)",
                r"pg-pass=********"
            )

        sensitive_keys = self.DEFAULT_SENSITIVE_KEYS
        # Handle --alloptions case which set this to True.
        keys_opt = self.get_option('sensitive_keys')
        if keys_opt and keys_opt is not True:
            sensitive_keys = keys_opt
        key_list = [x for x in sensitive_keys.split(':') if x]
        for key in key_list:
            self.do_path_regex_sub(
                self.DB_PASS_FILES,
                r'{key}=(.*)'.format(key=key),
                r'{key}=********'.format(key=key)
            )

        # Answer files contain passwords
        for key in (
            'OVESETUP_CONFIG/adminPassword',
            'OVESETUP_CONFIG/remoteEngineHostRootPassword',
            'OVESETUP_DWH_DB/password',
            'OVESETUP_DB/password',
            'OVESETUP_REPORTS_CONFIG/adminPassword',
            'OVESETUP_REPORTS_DB/password',
        ):
            self.do_path_regex_sub(
                r'/var/lib/ovirt-engine/setup/answers/.*',
                r'{key}=(.*)'.format(key=key),
                r'{key}=********'.format(key=key)
            )

        # aaa profiles contain passwords
        protect_keys = [
            "vars.password",
            "pool.default.auth.simple.password",
            "pool.default.ssl.truststore.password",
            "config.datasource.dbpassword"
        ]
        regexp = r"((?m)^\s*#*(%s)\s*=\s*)(.*)" % "|".join(protect_keys)

        self.do_path_regex_sub(r"/etc/ovirt-engine/aaa/.*\.properties", regexp,
                               r"\1*********")

# vim: expandtab tabstop=4 shiftwidth=4
