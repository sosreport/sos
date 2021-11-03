# Copyright Red Hat 2020, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import fnmatch

from pipes import quote
from sos.collector.clusters import Cluster

ENGINE_KEY = '/etc/pki/ovirt-engine/keys/engine_id_rsa'


class ovirt(Cluster):
    """
    This cluster profile is for the oVirt/RHV project which provides for a
    virtualization cluster built ontop of KVM.

    Nodes enumerated will be hypervisors within the envrionment, not virtual
    machines running on those hypervisors. By default, ALL hypervisors within
    the environment are returned. This may be influenced by the 'cluster' and
    'datacenter' cluster options, which will limit enumeration to hypervisors
    within the specific cluster and/or datacenter. The spm-only cluster option
    may also be used to only collect from hypervisors currently holding the
    SPM role.

    Optionally, to only collect an archive from manager and the postgresql
    database, use the no-hypervisors cluster option.

    By default, a second archive from the manager will be collected that is
    just the postgresql plugin configured in such a way that a dump of the
    manager's database that can be explored and restored to other systems will
    be collected.

    The ovirt profile focuses on the upstream, community ovirt project.

    The rhv profile is for Red Hat customers running RHV (formerly RHEV).

    The rhhi_virt profile is for Red Hat customers running RHV in a
    hyper-converged setup and enables gluster collections.
    """

    cluster_name = 'Community oVirt'
    packages = ('ovirt-engine',)
    db_exec = '/usr/share/ovirt-engine/dbscripts/engine-psql.sh -c'

    option_list = [
        ('no-database', False, 'Do not collect a database dump'),
        ('cluster', '', 'Only collect from hosts in this cluster'),
        ('datacenter', '', 'Only collect from hosts in this datacenter'),
        ('no-hypervisors', False, 'Do not collect from hypervisors'),
        ('spm-only', False, 'Only collect from SPM host(s)')
    ]

    def _run_db_query(self, query):
        '''
        Wrapper for running DB queries on the manager. Any scrubbing of the
        query should be done _before_ passing the query to this method.
        '''
        cmd = "%s %s" % (self.db_exec, quote(query))
        return self.exec_primary_cmd(cmd, need_root=True)

    def _sql_scrub(self, val):
        '''
        Manually sanitize SQL queries since we can't leave this up to the
        driver since we do not have an actual DB connection
        '''
        if not val:
            return '%'

        invalid_chars = ['\x00', '\\', '\n', '\r', '\032', '"', '\'']
        if any(x in invalid_chars for x in val):
            self.log_warn("WARNING: Cluster option \'%s\' contains invalid "
                          "characters. Using '%%' instead." % val)
            return '%'

        return val

    def _check_for_engine_keys(self):
        '''
        Checks for the presence of the VDSM ssh keys the manager uses for
        communication with hypervisors.

        This only runs if we're locally on the RHV-M, *and* if no ssh-keys are
        called out on the command line, *and* no --password option is given.
        '''
        if self.primary.local:
            if not any([self.opts.ssh_key, self.opts.password,
                        self.opts.password_per_node]):
                if self.primary.file_exists(ENGINE_KEY):
                    self.add_default_ssh_key(ENGINE_KEY)
                    self.log_debug("Found engine SSH key. User command line"
                                   " does not specify a key or password, using"
                                   " engine key.")

    def setup(self):
        self.pg_pass = False
        if not self.get_option('no-database'):
            self.conf = self.parse_db_conf()
        self.format_db_cmd()
        self._check_for_engine_keys()

    def format_db_cmd(self):
        cluster = self._sql_scrub(self.get_option('cluster'))
        datacenter = self._sql_scrub(self.get_option('datacenter'))
        self.dbquery = ("SELECT host_name from vds where cluster_id in "
                        "(select cluster_id FROM cluster WHERE name like '%s'"
                        " and storage_pool_id in (SELECT id FROM storage_pool "
                        "WHERE name like '%s'))" % (cluster, datacenter))
        if self.get_option('spm-only'):
            # spm_status is an integer with the following meanings
            # 0 - Normal (not SPM)
            # 1 - Contending (SPM election in progress, but is not SPM)
            # 2 - SPM
            self.dbquery += ' AND spm_status = 2'
        self.log_debug('Query command for ovirt DB set to: %s' % self.dbquery)

    def get_nodes(self):
        if self.get_option('no-hypervisors'):
            return []
        res = self._run_db_query(self.dbquery)
        if res['status'] == 0:
            nodes = res['output'].splitlines()[2:-1]
            return [n.split('(')[0].strip() for n in nodes]
        else:
            raise Exception('database query failed, return code: %s'
                            % res['status'])

    def run_extra_cmd(self):
        if not self.get_option('no-database') and self.conf:
            return self.collect_database()
        return False

    def parse_db_conf(self):
        conf = {}
        engconf = '/etc/ovirt-engine/engine.conf.d/10-setup-database.conf'
        res = self.exec_primary_cmd('cat %s' % engconf, need_root=True)
        if res['status'] == 0:
            config = res['output'].splitlines()
            for line in config:
                try:
                    k = str(line.split('=')[0])
                    v = str(line.split('=')[1].replace('"', ''))
                    conf[k] = v
                except IndexError:
                    pass
            return conf
        return False

    def collect_database(self):
        sos_opt = (
                   '-k {plugin}.dbname={db} '
                   '-k {plugin}.dbhost={dbhost} '
                   '-k {plugin}.dbport={dbport} '
                   '-k {plugin}.username={dbuser} '
                   ).format(plugin='postgresql',
                            db=self.conf['ENGINE_DB_DATABASE'],
                            dbhost=self.conf['ENGINE_DB_HOST'],
                            dbport=self.conf['ENGINE_DB_PORT'],
                            dbuser=self.conf['ENGINE_DB_USER']
                            )
        cmd = ('PGPASSWORD={} /usr/sbin/sosreport --name=postgresql '
               '--batch -o postgresql {}'
               ).format(self.conf['ENGINE_DB_PASSWORD'], sos_opt)
        db_sos = self.exec_primary_cmd(cmd, need_root=True)
        for line in db_sos['output'].splitlines():
            if fnmatch.fnmatch(line, '*sosreport-*tar*'):
                _pg_dump = line.strip()
                self.primary.manifest.add_field('postgresql_dump',
                                                _pg_dump.split('/')[-1])
                return _pg_dump
        self.log_error('Failed to gather database dump')
        return False


class rhv(ovirt):

    cluster_name = 'Red Hat Virtualization'
    packages = ('rhevm', 'rhvm')
    sos_preset = 'rhv'

    def set_node_label(self, node):
        if node.address == self.primary.address:
            return 'manager'
        if node.is_installed('ovirt-node-ng-nodectl'):
            return 'rhvh'
        else:
            return 'rhelh'


class rhhi_virt(rhv):

    cluster_name = 'Red Hat Hyperconverged Infrastructure - Virtualization'
    sos_plugins = ('gluster',)
    sos_plugin_options = {'gluster.dump': 'on'}
    sos_preset = 'rhv'

    def check_enabled(self):
        return (self.primary.is_installed('rhvm') and self._check_for_rhhiv())

    def _check_for_rhhiv(self):
        ret = self._run_db_query('SELECT count(server_id) FROM gluster_server')
        if ret['status'] == 0:
            # if there are any entries in this table, RHHI-V is in use
            return ret['output'].splitlines()[2].strip() != '0'
        return False

# vim: set et ts=4 sw=4 :
