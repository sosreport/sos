# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class KataContainers(Plugin, IndependentPlugin):

    short_desc = 'Kata Containers configuration'

    plugin_name = 'kata_containers'
    profiles = ('system', 'virt', 'container')
    packages = ('kata-containers',)

    def setup(self):
        self.limit = self.get_option('log_size')

        if self.get_option('all_logs'):
            # no limit on amount of data recorded
            self.limit = None

        self.add_cmd_output('kata-runtime kata-env')

        config_files = set()

        # start with the default file locations
        config_files.add('/etc/kata-containers/configuration.toml')
        config_files.add(
                '/usr/share/defaults/kata-containers/configuration.toml')

        # obtain a list of config files by asking the runtime
        cmd = 'kata-runtime --kata-show-default-config-paths'
        configs = self.collect_cmd_output(cmd)
        if configs and configs['status']:
            for config in configs['output'].splitlines():
                if config != "":
                    config_files.add(config)

            self.add_copy_spec(config_files)

# vim: set et ts=4 sw=4 :
