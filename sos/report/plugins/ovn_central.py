# Copyright (C) 2018 Mark Michelson <mmichels@redhat.com>
# Copyright (C) 2024 Alan Baghumian <alan.baghumian@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
import os
import re
from sos.report.plugins import (
    Plugin,
    RedHatPlugin,
    DebianPlugin,
    UbuntuPlugin,
)


class OVNCentral(Plugin):

    short_desc = 'OVN Northd'
    plugin_name = "ovn_central"
    profiles = ('network', 'virt')
    containers = ('ovn-dbs-bundle.*', 'ovn_cluster_north_db_server')
    container_name = ""
    ovn_nbdb_socket = ""
    ovn_sbdb_socket = ""
    ovn_socket = ""
    ovn_controller_sock_regex = ""
    ovn_northd_sock_regex = ""
    pfx = ""

    def _find_sock(self, path, regex_name):
        _sfile = self.path_join(path, regex_name)
        if self.container_name:
            res = self.exec_cmd(f"ls {path}", container=self.container_name)
            if res['status'] != 0 or '\n' not in res['output']:
                self._log_error(
                    "Could not retrieve ovn_controller socket path "
                    f"from container {self.container_name}"
                )
            else:
                pattern = re.compile(regex_name)
                for filename in res['output'].split('\n'):
                    if pattern.match(filename):
                        return self.path_join(path, filename)
        # File not found, return the regex full path
        return _sfile

    def get_tables_from_schema(self, filename, skip=[]):
        """ Get tables from schema """
        if self.container_name:
            cmd = f"cat {filename}"
            res = self.exec_cmd(cmd, timeout=None, foreground=True,
                                container=self.container_name)
            if res['status'] != 0:
                self._log_error("Could not retrieve DB schema file from "
                                f"container {self.container_name}")
                return None
            try:
                db_schema = json.loads(res['output'])
            except Exception:  # pylint: disable=broad-except
                self._log_error(f"Cannot parse JSON file {filename}")
                return None
        else:
            try:
                fname = self.path_join(filename)
                with open(fname, 'r', encoding='UTF-8') as file:
                    try:
                        db_schema = json.load(file)
                    except Exception:  # pylint: disable=broad-except
                        self._log_error(f"Cannot parse JSON file {filename}")
                        return None
            except IOError as ex:
                self._log_error(
                    f"Could not open DB schema file {filename}: {ex}")
                return None
        try:
            return [table for table in dict.keys(
                db_schema['tables']) if table not in skip]
        except AttributeError:
            self._log_error(f"DB schema {filename} has no 'tables' key")
        return None

    def add_database_output(self, tables, ovn_cmd):
        """ Collect OVN database output """
        if tables:
            return [f"{ovn_cmd} list {table}" for table in tables]
        return None

    def setup(self):
        # check if env is a clustered or non-clustered one
        if self.container_exists(self.containers[1]):
            self.container_name = self.get_container_by_name(
                self.containers[1])
        else:
            self.container_name = self.get_container_by_name(
                self.containers[0])

        ovs_rundir = os.environ.get('OVS_RUNDIR')
        for pidfile in ['ovnnb_db.pid', 'ovnsb_db.pid', 'ovn-northd.pid']:
            self.add_copy_spec([
                self.path_join('/var/lib/openvswitch/ovn', pidfile),
                self.path_join('/usr/local/var/run/openvswitch', pidfile),
                self.path_join('/run/openvswitch/', pidfile),
                self.path_join('/var/snap/microovn/common/run/ovn', pidfile),
            ])

            if ovs_rundir:
                self.add_copy_spec(self.path_join(ovs_rundir, pidfile))

        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/ovn/")
        else:
            self.add_copy_spec("/var/log/ovn/*.log")

        ovn_controller_socket = self._find_sock(
            self.ovn_socket, self.ovn_controller_sock_regex)

        northd_socket = self._find_sock(self.ovn_socket,
                                        self.ovn_northd_sock_regex)

        # ovsdb nb/sb cluster status commands
        cs = "cluster/status"
        cmds = []
        pfx = self.pfx

        appctl_cmds = [
            f"{pfx}ovs-appctl -t {self.ovn_nbdb_socket} {cs} OVN_Northbound",
            f"{pfx}ovs-appctl -t {self.ovn_sbdb_socket} {cs} OVN_Southbound",
            f"{pfx}ovn-appctl -t {northd_socket} status",
            f"{pfx}ovn-appctl -t {ovn_controller_socket} connection-status",
        ]

        self.add_cmd_output(appctl_cmds, foreground=True,
                            container=self.container_name, timeout=30)

        # MicroOVN currently does not support this
        if not pfx:
            dfl = "debug/chassis-features-list"
            self.add_cmd_output(f"{pfx}ovn-appctl -t {northd_socket} {dfl}",
                                foreground=True,
                                container=self.container_name, timeout=30)

        # Some user-friendly versions of DB output
        nolo = "--no-leader-only"
        nbctl_cmds = [
            f"{pfx}ovn-nbctl {nolo} show",
            f"{pfx}ovn-nbctl {nolo} get-ssl",
            f"{pfx}ovn-nbctl {nolo} get-connection",
        ]

        self.add_cmd_output(nbctl_cmds, foreground=True,
                            container=self.container_name, timeout=30)

        sbctl_cmds = [
            f"{pfx}ovn-sbctl {nolo} show",
            f"{pfx}ovn-sbctl {nolo} lflow-list",
            f"{pfx}ovn-sbctl {nolo} get-ssl",
            f"{pfx}ovn-sbctl {nolo} get-connection",
        ]

        self.add_cmd_output(sbctl_cmds, foreground=True,
                            container=self.container_name, timeout=30)

        # backward compatibility
        for path in ['/usr/share/openvswitch', '/usr/share/ovn',
                     '/snap/microovn/current/share/ovn']:
            if self.path_exists(self.path_join(path, 'ovn-nb.ovsschema')):
                nb_tables = self.get_tables_from_schema(self.path_join(
                    path, 'ovn-nb.ovsschema'))
                cmds.extend(self.add_database_output(nb_tables,
                                                     f"{pfx}ovn-nbctl {nolo}"))

        for path in ['/usr/share/openvswitch', '/usr/share/ovn',
                     '/snap/microovn/current/share/ovn']:
            if self.path_exists(self.path_join(path, 'ovn-sb.ovsschema')):
                sb_tables = self.get_tables_from_schema(self.path_join(
                    path, 'ovn-sb.ovsschema'), ['Logical_Flow'])
                cmds.extend(self.add_database_output(sb_tables,
                                                     f"{pfx}ovn-sbctl {nolo}"))

        # If OVN is containerized, we need to run the above commands inside
        # the container. Removing duplicates (in case there are) to avoid
        # failing on collecting output to file on container running commands
        cmds = list(set(cmds))
        self.add_cmd_output(
            cmds, foreground=True, container=self.container_name
        )

        self.add_copy_spec("/etc/sysconfig/ovn-northd")

        ovs_dbdir = os.environ.get('OVS_DBDIR')
        for dbfile in ["ovnnb_db.db", "ovnsb_db.db"]:
            for path in [
                "/var/lib/openvswitch/ovn",
                "/usr/local/etc/openvswitch",
                "/etc/openvswitch",
                "/var/lib/openvswitch",
                "/var/lib/ovn/etc",
                "/var/lib/ovn",
                "/var/snap/microovn/common/data/central/db",
            ]:
                dbfilepath = self.path_join(path, dbfile)
                if self.path_exists(dbfilepath):
                    self.add_copy_spec(dbfilepath)
                    self.add_dir_listing(dbfilepath)

            if ovs_dbdir:
                self.add_copy_spec(self.path_join(ovs_dbdir, dbfile))

        self.add_journal(units="ovn-northd")


