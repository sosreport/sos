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
