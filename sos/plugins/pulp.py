# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin
from pipes import quote


class Pulp(Plugin, RedHatPlugin):
    """Pulp platform"""

    plugin_name = "pulp"
    packages = ("pulp-server", "pulp-katello")
    option_list = [
        ('tasks', 'number of tasks to collect from DB queries', 'fast', 200)
    ]

    def setup(self):
        self.add_copy_spec([
            "/etc/pulp/*.conf",
            "/etc/pulp/server/plugins.conf.d/",
            "/etc/default/pulp*",
            "/var/log/httpd/pulp-http.log*",
            "/var/log/httpd/pulp-https.log*",
            "/var/log/httpd/pulp-http_access_ssl.log*",
            "/var/log/httpd/pulp-https_access_ssl.log*",
            "/var/log/httpd/pulp-http_error_ssl.log*",
            "/var/log/httpd/pulp-https_error_ssl.log*"
        ])

        num_tasks = self.get_option('tasks')

        mtasks = self.build_mongo_cmd(
            '\"DBQuery.shellBatchSize=%s;; '
            'db.task_status.find().sort({finish_time: -1})'
            '.pretty().shellPrint()\"' % num_tasks
        )

        mres = self.build_mongo_cmd(
            '\"DBQuery.shellBatchSize=%s;; '
            'db.reserved_resources.find().pretty().shellPrint()\"' % num_tasks
        )

        prun = self.build_mongo_cmd(
            r'"DBQuery.shellBatchSize=%s;; '
            r'db.task_status.find({state:{\$ne: \"finished\"}}).pretty()'
            r'.shellPrint()"' % num_tasks
        )

        self.add_cmd_output(mtasks, suggest_filename="mongo-task_status")
        self.add_cmd_output(mres, suggest_filename="mongo-reserved_resources")
        self.add_cmd_output(prun, suggest_filename="pulp-running_tasks")

    def build_mongo_cmd(self, query):
        _cmd = "bash -c %s"
        _moncmd = "mongo pulp_database --eval %s"
        return _cmd % quote(_moncmd % query)

    def postproc(self):
        etcreg = r"(([a-z].*(passw|token|cred|secret).*)\:(\s))(.*)"
        repl = r"\1 ********"
        self.do_path_regex_sub("/etc/pulp/(.*).conf", etcreg, repl)
        jreg = r"(\s*\".*(passw|cred|token|secret).*\:)(.*)"
        self.do_path_regex_sub("/etc/pulp(.*)(.json$)", jreg, repl)

# vim: set et ts=4 sw=4 :