class RedHatOVNCentral(OVNCentral, RedHatPlugin):

    packages = ('openvswitch-ovn-central', 'ovn.*-central', )
    ovn_nbdb_socket = '/var/run/openvswitch/ovnnb_db.ctl'
    ovn_sbdb_socket = '/var/run/openvswitch/ovnsb_db.ctl'
    ovn_socket = '/var/run/openvswitch'
    ovn_controller_sock_regex = 'ovn-controller.*.ctl'
    ovn_northd_sock_regex = 'ovn-northd.*.ctl'


class DebianOVNCentral(OVNCentral, DebianPlugin, UbuntuPlugin):

    packages = ('ovn-central', 'microovn', )

    def setup(self):
        if self.path_exists('/snap/bin/microovn'):
            self.ovn_socket = '/var/snap/microovn/common/run/ovn'
            self.ovn_nbdb_socket = f"{self.ovn_socket}/ovnnb_db.ctl"
            self.ovn_sbdb_socket = f"{self.ovn_socket}/ovnsb_db.ctl"
            self.pfx = 'microovn.'
        else:
            self.ovn_socket = '/var/run/ovn'
            self.ovn_nbdb_socket = '/var/run/ovn/ovnnb_db.ctl'
            self.ovn_sbdb_socket = '/var/run/ovn/ovnsb_db.ctl'
        super().setup()

    ovn_controller_sock_regex = 'ovn-controller.*.ctl'
    ovn_northd_sock_regex = 'ovn-northd.*.ctl'
