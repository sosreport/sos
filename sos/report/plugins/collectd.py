# Copyright (C) 2016 Archit Sharma <archit.sh@redhat.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import re
from sos.report.plugins import Plugin, IndependentPlugin


class Collectd(Plugin, IndependentPlugin):

    short_desc = 'Collectd config collector'
    plugin_name = "collectd"
    profiles = ('services', 'webserver')

    # enable the plugin either when collectd package is installed
    # or being inside Super Proviledged Container that does not have
    # the package but logs to the host's logfile
    packages = ('collectd',)
    files = ('/var/log/containers/collectd/collectd.log',
             '/var/log/collectd/collectd.log')

    def setup(self):
        self.add_copy_spec([
            '/etc/collectd.conf',
            '/etc/collectd.d/*.conf',
            '/var/log/containers/collectd/collectd.log',
            '/var/lib/config-data/puppet-generated/collectd/etc/collectd.conf',
            '/var/lib/config-data/puppet-generated/collectd/etc/collectd.d/'
            + '*.conf',
        ])

        plugin = re.compile('^LoadPlugin.*')
        try:
            cfile = self.path_join("/etc/collectd.conf")
            with open(cfile, 'r', encoding='UTF-8') as file:
                for line in file:
                    if plugin.match(line):
                        self.add_alert("Active Plugin found: "
                                       f"{line.split()[-1]}")
        except IOError as err:
            self._log_warn(f"could not open /etc/collectd.conf: {err}")

    def postproc(self):
        # add these to protect_keys if need be:
        # "Port", "[<]*Host",
        protect_keys = [
            "Password", "User",
            "[<]*URL", "Address"
        ]
        regexp = fr"(^[#]*\s*({'|'.join(protect_keys)})\s* \s*)(.*)"
        self.do_path_regex_sub(
            "/etc/collectd.d/*.conf",
            regexp, r'\1"*********"'
        )
        self.do_file_sub("/etc/collectd.conf", regexp, r'\1"*********"')

# vim: set et ts=4 sw=4 :
