# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.#

import os

from sos.report.plugins import Plugin, PluginOpt, UbuntuPlugin

SNAP_PATH_COMMON = "/var/snap/charmed-mysql/common"
SNAP_PATH_CURRENT = "/var/snap/charmed-mysql/current"

PATHS = {
    "MYSQL_CONF": f"{SNAP_PATH_CURRENT}/etc/mysql",
    "MYSQL_LOGS": f"{SNAP_PATH_COMMON}/var/log/mysql",
    "MYSQL_ROUTER_CONF": f"{SNAP_PATH_CURRENT}/etc/mysqlrouter",
    "MYSQL_ROUTER_LOGS": f"{SNAP_PATH_COMMON}/var/log/mysqlrouter",
    "MYSQL_SHELL_LOGS": f"{SNAP_PATH_COMMON}/var/log/mysqlsh",
}


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

        # Ignore private keys
        self.add_forbidden_path([
            f"{PATHS['MYSQL_CONF']}/*.pem",
            f"{PATHS['MYSQL_CONF']}/*.key",
        ])

        # Include the files we want to get
        self.add_copy_spec([
            PATHS["MYSQL_CONF"],
            PATHS["MYSQL_LOGS"],
            PATHS["MYSQL_ROUTER_CONF"],
            PATHS["MYSQL_ROUTER_LOGS"],
            PATHS["MYSQL_SHELL_LOGS"],
        ])

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

            # Record all available databases
            self.add_cmd_output(
                f"mysql {opts} -e 'show databases;'",
                env=mysql_env
            )

# vim: set et ts=4 sw=4 :
