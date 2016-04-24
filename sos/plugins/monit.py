# Copyright (C) 2015 Red Hat, Inc.,
# Pablo Iranzo Gomez <Pablo.Iranzo@redhat.com>

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


class Monit(Plugin, RedHatPlugin):
    """Monit monitoring daemon
    """
    packages = ('monit',)
    profiles = ('system')
    plugin_name = 'monit'

    # Define configuration files
    monit_conf = glob("/etc/monit.d/*")
    monit_conf.append("/etc/monit.conf")
    monit_conf.append("/etc/monitrc")

    # Define log files
    monit_log = ["/var/log/monit.log"]

    option_list = []

    def setup(self):
        self.add_cmd_output("monit status")
        self.add_copy_spec([self.monit_log, self.monit_conf])

    def postproc(self):
        # Post process the files included to scrub any
        # password or other sensitive data

        # usernames and emails are cleaned to not disclose any
        # confidential data

        for file in self.monit_conf:
            # Remove username:password from files
            self.do_file_sub(file,
                             r"allow (.*):(.*)",
                             r"allow ********:********"
                             )
            self.do_file_sub(file,
                             r"ALLOW (.*):(.*)",
                             r"ALLOW ********:********"
                             )
            # Remove MAILSERVER username/password
            self.do_file_sub(file,
                             r"username (\w)+",
                             r"username ********"
                             )
            self.do_file_sub(file,
                             r"password (\w)+",
                             r"password ********"
                             )
            self.do_file_sub(file,
                             r"USERNAME (\w)+",
                             r"USERNAME ********"
                             )
            self.do_file_sub(file,
                             r"PASSWORD (\w)+",
                             r"PASSWORD ********"
                             )

# vim: et ts=4 sw=4
