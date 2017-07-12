### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

from sos.plugins import Plugin, RedHatPlugin

class Lustre(Plugin, RedHatPlugin):
    '''Lustre filesystem'''

    plugin_name = 'lustre'
    profiles = ('storage','network','cluster',)
    packages = ('lustre', 'lustre-client',)

    def setup(self):
        self.add_cmd_output("lctl debug_kernel")
        self.add_cmd_output("lctl device_list")

        self.get_params("basic", [ "version", "health_check", "debug" ])
        self.get_params("lnet", [ "peers", "routes", "routers", "nis" ])
        self.get_params("ldlm-states", [ "*.*.state" ])
        self.get_params("jobid", [ "jobid_name", "jobid_var" ])

        if (self.is_installed('lustre-client')):
            self.add_cmd_output("lfs df")
            self.add_cmd_output("lfs df -i")

        else:
            self.get_params("osd", [ "osd-*.*.{mntdev,files*,kbytes*,blocksize,brw_stats}" ])
            self.get_params("quota", [ "osd-*.*.quota_slave.{info,limit_*,acct_*}" ])

    def get_params(self, name, param_list):
        ''' Use lctl get_param to collect a selection of parameters into a file.
        '''
        self.add_cmd_output("lctl get_param "+" ".join(param_list),
                            suggest_filename="params-"+name,
                            stderr=False)

# vim: set et ts=4 sw=4 :
