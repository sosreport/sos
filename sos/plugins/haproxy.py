# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin
from re import match

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


class HAProxy(Plugin, RedHatPlugin, DebianPlugin):
    """HAProxy load balancer
    """

    plugin_name = 'haproxy'
    profiles = ('webserver',)

    packages = ('haproxy',)

    def setup(self):
        var_puppet_gen = "/var/lib/config-data/puppet-generated/haproxy"
        self.add_copy_spec([
            "/etc/haproxy/haproxy.cfg",
            var_puppet_gen + "/etc/haproxy/haproxy.cfg"
        ])
        self.add_copy_spec("/etc/haproxy/conf.d/*")
        self.add_cmd_output("haproxy -f /etc/haproxy/haproxy.cfg -c")

        self.add_copy_spec("/var/log/haproxy.log")

        # collect haproxy overview - curl to IP address taken from haproxy.cfg
        # as 2nd word on line below "haproxy.stats"
        # so parse haproxy.cfg until "haproxy.stats" read, and take 2nd word
        # from the next line
        matched = None
        provision_ip = None
        try:
            for line in open("/etc/haproxy/haproxy.cfg").read().splitlines():
                if matched:
                    provision_ip = line.split()[1]
                    break
                matched = match(".*haproxy\.stats.*", line)
        except:
            # fallback when the cfg file is not accessible
            pass

        if not provision_ip:
            return

        # check if provision_ip contains port - if not, add default ":1993"
        if urlparse("http://"+provision_ip).port is None:
            provision_ip = provision_ip + ":1993"

        self.add_cmd_output("curl http://"+provision_ip+"/\;csv",
                            suggest_filename="haproxy_overview.txt")

# vim: set et ts=4 sw=4 :
