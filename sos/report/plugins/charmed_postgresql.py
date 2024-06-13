# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import yaml

from sos.report.plugins import Plugin, UbuntuPlugin

SNAP_COMMON_PATH = "/var/snap/charmed-postgresql/common"
SNAP_CURRENT_PATH = "/var/snap/charmed-postgresql/current"

PATHS = {
    "POSTGRESQL_CONF": SNAP_COMMON_PATH + "/var/lib/postgresql",
    "POSTGRESQL_LOGS": SNAP_COMMON_PATH + "/var/log/postgresql",
    "PATRONI_CONF": SNAP_CURRENT_PATH + "/etc/patroni",
    "PATRONI_LOGS": SNAP_COMMON_PATH + "/var/log/patroni",
    "PGBACKREST_CONF": SNAP_CURRENT_PATH + "/etc/pgbackrest",
    "PGBACKREST_LOGS": SNAP_COMMON_PATH + "/var/log/pgbackrest",
    "PGBOUNCER_CONF": SNAP_CURRENT_PATH + "/etc/pgbouncer",
    "PGBOUNCER_LOGS": SNAP_COMMON_PATH + "/var/log/pgbouncer",
}

PATRONI_CONFIG_FILE = f"{PATHS['PATRONI_CONF']}/patroni.yaml"

RUNAS = "snap_daemon"
PSQL = "charmed-postgresql.psql"
PATRONICTL = "charmed-postgresql.patronictl"


class CharmedPostgreSQL(Plugin, UbuntuPlugin):

    short_desc = "Charmed PostgreSQL"
    plugin_name = "charmed_postgresql"
    packages = ('charmed-postgresql',)

    @property
    def patronictl_args(self) -> str:
        return f"--config-file {PATRONI_CONFIG_FILE}"

    @property
    def psql_args(self) -> str:
        return (f"-U {self.postgresql_username} "
                f"-h {self.postgresql_host} "
                f"-p {self.postgresql_port} "
                r"-d postgres -P pager=off")

    def setup(self):
        # --- FILE EXCLUSIONS ---

        # Keys and certificates
        self.add_forbidden_path([
            f"{PATHS['PATRONI_CONF']}/*.pem",
            f"{PATHS['PGBOUNCER_CONF']}/*.pem",
        ])

        # --- FILE INCLUSIONS ---

        self.add_copy_spec([
            f"{PATHS['POSTGRESQL_CONF']}/*.conf*",
            f"{PATHS['POSTGRESQL_LOGS']}",
            f"{PATHS['PATRONI_CONF']}/*.y*ml",
            f"{PATHS['PATRONI_LOGS']}",
            f"{PATHS['PGBACKREST_CONF']}",
            f"{PATHS['PGBACKREST_LOGS']}",
            f"{PATHS['PGBOUNCER_CONF']}",
            f"{PATHS['PGBOUNCER_LOGS']}",
        ])

        # --- SNAP LOGS ---

        self.add_journal("snap.charmed-postgresql.*")

        # --- SNAP INFO ---

        self.add_cmd_output(
            "snap info charmed-postgresql",
            suggest_filename="snap-info",
        )

        # Read and parse patroni config, finish setup if there are errors
        try:
            with open(PATRONI_CONFIG_FILE) as f:
                patroni_config = yaml.safe_load(f)
            self.patroni_cluster_name = patroni_config["scope"]
            postgresql = patroni_config["postgresql"]
            host_port = postgresql["connect_address"].split(":")
            self.postgresql_host, self.postgresql_port = host_port
            authentication = postgresql["authentication"]
            superuser = authentication["superuser"]
            self.postgresql_username = superuser["username"]
            self.postgresql_password = superuser["password"]
        except (OSError, yaml.YAMLError, TypeError,
                ValueError, KeyError, AttributeError) as error:
            self._log_warn("Can not run additional commands due to "
                           "an error on opening or parsing the config file "
                           f"{PATRONI_CONFIG_FILE}: "
                           f'{error}')
            return

        # --- TOPOLOGY ---

        self.add_cmd_output(
            (f"{PATRONICTL} {self.patronictl_args} "
             f"topology {self.patroni_cluster_name}"),
            suggest_filename="patroni-topology",
            runas=RUNAS,
        )

        # --- HISTORY ---

        self.add_cmd_output(
            (f"{PATRONICTL} {self.patronictl_args} "
             f"history {self.patroni_cluster_name}"),
            suggest_filename="patroni-history",
            runas=RUNAS,
        )

        # --- DCS CONFIGS ---

        self.add_cmd_output(
            (f"{PATRONICTL} {self.patronictl_args} "
             f"show-config {self.patroni_cluster_name}"),
            suggest_filename="patroni-dcs-config",
            runas=RUNAS,
        )

        # ADD DB PASSWORD TO ENVIRONMENT
        os.environ["PGPASSWORD"] = self.postgresql_password

        # --- DATABASES ---

        self.add_cmd_output(
            (f"{PSQL} {self.psql_args} "
             r"-c '\l+'"),
            suggest_filename="postgresql-databases",
            runas=RUNAS,
        )

        # --- USERS ---

        self.add_cmd_output(
            (f"{PSQL} {self.psql_args} "
             r"-c '\duS+'"),
            suggest_filename="postgresql-users",
            runas=RUNAS,
        )

        # --- TABLES ---

        self.add_cmd_output(
            (f"{PSQL} {self.psql_args} "
             r"-c '\dtS+'"),
            suggest_filename="postgresql-tables",
            runas=RUNAS,
        )

    def postproc(self):

        # REMOVE DB PASSWORD FROM ENVIRONMENT
        if "PGPASSWORD" in os.environ:
            del os.environ["PGPASSWORD"]

        # --- SCRUB PASSWORDS ---

        # Match lines containing password: and
        # followed by anything which may be enclosed with "
        self.do_path_regex_sub(
            f"{PATHS['PATRONI_CONF']}/*",
            r'(password: )"?.*"?',
            r'\1"*********"',
        )

        # https://pgbackrest.org/configuration.html#section-repository/option-repo-s3-key
        # https://pgbackrest.org/configuration.html#section-repository/option-repo-s3-key-secret
        self.do_path_regex_sub(
            f"{PATHS['PGBACKREST_CONF']}/pgbackrest.conf",
            r'(.*s3-key.*=).*',
            r'\1*********',
        )

        # https://www.pgbouncer.org/config.html#authentication-file-format
        self.do_path_regex_sub(
            f"{PATHS['PGBOUNCER_CONF']}/pgbouncer/userlist.txt",
            r'(".*" )".*"',
            r'\1"*********"',
        )
