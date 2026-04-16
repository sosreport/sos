# Copyright (C) 2026 Canonical Ltd.,
# Munir Siddiqui <munir.siddiqui@canonical.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class MysqlRouter(Plugin, IndependentPlugin):
    """
    Collects configuration and logs for MySQL Router.
    """

    short_desc = "MySQL Router"

    plugin_name = "mysql_router"
    profiles = ("services",)
    packages = ("mysql-router", "mysql-router-community",)

    def setup(self):
        super().setup()

        self.add_copy_spec([
            "/etc/mysqlrouter/",
            "/var/lib/mysql/*-mysql-router/mysqlrouter.conf",
        ])

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/mysqlrouter/*",
                "/var/lib/mysql/*-mysql-router/log/*",
            ])
        else:
            self.add_copy_spec([
                "/var/log/mysqlrouter/mysqlrouter.log",
                "/var/lib/mysql/*-mysql-router/log/mysqlrouter.log*",
            ])

# vim: set et ts=4 sw=4 :
