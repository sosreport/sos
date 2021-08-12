# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Nginx(Plugin, IndependentPlugin):

    short_desc = 'nginx http daemon'
    plugin_name = "nginx"
    profiles = ('webserver',)
    packages = ('nginx',)

    option_list = [
        PluginOpt('log', default=False, desc='collect all nginx logs')
    ]

    def setup(self):
        # collect configuration dump and build options
        self.add_cmd_output([
            "nginx -V",
            "nginx -T"
        ])

        # collect configuration files and only the current log set by default
        self.add_copy_spec([
            "/etc/nginx/*",
            "/var/log/nginx/access.log",
            "/var/log/nginx/error.log",
        ])
        if self.get_option("log") or self.get_option("all_logs"):
            self.add_copy_spec("/var/log/nginx/*")

# vim: set et ts=4 sw=4 :
