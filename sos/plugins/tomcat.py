# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

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

        limit = self.get_option("log_size")

        if not self.get_option("all_logs"):
            log_glob = "/var/log/tomcat*/catalina.out"
            self.add_copy_spec(log_glob, sizelimit=limit)

            # get today's date in iso format so that days/months below 10
            # prepend 0
            today = datetime.date(datetime.now()).isoformat()
            log_glob = "/var/log/tomcat*/catalina.%s.log" % today
            self.add_copy_spec(log_glob, sizelimit=limit)
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
