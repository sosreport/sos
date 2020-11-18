# Copyright (C) 2015 Red Hat, Inc., Abhijeet Kasurde <akasurde@redhat.com>
# Copyright (C) 2017 Red Hat, Inc., Martin Schuppert <mschuppe@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, SCLPlugin


class Redis(Plugin, SCLPlugin):

    short_desc = 'Redis, in-memory data structure store'

    plugin_name = 'redis'
    profiles = ('services',)

    packages = ('redis', 'rh-redis32', 'rh-redis5')

    var_puppet_gen = "/var/lib/config-data/puppet-generated/redis"

    def setup(self):
        self.add_copy_spec([
            "/etc/redis.conf",
            self.var_puppet_gen + "/etc/redis*",
            self.var_puppet_gen + "/etc/redis/",
            self.var_puppet_gen + "/etc/security/limits.d/"
        ])

        for pkg in self.packages[1:]:
            scl = pkg.split('rh-redis*-')[0]
            self.add_copy_spec_scl(scl, [
                '/etc/redis.conf',
                '/etc/redis.conf.puppet',
                '/etc/redis-sentinel.conf',
                '/etc/redis-sentinel.conf.puppet',
                '/var/log/redis/sentinel.log',
                '/var/log/redis/redis.log'
            ])

        self.add_cmd_output("redis-cli info")
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/redis/redis.log*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/redis/redis.log",
            ])

    def postproc(self):
        for path in ["/etc/",
                     self.var_puppet_gen + "/etc/",
                     "/etc/opt/rh/rh-redis32/",
                     "/etc/opt/rh/rh-redis5/"]:
            self.do_file_sub(
                path + "redis.conf",
                r"(masterauth\s).*",
                r"\1********"
            )
            self.do_file_sub(
                path + "redis.conf",
                r"(requirepass\s).*",
                r"requirepass = ********"
            )

# vim: set et ts=4 sw=4 :
