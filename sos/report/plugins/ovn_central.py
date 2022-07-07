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
    SoSPredicate,
)
import json
import os


class OVNCentral(Plugin):

    short_desc = 'OVN Northd'
    plugin_name = "ovn_central"
    profiles = ('network', 'virt')
    containers = ('ovn-dbs-bundle.*',)

    def get_tables_from_schema(self, filename, skip=[]):
        if self._container_name:
            cmd = "cat %s" % filename
            res = self.exec_cmd(cmd, timeout=None, foreground=True,
                                container=self._container_name)
            if res['status'] != 0:
                self._log_error("Could not retrieve DB schema file from "
                                "container %s" % self._container_name)
                return
            try:
                db = json.loads(res['output'])
            except Exception:
                self._log_error("Cannot parse JSON file %s" % filename)
                return
        else:
            try:
                with open(self.path_join(filename), 'r') as f:
                    try:
                        db = json.load(f)
                    except Exception:
                        self._log_error(
                            "Cannot parse JSON file %s" % filename)
                        return
            except IOError as ex:
                self._log_error(
                    "Could not open DB schema file %s: %s" % (filename, ex))
                return
        try:
            return [table for table in dict.keys(
                db['tables']) if table not in skip]
        except AttributeError:
            self._log_error("DB schema %s has no 'tables' key" % filename)

    def add_database_output(self, tables, cmds, ovn_cmd):
        if not tables:
            return
        for table in tables:
            cmds.append('%s list %s' % (ovn_cmd, table))

    def setup(self):
        self._container_name = self.get_container_by_name(self.containers[0])

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

        # ovsdb nb/sb cluster status commands
        self.add_cmd_output(
            [
                'ovs-appctl -t {} cluster/status OVN_Northbound'.format(
                    self.ovn_nbdb_sock_path),
                'ovs-appctl -t {} cluster/status OVN_Southbound'.format(
                    self.ovn_sbdb_sock_path),
                'ovn-appctl -t ovn-northd status'
            ],
            foreground=True, container=self._container_name, timeout=30
        )

        # Some user-friendly versions of DB output
        nbctl_cmds = [
            'ovn-nbctl show',
            'ovn-nbctl get-ssl',
            'ovn-nbctl get-connection',
            'ovn-nbctl list loadbalancer',
            'ovn-nbctl list Load_Balancer',
            'ovn-nbctl list ACL',
            'ovn-nbctl list Logical_Switch_Port',
        ]

        sbctl_cmds = [
            'ovn-sbctl show',
            'ovn-sbctl lflow-list',
            'ovn-sbctl get-ssl',
            'ovn-sbctl get-connection',
        ]

        # backward compatibility
        for path in ['/usr/share/openvswitch', '/usr/share/ovn']:
            nb_tables = self.get_tables_from_schema(self.path_join(
                path, 'ovn-nb.ovsschema'))
            self.add_database_output(nb_tables, nbctl_cmds, 'ovn-nbctl')

        cmds = nbctl_cmds

        # Can only run sbdb commands if we are the leader
        co = {'cmd': "ovs-appctl -t {} cluster/status OVN_Southbound".
              format(self.ovn_sbdb_sock_path),
              "output": "Leader: self"}
        if self.test_predicate(self, pred=SoSPredicate(self, cmd_outputs=co)):
            # backward compatibility
            for path in ['/usr/share/openvswitch', '/usr/share/ovn']:
                sb_tables = self.get_tables_from_schema(self.path_join(
                    path, 'ovn-sb.ovsschema'), ['Logical_Flow'])
                self.add_database_output(sb_tables, sbctl_cmds, 'ovn-sbctl')
            cmds += sbctl_cmds

        # If OVN is containerized, we need to run the above commands inside
        # the container.

        self.add_cmd_output(
            cmds, foreground=True, container=self._container_name
        )

        self.add_copy_spec("/etc/sysconfig/ovn-northd")

        ovs_dbdir = os.environ.get('OVS_DBDIR')
        for dbfile in ['ovnnb_db.db', 'ovnsb_db.db']:
            self.add_copy_spec([
                self.path_join('/var/lib/openvswitch/ovn', dbfile),
                self.path_join('/usr/local/etc/openvswitch', dbfile),
                self.path_join('/etc/openvswitch', dbfile),
                self.path_join('/var/lib/openvswitch', dbfile),
                self.path_join('/var/lib/ovn/etc', dbfile)
            ])
            if ovs_dbdir:
                self.add_copy_spec(self.path_join(ovs_dbdir, dbfile))

        self.add_journal(units="ovn-northd")


class RedHatOVNCentral(OVNCentral, RedHatPlugin):

    packages = ('openvswitch-ovn-central', 'ovn.*-central', )
    ovn_nbdb_sock_path = '/var/run/openvswitch/ovnnb_db.ctl'
    ovn_sbdb_sock_path = '/var/run/openvswitch/ovnsb_db.ctl'


class DebianOVNCentral(OVNCentral, DebianPlugin, UbuntuPlugin):

    packages = ('ovn-central', )
    ovn_nbdb_sock_path = '/var/run/ovn/ovnnb_db.ctl'
    ovn_sbdb_sock_path = '/var/run/ovn/ovnsb_db.ctl'
