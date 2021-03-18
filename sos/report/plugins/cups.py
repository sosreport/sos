# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from re import compile
from sos.report.plugins import Plugin, IndependentPlugin


class Cups(Plugin, IndependentPlugin):

    short_desc = 'CUPS IPP print service'

    plugin_name = 'cups'
    profiles = ('hardware',)

    packages = ('cups',)

    def get_jids(self, dir="/var/spool/cups", n_jids=10,
                 exists_f=os.path.exists, listdir_f=os.listdir):
        jids = []

        if not exists_f(dir):
            return

        spool_files = listdir_f(dir)

        jid_pattern = compile(r'c0*')

        for file in spool_files:
            matched = jid_pattern.search(file)
            if not matched:
                continue
            jids.append(file[matched.span()[1]:])

        return jids[-n_jids:]

    def get_jid_strings(self):
        jid_strings = []

        jids = self.get_jids()

        if not jids:
            return

        jid_strings = ["JID={}".format(jid) for jid in jids]

        return jid_strings

    def setup(self):
        if not self.get_option("all_logs"):
            self.add_copy_spec("/var/log/cups/access_log")
            self.add_copy_spec("/var/log/cups/error_log")
            self.add_copy_spec("/var/log/cups/page_log")
        else:
            self.add_copy_spec("/var/log/cups")

        self.add_copy_spec([
            "/etc/cups/*.conf",
            "/etc/cups/*.types",
            "/etc/cups/lpoptions",
            "/etc/cups/ppd/*.ppd"
        ])

        self.add_cmd_output([
            "lpstat -t",
            "lpstat -s",
            "lpstat -d"
        ])

        self.add_journal(units="cups")

        jid_arguments = self.get_jid_strings()

        if not jid_arguments:
            return

        for jid_arg in jid_arguments:
            self.add_journal(units="cups", otherargs=[jid_arg])

# vim: set et ts=4 sw=4 :
