# Copyright (C) 2018 Red Hat, Inc., Reid Wahl <nwahl@redhat.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt

from glob import glob


class Watchdog(Plugin, RedHatPlugin):

    short_desc = 'Watchdog information.'
    plugin_name = 'watchdog'
    profiles = ('system',)
    packages = ('watchdog',)

    option_list = [
        PluginOpt('conf_file', default='/etc/watchdog.conf',
                  desc='watchdog config file')
    ]

    def get_log_dir(self, conf_file):
        """Get watchdog log directory.

            Get watchdog log directory path configured in ``conf_file``.

            :returns: The watchdog log directory path.
            :returntype: str.
            :raises: IOError if ``conf_file`` is not readable.
        """
        log_dir = None

        with open(conf_file, 'r') as conf_f:
            for line in conf_f:
                line = line.split('#')[0].strip()

                try:
                    (key, value) = line.split('=', 1)
                    if key.strip() == 'log-dir':
                        log_dir = value.strip()
                except ValueError:
                    pass

        return log_dir

    def setup(self):
        """Collect watchdog information.

            Collect configuration files, custom executables for test-binary
            and repair-binary, and stdout/stderr logs.
        """
        conf_file = self.path_join(self.get_option('conf_file'))
        log_dir = self.path_join('/var/log/watchdog')

        # Get service configuration and sysconfig files
        self.add_copy_spec([
            conf_file,
            '/etc/sysconfig/watchdog',
        ])

        # Get custom executables
        self.add_copy_spec([
            '/etc/watchdog.d',
            '/usr/libexec/watchdog/scripts',
        ])

        # Get logs
        try:
            res = self.get_log_dir(conf_file)
            if res:
                log_dir = res
        except IOError as ex:
            self._log_warn("Could not read %s: %s" % (conf_file, ex))

        if self.get_option('all_logs'):
            log_files = glob(self.path_join(log_dir, '*'))
        else:
            log_files = (glob(self.path_join(log_dir, '*.stdout')) +
                         glob(self.path_join(log_dir, '*.stderr')))

        self.add_copy_spec(log_files)

        # Get output of "wdctl <device>" for each /dev/watchdog*
        for dev in glob(self.path_join('/dev/watchdog*')):
            self.add_cmd_output("wdctl %s" % dev)

# vim: set et ts=4 sw=4 :
