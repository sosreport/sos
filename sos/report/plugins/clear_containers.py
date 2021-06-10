# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re

from sos.report.plugins import Plugin, IndependentPlugin


class ClearContainers(Plugin, IndependentPlugin):

    short_desc = 'Intel(R) Clear Containers configuration'

    plugin_name = 'clear_containers'
    profiles = ('system', 'virt', 'container')

    runtime = 'cc-runtime'
    packages = (runtime,)
    services = ('cc-proxy',)

    def attach_cc_config_files(self):

        # start with the default file locations
        config_files = [
                '/etc/clear-containers/configuration.toml'
                '/usr/share/defaults/clear-containers/configuration.toml'
        ]

        # obtain a list of config files by asking the runtime
        cmd = '{} --cc-show-default-config-paths'.format(self.runtime)
        configs = self.exec_cmd(cmd)['output']

        for config in configs.splitlines():
            if config != "":
                config_files.append(config)

        # get a unique list of config files
        config_files = set(config_files)

        self.add_copy_spec(config_files)

    def attach_cc_log_files(self):
        # start with the default global log
        log_files = [
            '/var/lib/clear-containers/runtime/runtime.log'
        ]

        # query the runtime to find the configured global log file
        cmd = '{} cc-env'.format(self.runtime)
        output = self.exec_cmd(cmd)['output']
        for line in output.splitlines():
            result = re.search(r'\bGlobalLogPath\b\s+=\s+"(.+)"', line)
            if result:
                global_logfile = result.group(1)
                if global_logfile:
                    log_files.append(global_logfile)
                break

        # get a unique list of log files
        log_files = set(log_files)

        self.add_copy_spec(log_files, self.limit)

    def setup(self):
        self.limit = self.get_option("log_size")

        if self.get_option("all_logs"):
            # no limit on amount of data recorded
            self.limit = None

        self.add_cmd_output('{} cc-env'.format(self.runtime))
        self.attach_cc_config_files()

        self.attach_cc_log_files()
        self.add_journal(identifier="cc-shim")

# vim: set et ts=4 sw=4 :
