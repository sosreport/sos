# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.plugins import Plugin, UbuntuPlugin
from json import loads as json_loads


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
    files = ('/usr/bin/juju', '/usr/bin/juju-run')

    option_list = [
        ('export-mongodb',
         'Export mongodb collections as json files', '', False),
        ('generate-bundle',
         """Generate a YAML bundle of the current environment
         (requires juju-deployerizer)""", '', False),
    ]

    def get_deployed_services(self):
        cmd = "juju status --format json"
        status_json = self.call_ext_prog(cmd)['output']
        self.add_string_as_file(status_json, "juju_status_json")
        return json_loads(status_json)['services'].keys()

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
        self.add_copy_spec("/var/log/upstart/juju-db.log")
        self.add_copy_spec("/var/log/upstart/juju-db.log.1")
        if not self.get_option("all_logs"):
            # We need this because we want to collect to the limit of all
            # *.logs in the directory.
            if(os.path.isdir("/var/log/juju/")):
                for filename in os.listdir("/var/log/juju/"):
                    if filename.endswith(".log"):
                        fullname = os.path.join("/var/log/juju/" + filename)
                        self.add_copy_spec(fullname)
            self.add_cmd_output('ls -alRh /var/log/juju*')
            self.add_cmd_output('ls -alRh /var/lib/juju/*')

        else:
            self.add_copy_spec([
                "/var/log/juju",
                "/var/log/juju-*",
                "/var/lib/juju"
                # /var/lib/juju used to be in the default capture moving here
                # because it usually was way to big.  However, in most cases
                # you want all logs you want this too.
            ])

        self.add_cmd_output([
                "juju --version",
                "juju -v status --format=tabular",
        ])
        for service in self.get_deployed_services():
            self.add_cmd_output([
                "juju get {}".format(service),
                "juju get-config {}".format(service),
                "juju get-constraints {}".format(service)
            ])

        if self.get_option("export-mongodb"):
            self.export_mongodb()

        if self.get_option("generate-bundle"):
            self.add_cmd_output("juju deployerizer --include-charm-versions",
                                suggest_filename="juju-env-bundle.yaml")


# vim: set et ts=4 sw=4 :
