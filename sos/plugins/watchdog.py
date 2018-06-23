# Copyright (C) 2018 Red Hat, Inc., Reid Wahl <nwahl@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

from glob import glob
import os


class Watchdog(Plugin, RedHatPlugin):
    """Watchdog information."""
    plugin_name = 'watchdog'
    profiles = ('system',)
    packages = ('watchdog',)

    option_list = [
        ('conf_file', 'watchdog config file', 'fast', '/etc/watchdog.conf'),
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
        conf_file = self.get_option('conf_file')
        log_dir = '/var/log/watchdog'

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
            log_files = glob(os.path.join(log_dir, '*'))
        else:
            log_files = (glob(os.path.join(log_dir, '*.stdout')) +
                         glob(os.path.join(log_dir, '*.stderr')))

        self.add_copy_spec(log_files)

# vim: set et ts=4 sw=4 :
