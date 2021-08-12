# Copyright (C) 2015 Red Hat, Inc.,
# Pablo Iranzo Gomez <Pablo.Iranzo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin
from glob import glob


class Monit(Plugin, RedHatPlugin):

    short_desc = 'Monit monitoring daemon'
    packages = ('monit',)
    profiles = ('system',)
    plugin_name = 'monit'

    # Define configuration files
    # FIXME: direct globs will fail in container environments.
    monit_conf = glob("/etc/monit.d/*")
    monit_conf.append("/etc/monit.conf")
    monit_conf.append("/etc/monitrc")

    # Define log files
    monit_log = ["/var/log/monit.log"]

    def setup(self):
        self.add_cmd_output("monit status")
        self.add_copy_spec(self.monit_log + self.monit_conf)

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
