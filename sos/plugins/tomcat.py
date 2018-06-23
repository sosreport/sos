# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin
from datetime import datetime


class Tomcat(Plugin, RedHatPlugin):
    """Apache Tomcat server
    """

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

    def postproc(self):
        serverXmlPasswordAttributes = ['keyPass', 'keystorePass',
                                       'truststorePass', 'SSLPassword']
        for attr in serverXmlPasswordAttributes:
            self.do_path_regex_sub(
                r"\/etc\/tomcat.*\/server.xml",
                r"%s=(\S*)" % attr,
                r'%s="********"' % attr
            )
        self.do_path_regex_sub(
            r"\/etc\/tomcat.*\/tomcat-users.xml",
            r"password=(\S*)",
            r'password="********"'
        )

# vim: set et ts=4 sw=4 :
