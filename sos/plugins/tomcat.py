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


class Tomcat(Plugin, RedHatPlugin):
    """Apache Tomcat server
    """

    plugin_name = 'tomcat'
    profiles = ('webserver', 'java', 'services', 'sysmgmt')

    packages = ('tomcat6', 'tomcat')

    def setup(self):
        self.add_copy_spec([
            "/etc/tomcat",
            "/etc/tomcat6"
        ])

        limit = self.get_option("log_size")
        log_glob = "/var/log/tomcat*/catalina.out"
        self.add_copy_spec_limit(log_glob, sizelimit=limit)

    def postproc(self):
        self.do_path_regex_sub(
            r"\/etc\/tomcat.*\/tomcat-users.xml",
            r"password=(\S*)",
            r'password="********"'
        )

# vim: set et ts=4 sw=4 :
