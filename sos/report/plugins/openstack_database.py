# Copyright (C) 2021 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re


from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt


class OpenStackDatabase(Plugin):

    short_desc = 'Openstack Database Information'
    plugin_name = 'openstack_database'
    profiles = ('openstack', 'openstack_controller')

    option_list = [
        PluginOpt('dump', default=False, desc='Dump select databases'),
        PluginOpt('dumpall', default=False, desc='Dump ALL databases')
    ]

    databases = [
        'cinder',
        'glance',
        'heat',
        'ironic',
        'keystone',
        'mistral',
        '(.*)?neutron',
        'nova.*'
    ]

    def setup(self):
        # determine if we're running databases on the host or in a container
        _db_containers = [
            'galera-bundle-.*',  # overcloud
            'mysql'  # undercloud
        ]

        cname = None
        for container in _db_containers:
            cname = self.get_container_by_name(container)
            if cname:
                break

        fname = "clustercheck_%s" % cname if cname else None
        self.add_cmd_output('clustercheck', container=cname, timeout=15,
                            suggest_filename=fname)

        if self.get_option('dump') or self.get_option('dumpall'):
            db_dump = self.get_mysql_db_string(container=cname)
            db_cmd = "mysqldump --opt %s" % db_dump

            self.add_cmd_output(db_cmd, suggest_filename='mysql_dump.sql',
                                sizelimit=0, container=cname)

    def get_mysql_db_string(self, container=None):

        if self.get_option('dumpall'):
            return '--all-databases'

        collect = []
        dbs = self.exec_cmd('mysql -e "show databases;"', container=container)

        for db in dbs['output'].splitlines():
            if any([re.match(db, reg) for reg in self.databases]):
                collect.append(db)

        return '-B ' + ' '.join(d for d in collect)


class RedHatOpenStackDatabase(OpenStackDatabase, RedHatPlugin):

    packages = ('openstack-selinux', )


# vim: set et ts=4 sw=4 :
