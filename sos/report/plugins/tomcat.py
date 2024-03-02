# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from datetime import datetime
from sos.report.plugins import Plugin, RedHatPlugin


class Tomcat(Plugin, RedHatPlugin):

    short_desc = 'Apache Tomcat Server'
    plugin_name = 'tomcat'
    profiles = ('webserver', 'java', 'services', 'sysmgmt')

    packages = ('tomcat', 'tomcat6', 'tomcat7', 'tomcat8')

    def setup(self):
        self.add_copy_spec([
            "/etc/tomcat",
            "/etc/tomcat6",
            "/etc/tomcat7",
            "/etc/tomcat8"
        ])

        if not self.get_option("all_logs"):
            log_glob = "/var/log/tomcat*/catalina.out"
            self.add_copy_spec(log_glob)

            # get today's date in iso format so that days/months below 10
            # prepend 0
            today = datetime.date(datetime.now()).isoformat()
            log_glob = "/var/log/tomcat*/catalina.%s.log" % today
            self.add_copy_spec(log_glob)
        else:
            self.add_copy_spec("/var/log/tomcat*/*")

        self.add_file_tags({
            "/etc/tomcat.*/web.xml": "tomcat_web_xml",
            "/var/log/tomcat.*/catalina.out": "catalina_out",
            "/var/log/tomcat.*/catalina.*.log": "catalina_server_log"
        })

    def postproc(self):
        server_password_attr = ['keyPass', 'keystorePass',
                                'truststorePass', 'SSLPassword']
        self.do_path_regex_sub(
            r"\/etc\/tomcat.*\/server.xml",
            r"(%s)=(\S*)" % "|".join(server_password_attr),
            r'\1="********"'
        )
        self.do_path_regex_sub(
            r"\/etc\/tomcat.*\/tomcat-users.xml",
            r"(password)=(\S*)",
            r'\1="********"'
        )

# vim: set et ts=4 sw=4 :
