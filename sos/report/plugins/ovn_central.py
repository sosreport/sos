# Copyright (C) 2018 Mark Michelson <mmichels@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (
    Plugin,
    RedHatPlugin,
    DebianPlugin,
    UbuntuPlugin,
)
import json
import os
import re


class OVNCentral(Plugin):

    short_desc = 'OVN Northd'
    plugin_name = "ovn_central"
    profiles = ('network', 'virt')
    containers = ('ovn-dbs-bundle.*', 'ovn_cluster_north_db_server')

    def _find_sock(self, path, regex_name):
        _sfile = os.path.join(path, regex_name)
        if self._container_name:
            res = self.exec_cmd("ls %s" % path, container=self._container_name)
            if res['status'] != 0 or '\n' not in res['output']:
                self._log_error(
                    "Could not retrieve ovn_controller socket path "
                    "from container %s" % self._container_name
                )
            else:
                pattern = re.compile(regex_name)
                for filename in res['output'].split('\n'):
                    if pattern.match(filename):
                        return os.path.join(path, filename)
        # File not found, return the regex full path
        return _sfile

    def get_tables_from_schema(self, filename, skip=[]):
        if self._container_name:
            cmd = "cat %s" % filename
            res = self.exec_cmd(cmd, timeout=None, foreground=True,
                                container=self._container_name)
            if res['status'] != 0:
                self._log_error("Could not retrieve DB schema file from "
                                "container %s" % self._container_name)
                return None
            try:
                db = json.loads(res['output'])
            except Exception:
                self._log_error("Cannot parse JSON file %s" % filename)
                return None
        else:
            try:
                with open(self.path_join(filename), 'r') as f:
                    try:
                        db = json.load(f)
                    except Exception:
                        self._log_error(
                            "Cannot parse JSON file %s" % filename)
                        return None
            except IOError as ex:
                self._log_error(
                    "Could not open DB schema file %s: %s" % (filename, ex))
                return None
        try:
            return [table for table in dict.keys(
                db['tables']) if table not in skip]
        except AttributeError:
            self._log_error("DB schema %s has no 'tables' key" % filename)
        return None

    def add_database_output(self, tables, cmds, ovn_cmd):
        if not tables:
            return
        for table in tables:
            cmds.append('%s list %s' % (ovn_cmd, table))

    def setup(self):
        # check if env is a clustered or non-clustered one
        if self.container_exists(self.containers[1]):
            self._container_name = self.get_container_by_name(
                self.containers[1])
        else:
            self._container_name = self.get_container_by_name(
                self.containers[0])

        ovs_rundir = os.environ.get('OVS_RUNDIR')
        for pidfile in ['ovnnb_db.pid', 'ovnsb_db.pid', 'ovn-northd.pid']:
            self.add_copy_spec([
                self.path_join('/var/lib/openvswitch/ovn', pidfile),
                self.path_join('/usr/local/var/run/openvswitch', pidfile),
                self.path_join('/run/openvswitch/', pidfile),
            ])

            if ovs_rundir:
                self.add_copy_spec(self.path_join(ovs_rundir, pidfile))

        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/ovn/")
        else:
            self.add_copy_spec("/var/log/ovn/*.log")

        ovn_controller_sock_path = self._find_sock(
            self.ovn_sock_path, self.ovn_controller_sock_regex)

        northd_sock_path = self._find_sock(self.ovn_sock_path,
                                           self.ovn_northd_sock_regex)

        # ovsdb nb/sb cluster status commands
        self.add_cmd_output(
            [
                'ovs-appctl -t {} cluster/status OVN_Northbound'.format(
                    self.ovn_nbdb_sock_path),
                'ovs-appctl -t {} cluster/status OVN_Southbound'.format(
                    self.ovn_sbdb_sock_path),
                'ovn-appctl -t {} status'.format(northd_sock_path),
                'ovn-appctl -t {} debug/chassis-features-list'.format(
                    northd_sock_path),
                'ovn-appctl -t {} connection-status'.format(
                    ovn_controller_sock_path),
            ],
            foreground=True, container=self._container_name, timeout=30
        )

        # Some user-friendly versions of DB output
        nbctl_cmds = [
            'ovn-nbctl --no-leader-only show',
            'ovn-nbctl --no-leader-only get-ssl',
            'ovn-nbctl --no-leader-only get-connection',
        ]

        sbctl_cmds = [
            'ovn-sbctl --no-leader-only show',
            'ovn-sbctl --no-leader-only lflow-list',
            'ovn-sbctl --no-leader-only get-ssl',
            'ovn-sbctl --no-leader-only get-connection',
        ]

        # backward compatibility
        for path in ['/usr/share/openvswitch', '/usr/share/ovn']:
            nb_tables = self.get_tables_from_schema(self.path_join(
                path, 'ovn-nb.ovsschema'))
            self.add_database_output(nb_tables, nbctl_cmds,
                                     'ovn-nbctl --no-leader-only')

        cmds = nbctl_cmds

        for path in ['/usr/share/openvswitch', '/usr/share/ovn']:
            sb_tables = self.get_tables_from_schema(self.path_join(
                path, 'ovn-sb.ovsschema'), ['Logical_Flow'])
            self.add_database_output(sb_tables, sbctl_cmds,
                                     'ovn-sbctl --no-leader-only')
        cmds += sbctl_cmds

        # If OVN is containerized, we need to run the above commands inside
        # the container. Removing duplicates (in case there are) to avoid
        # failing on collecting output to file on container running commands
        cmds = list(set(cmds))
        self.add_cmd_output(
            cmds, foreground=True, container=self._container_name
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
            ]:
                dbfilepath = self.path_join(path, dbfile)
                if os.path.exists(dbfilepath):
                    self.add_copy_spec(dbfilepath)
                    self.add_cmd_output(
                        "ls -lan %s" % dbfilepath, foreground=True)
            if ovs_dbdir:
                self.add_copy_spec(self.path_join(ovs_dbdir, dbfile))

        self.add_journal(units="ovn-northd")


class RedHatOVNCentral(OVNCentral, RedHatPlugin):

    packages = ('openvswitch-ovn-central', 'ovn.*-central', )
    ovn_nbdb_sock_path = '/var/run/openvswitch/ovnnb_db.ctl'
    ovn_sbdb_sock_path = '/var/run/openvswitch/ovnsb_db.ctl'
    ovn_sock_path = '/var/run/openvswitch'
    ovn_controller_sock_regex = 'ovn-controller.*.ctl'
    ovn_northd_sock_regex = 'ovn-northd.*.ctl'


class DebianOVNCentral(OVNCentral, DebianPlugin, UbuntuPlugin):

    packages = ('ovn-central', )
    ovn_nbdb_sock_path = '/var/run/ovn/ovnnb_db.ctl'
    ovn_sbdb_sock_path = '/var/run/ovn/ovnsb_db.ctl'
    ovn_sock_path = '/var/run/ovn'
    ovn_controller_sock_regex = 'ovn-controller.*.ctl'
    ovn_northd_sock_regex = 'ovn-northd.*.ctl'
