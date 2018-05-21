# Copyright (C) 2018 Mark Michelson <mmichels@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import json
import os
import six


class OVNCentral(Plugin):
    """ OVN Northd
    """
    plugin_name = "ovn_central"
    profiles = ('network', 'virt')

    def add_database_output(self, filename, cmds, ovn_cmd, skip=[]):
        try:
            with open(filename, 'r') as f:
                try:
                    db = json.load(f)
                except:
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

    def setup(self):
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
            'ovn-sbctl lflow-list',
            'ovn-nbctl get-ssl',
            'ovn-nbctl get-connection',
            'ovn-sbctl get-ssl',
            'ovn-sbctl get-connection',
        ]

        schema_dir = '/usr/share/openvswitch'

        self.add_database_output(os.path.join(schema_dir, 'ovn-nb.ovsschema'),
                                 cmds, 'ovn-nbctl')
        self.add_database_output(os.path.join(schema_dir, 'ovn-sb.ovsschema'),
                                 cmds, 'ovn-sbctl', ['Logical_Flow'])

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
