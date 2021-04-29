# Copyright (C) 2021 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re


from sos.report.plugins import Plugin, RedHatPlugin


class OpenStackDatabase(Plugin):

    short_desc = 'Openstack Database Information'
    plugin_name = 'openstack_database'
    profiles = ('openstack', 'openstack_controller')

    option_list = [
        ('dump', 'Dump select databases to a SQL file', 'slow', False),
        ('dumpall', 'Dump ALL databases to a SQL file', 'slow', False)
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

        in_container = False
        # determine if we're running databases on the host or in a container
        _db_containers = [
            'galera-bundle-.*',  # overcloud
            'mysql'  # undercloud
        ]

        for container in _db_containers:
            cname = self.get_container_by_name(container)
            if cname is not None:
                in_container = True
                break

        if in_container:
            fname = "clustercheck_%s" % cname
            cmd = self.fmt_container_cmd(cname, 'clustercheck')
            self.add_cmd_output(cmd, timeout=15, suggest_filename=fname)
        else:
            self.add_cmd_output('clustercheck', timeout=15)

        if self.get_option('dump') or self.get_option('dumpall'):
            db_dump = self.get_mysql_db_string(container=cname)
            db_cmd = "mysqldump --opt %s" % db_dump

            if in_container:
                db_cmd = self.fmt_container_cmd(cname, db_cmd)

            self.add_cmd_output(db_cmd, suggest_filename='mysql_dump.sql',
                                sizelimit=0)

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
