# -*- python -*-
# -*- coding: utf-8 -*-

# Copyright (C) 2015 Red Hat, Inc., Pep Turró Mauri <pep@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

import os.path


class ManageIQ(Plugin, RedHatPlugin):
    """ManageIQ/CloudForms related information
    """

    plugin_name = 'manageiq'

    miq_dir = '/var/www/miq/vmdb'

    packages = ('cfme',)
    files = (
        os.path.join(miq_dir, 'BUILD'),
        os.path.join(miq_dir, 'GUID'),
        os.path.join(miq_dir, 'VERSION')
    )

    # Config files to collect from miq_dir/config/
    miq_conf_dir = os.path.join(miq_dir, "config")
    miq_conf_files = [
        'application.rb',
        'boot.rb',
        'environment.rb',
        'preinitializer.rb',
        'routes.rb',
        'environments/metric_fu.rb',
        'environments/production.rb',
        'api.yml',
        'broker_notify_properties.tmpl.yml',
        'capacity.tmpl.yml',
        'dashboard.yml',
        'event_handling.tmpl.yml',
        'hostdefaults.tmpl.yml',
        'mongrel_cluster.yml',
        'mongrel_win.yml',
        'storage.tmpl.yml',
        'vmdb.tmpl.yml',
        'vmdb.yml.db',
        'event_handling.yml.db',
        'lighttpd.conf',
        'replication.conf'
    ]

    # Log files to collect from miq_dir/log/
    miq_log_dir = os.path.join(miq_dir, "log")
    miq_log_files = [
        'appliance_console.log',
        'api.log',
        'audit.log',
        'automation.log',
        'aws.log',
        'evm.log',
        'fog.log',
        'miq_ntpdate.log',
        'mongrel.log',
        'policy.log',
        'prince.log',
        'production.log',
        'rhevm.log',
        'scvmm.log',
        'top_output.log',
        'vim.log',
        'vmdb_restart.log',
        'vmstat_output.log',
        'vmstat_output.log',
        'apache/miq_apache.log',
        'apache/ssl_access.log',
        'apache/ssl_error.log',
        'apache/ssl_request.log',
        'apache/ssl_mirror_request.log',
        'apache/ssl_mirror_error.log',
        'apache/ssl_mirror_access_error.log',
        'gem_list.txt',
        'last_startup.txt',
        'package_list_rpm.txt',
        'vendor_gems.txt'
    ]

    def setup(self):
        if self.get_option("all_logs"):
            # turn all log files to a glob to include logrotated ones
            self.miq_log_files = map(lambda x: x + '*', self.miq_log_files)

        self.add_copy_spec(list(self.files))

        self.add_copy_spec([
            os.path.join(self.miq_conf_dir, x) for x in self.miq_conf_files
        ])

        self.add_copy_spec([
            os.path.join(self.miq_log_dir, x) for x in self.miq_log_files
        ])

# vim: set et ts=4 sw=4 :
