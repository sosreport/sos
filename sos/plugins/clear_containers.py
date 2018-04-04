# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import re

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin, \
        SuSEPlugin


class ClearContainers(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin,
                      SuSEPlugin):
    """Intel(R) Clear Containers configuration
    """

    plugin_name = 'clear_containers'
    profiles = ('system', 'virt')

    runtime = 'cc-runtime'
    packages = (runtime,)

    def attach_cc_config_files(self):

        # start with the default file locations
        config_files = [
                '/etc/clear-containers/configuration.toml'
                '/usr/share/defaults/clear-containers/configuration.toml'
        ]

        # obtain a list of config files by asking the runtime
        cmd = '{} --cc-show-default-config-paths'.format(self.runtime)
        configs = self.get_command_output(cmd)['output']

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
        output = self.get_command_output(cmd)['output']
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
        self.add_journal(units="cc-proxy")
        self.add_journal(identifier="cc-shim")
