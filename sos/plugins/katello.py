# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin
from pipes import quote


class Katello(Plugin, RedHatPlugin):
    """Katello application life-cycle management"""

    plugin_name = 'katello'
    packages = ('katello',)

    def setup(self):
        self.add_copy_spec([
            "/var/log/httpd/katello-reverse-proxy_access_ssl.log*",
            "/var/log/httpd/katello-reverse-proxy_error_ssl.log*"
        ])

        cert = "/etc/pki/katello/qpid_client_striped.crt"
        self.add_cmd_output([
            "qpid-stat -%s --ssl-certificate=%s -b amqps://localhost:5671" %
            (opt, cert) for opt in "quc"
        ])

        kat_db = self.build_query_cmd(
            "select id,name,checksum_type,updated_at from katello_repositories"
        )
        self.add_cmd_output(kat_db, suggest_filename="katello_repositories")

        db_size = self.build_query_cmd(
            "SELECT table_name, pg_size_pretty(total_bytes) AS total, "
            "pg_size_pretty(index_bytes) AS INDEX , "
            "pg_size_pretty(toast_bytes) AS toast, pg_size_pretty(table_bytes)"
            " AS TABLE FROM ( SELECT *, "
            "total_bytes-index_bytes-COALESCE(toast_bytes,0) AS table_bytes "
            "FROM (SELECT c.oid,nspname AS table_schema, relname AS "
            "TABLE_NAME, c.reltuples AS row_estimate, "
            "pg_total_relation_size(c.oid) AS total_bytes, "
            "pg_indexes_size(c.oid) AS index_bytes, "
            "pg_total_relation_size(reltoastrelid) AS toast_bytes "
            "FROM pg_class c LEFT JOIN pg_namespace n ON "
            "n.oid = c.relnamespace WHERE relkind = 'r') a) a order by "
            "total_bytes DESC"
        )
        self.add_cmd_output(db_size, suggest_filename="db_table_size")

    def build_query_cmd(self, query):
        _cmd = "su postgres -c %s"
        _dbcmd = "psql foreman -c %s"
        dbq = _dbcmd % quote(query)
        return _cmd % quote(dbq)

# vim: set et ts=4 sw=4 :
