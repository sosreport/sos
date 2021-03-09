# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Opensvc(Plugin, IndependentPlugin):

    short_desc = 'OpenSVC cluster and services (config and state collection)'
    plugin_name = 'opensvc'
    profiles = ('cluster', 'services', 'system')
    packages = ('opensvc',)

    def get_status(self, kind):
        getobjs = self.collect_cmd_output("om %s ls --color=no" % kind)
        dirname = kind + '_status'
        if getobjs['status'] == 0:
            for line in getobjs['output'].splitlines():
                self.add_cmd_output(
                    "om %s print status --color=no" % line,
                    subdir=dirname
                )

    def setup(self):
        self.add_copy_spec([
            "/etc/opensvc/*",
            "/var/log/opensvc/*",
            "/etc/conf.d/opensvc",
            "/etc/default/opensvc",
            "/etc/sysconfig/opensvc",
            "/var/lib/opensvc/*.json",
            "/var/lib/opensvc/list.*",
            "/var/lib/opensvc/ccfg",
            "/var/lib/opensvc/cfg",
            "/var/lib/opensvc/certs/ca_certificates",
            "/var/lib/opensvc/certs/certificate_chain",
            "/var/lib/opensvc/compliance/*",
            "/var/lib/opensvc/namespaces/*",
            "/var/lib/opensvc/node/*",
            "/var/lib/opensvc/sec/*",
            "/var/lib/opensvc/svc/*",
            "/var/lib/opensvc/usr/*",
            "/var/lib/opensvc/vol/*",
        ])
        self.add_cmd_output([
            "ls -laRt /var/lib/opensvc",
            "om pool status --verbose --color=no",
            "om net status --verbose --color=no",
            "om mon --color=no",
            "om daemon dns dump --color=no",
            "om daemon status --format flat_json --color=no"
        ])
        self.get_status('vol')
        self.get_status('svc')

    def postproc(self):
        # Example:
        #
        # [hb#2]
        # secret = mypassword
        # type = relay
        # timeout = 30
        #
        # to
        #
        # [hb#2]
        # secret = ****************************
        # type = relay
        # timeout = 30

        regexp = r"(\s*secret =\s*)\S+"
        self.do_file_sub(
            "/etc/opensvc/cluster.conf",
            regexp,
            r"\1****************************"
        )

# vim: set et ts=4 sw=4 :
