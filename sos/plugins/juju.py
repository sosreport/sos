# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, UbuntuPlugin
from json import loads as json_load


def ensure_service_is_running(service):
    def wrapper(callback):
        def wrapped_f(self, *args, **kwargs):
            try:
                result = self.call_ext_prog("service {0} stop".format(service))
                if result["status"] != 0:
                    raise Exception("Cannot stop {0} service".format(service))
                callback(self, *args, **kwargs)
            except Exception as ex:
                self._log_error("Cannot stop {0}, exception: {1}".format(
                    service,
                    ex.message))
            finally:
                self.call_ext_prog("service {0} start".format(service))
        return wrapped_f
    return wrapper


class Juju(Plugin, UbuntuPlugin):
    """ Juju orchestration tool
    """

    plugin_name = 'juju'
    profiles = ('virt', 'sysmgmt')
    packages = ('juju',)

    option_list = [
        ('export-mongodb',
         'Export mongodb collections as json files', '', False),
        ('generate-bundle',
         """Generate a YAML bundle of the current environment
         (requires juju-deployerizer)""", '', False),
    ]

    def get_deployed_services(self):
        cmd = "juju status --format json"
        return json_load(
            self.call_ext_prog(cmd)['output'])['services'].keys()

    @ensure_service_is_running("juju-db")
    def export_mongodb(self):
        collections = (
            "relations",
            "environments",
            "linkednetworks",
            "system",
            "settings",
        )

        for collection in collections:
            self.add_cmd_output(
                "/usr/lib/juju/bin/mongoexport --ssl \
                --dbpath=/var/lib/juju/db --db juju --collection {0} \
                --jsonArray".format(collection),
                suggest_filename="{}.json".format(collection))

    def setup(self):
        self.add_copy_spec([
            "/var/lib/juju"
        ])
        limit = self.get_option("log_size")
        self.add_copy_spec_limit("/var/log/upstart/juju-db.log",
                                 sizelimit=limit)
        self.add_copy_spec_limit("/var/log/upstart/juju-db.log.1",
                                 sizelimit=limit)
        if not self.get_option("all_logs"):
            # Capture the last bit of all files
            for filename in os.listdir("/var/log/juju/"):
                if filename.endswith(".log"):
                    fullname = "/var/log/juju/" + filename
                    self.add_copy_spec_limit(fullname, sizelimit=limit)
            # Do just the all-machines from juju local
            self.add_copy_spec_limit("/var/log/juju-*/all-machines.log",
                                     sizelimit=limit)
            self.add_cmd_output('ls -alRh /var/log/juju*')
        else:
            self.add_copy_spec([
                "/var/log/juju",
                "/var/log/juju-*"
            ])

        self.add_cmd_output([
            "juju -v status",
            "juju -v get-constraints"
        ])

        for service in self.get_deployed_services():
            self.add_cmd_output("juju get {}".format(service))

        if self.get_option("export-mongodb"):
            self.export_mongodb()

        if self.get_option("generate-bundle"):
            self.add_cmd_output("juju deployerizer --include-charm-versions",
                                suggest_filename="juju-env-bundle.yaml")


# vim: set et ts=4 sw=4 :
