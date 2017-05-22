# Copyright (C) 2016 Archit Sharma <archit.sh@redhat.com>
#
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
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Collectd(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    '''
    Collectd config collector
    '''
    plugin_name = "collectd"
    profiles = ('services', 'webserver')

    packages = ('collectd',)

    def setup(self):
        self.add_copy_spec([
            '/etc/collectd.conf',
            '/etc/collectd.d/*.conf',
        ])

        p = re.compile('^LoadPlugin.*')
        try:
            with open("/etc/collectd.conf") as f:
                for line in f:
                    if p.match(line):
                        self.add_alert("Active Plugin found: %s" %
                                       line.split()[-1])
        except IOError as e:
            self._log_warn("could not open /etc/collectd.conf: %s" % e)

    def postproc(self):
        # add these to protect_keys if need be:
        # "Port", "[<]*Host",
        protect_keys = [
            "Password", "User",
            "[<]*URL", "Address"
        ]
        regexp = r"((?m)^[#]*\s*(%s)\s* \s*)(.*)" % "|".join(protect_keys)
        self.do_path_regex_sub(
            "/etc/collectd.d/*.conf",
            regexp, r'\1"*********"'
        )
        self.do_file_sub("/etc/collectd.conf", regexp, r'\1"*********"')

# vim: set et ts=4 sw=4 :
