# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.#

import os

from sos.report.plugins import Plugin, PluginOpt, UbuntuPlugin


class CharmedMySQL(Plugin, UbuntuPlugin):
    """
    The Charmed MySQL plugin is used to collect MySQL configuration and logs
    from the Charmed MySQL snap package. It also collects MySQL Router
    and MySQL Shell configuration and logs where available,
    journal logs for the snap, and snap info.

    If the `dumpdbs` option is set to `True`, the plugin will also try and
    collect the names of the databases that the user has access to. The
    `mysql` user is used by default, but that can be set using the `dbuser`
    option. When using the `dumpdbs` option, you must then provide the
    password for the user using the `dbpass` option.
    """

    short_desc = "Charmed MySQL"
    plugin_name = "charmed_mysql"
    packages = ("charmed-mysql",)

    option_list = [
        PluginOpt(
            "dbuser", default="mysql", val_type=str,
            desc="Username for database dump collection"
        ),
        PluginOpt(
            "dbpass", default="", val_type=str,
            desc="Password for database dump collection",
        ),
        PluginOpt(
            "dumpdbs", default=False, val_type=bool,
            desc="Get name of all databases"
        ),
    ]

    def setup(self):
        # Set default paths for snap
        snap_path_common = "/var/snap/charmed-mysql/common"
        snap_path_current = "/var/snap/charmed-mysql/current"

        # Check if deployment is in a Kubernetes cluster
        k8s_deploy = any("KUBERNETES" in key for key in os.environ)

        # If in a Kubernetes cluster, set the snap paths to "None" as
        # MySQL configuration does not exist in snap paths
        if k8s_deploy:
            snap_path_common = ""
            snap_path_current = ""

        # Set the configuration paths
        conf_paths = {
            "MYSQL_CONF": f"{snap_path_current}/etc/mysql",
            "MYSQL_LOGS": f"{snap_path_common}/var/log/mysql",
            "MYSQL_ROUTER_CONF": f"{snap_path_current}/etc/mysqlrouter",
            "MYSQL_ROUTER_LOGS": f"{snap_path_common}/var/log/mysqlrouter",
            "MYSQL_SHELL_LOGS": f"{snap_path_common}/var/log/mysqlsh",
        }

        # Ignore private keys
        self.add_forbidden_path([
            f"{conf_paths['MYSQL_CONF']}/*.pem",
            f"{conf_paths['MYSQL_CONF']}/*.key",
        ])

        # Include the files we want to get
        self.add_copy_spec([
            conf_paths["MYSQL_CONF"],
            conf_paths["MYSQL_LOGS"],
            conf_paths["MYSQL_ROUTER_CONF"],
            conf_paths["MYSQL_ROUTER_LOGS"],
            conf_paths["MYSQL_SHELL_LOGS"],
        ])

        # Only applicable if not in a Kubernetes cluster
        # as `snap info` and `journalctl` are not available
        # in the Kubernetes container
        if not k8s_deploy:
            # Get snap logs
            self.add_journal("snap.charmed-mysql.*")

            # Get snap info
            self.add_cmd_output("snap info charmed-mysql")

        # If dumpdbs is set, then get all databases
        if self.get_option("dumpdbs"):

            db_user = self.get_option("dbuser")
            db_pass = self.get_option("dbpass")

            # Check password is not already an environment variable
            # and user did not supply a password
            if "MYSQL_PWD" in os.environ and not db_pass:
                self.soslog.info(
                    "MYSQL_PWD present: Using MYSQL_PWD environment variable, "
                    "user did not provide password."
                )
                db_pass = os.environ["MYSQL_PWD"]
            elif not db_pass:  # Environment variable not set and no password
                self.soslog.warning(
                    "dumpdbs_error: option is set, but username and password "
                    "are not provided"
                )
                return

            mysql_env = {"MYSQL_PWD": db_pass}
            opts = f"-h 127.0.0.1 -u{db_user}"
            sql_cmd = f"mysql {opts} -e"
            queries = [
                # Get databases user has access to
                "'show databases;'",

                # Get unit operations from MySQL to see, for example,
                # if a unit is stuck on joining the cluster
                "'select * from mysql.juju_units_operations;'",

                # Get the cluster group replication status
                ("'select * from performance_schema.replication_group_members "
                    "order by MEMBER_HOST;'"),

                # Get connection stats
                "'show global status like \"%conne%\";'",

                # Get errors per client and host
                # Useful for problens like an app disconnectting randomly
                "'select * from performance_schema.host_cache;'"
            ]

            self.add_cmd_output(
                [f"{sql_cmd} {query}" for query in queries],
                env=mysql_env
            )

# vim: set et ts=4 sw=4 :
