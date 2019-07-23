# Copyright (C) 2018 Mark Michelson <mmichels@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import json
import os
import six


class OVNCentral(Plugin):
    """ OVN Northd
    """
    plugin_name = "ovn_central"
    profiles = ('network', 'virt')
    _container_runtime = None
    _container_name = None

    def add_database_output(self, filename, cmds, ovn_cmd, skip=[]):
        try:
            with open(filename, 'r') as f:
                try:
                    db = json.load(f)
                except Exception:
                    # If json can't be parsed, then exit early
                    self._log_error("Cannot parse JSON file %s" % filename)
                    return
                try:
                    for table in six.iterkeys(db['tables']):
                        if table not in skip:
                            cmds.append('%s list %s' % (ovn_cmd, table))
                except AttributeError:
                    self._log_error("DB schema %s has no 'tables' key" %
                                    filename)
                    return
        except IOError as ex:
            self._log_error("Could not open DB schema file %s: %s" % (filename,
                                                                      ex))
            return

    def running_in_container(self):
        for runtime in ["docker", "podman"]:
            container_status = self.get_command_output(runtime + " ps")
            if container_status['status'] == 0:
                for line in container_status['output'].splitlines():
                    if "ovn-dbs-bundle" in line:
                        self._container_name = line.split()[-1]
                        self._container_runtime = runtime
                        return True
        return False

    def check_enabled(self):
        return (self.running_in_container() or
                super(OVNCentral, self).check_enabled())

    def setup(self):
        containerized = self.running_in_container()

        ovs_rundir = os.environ.get('OVS_RUNDIR')
        for pidfile in ['ovnnb_db.pid', 'ovnsb_db.pid', 'ovn-northd.pid']:
            self.add_copy_spec([
                os.path.join('/var/lib/openvswitch/ovn', pidfile),
                os.path.join('/usr/local/var/run/openvswitch', pidfile),
                os.path.join('/var/run/openvswitch/', pidfile),
                os.path.join('/run/openvswitch/', pidfile),
            ])

            if ovs_rundir:
                self.add_copy_spec(os.path.join(ovs_rundir, pidfile))

        # Some user-friendly versions of DB output
        cmds = [
            'ovn-nbctl show',
            'ovn-sbctl show',
            'ovn-sbctl lflow-list',
            'ovn-nbctl get-ssl',
            'ovn-nbctl get-connection',
            'ovn-sbctl get-ssl',
            'ovn-sbctl get-connection',
        ]


        schema_dir = '/usr/share/openvswitch'
        if containerized:
            cmd = "%s cp %s:/usr/share/openvswitch/ovn*.ovsschema /tmp/" % (
                self._container_runtime, self._container_name)
            if self.get_command_output(cmd)['status'] == 0:
                schema_dir = '/tmp'

        self.add_database_output(os.path.join(schema_dir, 'ovn-nb.ovsschema'),
                                 cmds, 'ovn-nbctl')
        self.add_database_output(os.path.join(schema_dir, 'ovn-sb.ovsschema'),
                                 cmds, 'ovn-sbctl', ['Logical_Flow'])

        # If OVN is containerized, we need to run the above commands inside
        # the container.
        if containerized:
            cmds = ['%s exec %s %s' % (self._container_runtime,
                                       self._container_name,
                                       cmd) for cmd in cmds]

        self.add_cmd_output(cmds)

        self.add_copy_spec("/etc/sysconfig/ovn-northd")

        ovs_dbdir = os.environ.get('OVS_DBDIR')
        for dbfile in ['ovnnb_db.db', 'ovnsb_db.db']:
            self.add_copy_spec([
                os.path.join('/var/lib/openvswitch/ovn', dbfile),
                os.path.join('/usr/local/etc/openvswitch', dbfile),
                os.path.join('/etc/openvswitch', dbfile),
                os.path.join('/var/lib/openvswitch', dbfile),
            ])
            if ovs_dbdir:
                self.add_copy_spec(os.path.join(ovs_dbdir, dbfile))

        self.add_journal(units="ovn-northd")


class RedHatOVNCentral(OVNCentral, RedHatPlugin):

    packages = ('openvswitch-ovn-central', )


class DebianOVNCentral(OVNCentral, DebianPlugin, UbuntuPlugin):

    packages = ('ovn-central', )
