# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
                matched = match(r".*haproxy\.stats.*", line)
        except IOError:
            # fallback when the cfg file is not accessible
            pass

        if not provision_ip:
            return

        # check if provision_ip contains port - if not, add default ":1993"
        if urlparse("http://"+provision_ip).port is None:
            provision_ip = provision_ip + ":1993"

        self.add_cmd_output("curl http://"+provision_ip+r"/\;csv",
                            suggest_filename="haproxy_overview.txt")

# vim: set et ts=4 sw=4 :
