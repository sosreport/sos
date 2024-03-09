# Copyright (C) 2015 Red Hat, Inc., Abhijeet Kasurde <akasurde@redhat.com>
# Copyright (C) 2017 Red Hat, Inc., Martin Schuppert <mschuppe@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Redis(Plugin, IndependentPlugin):

    short_desc = 'Redis, in-memory data structure store'

    plugin_name = 'redis'
    profiles = ('services',)

    packages = ('redis',)

    var_puppet_gen = "/var/lib/config-data/puppet-generated/redis"

    def setup(self):
        self.add_copy_spec([
            "/etc/redis.conf",
            self.var_puppet_gen + "/etc/redis*",
            self.var_puppet_gen + "/etc/redis/",
            self.var_puppet_gen + "/etc/security/limits.d/"
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
        for path in ["/etc/", self.var_puppet_gen + "/etc/"]:
            self.do_file_sub(
                path + "redis.conf",
                r"(masterauth|requirepass)\s.*",
                r"\1 ********"
            )

# vim: set et ts=4 sw=4 :
