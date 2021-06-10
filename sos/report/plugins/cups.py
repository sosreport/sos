# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Cups(Plugin, IndependentPlugin):

    short_desc = 'CUPS IPP print service'

    plugin_name = 'cups'
    profiles = ('hardware',)
    services = ('cups', 'cups-browsed')
    packages = ('cups',)

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

# vim: set et ts=4 sw=4 :
