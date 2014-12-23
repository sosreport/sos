# Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class ActiveMq(Plugin, DebianPlugin):
    """ActiveMQ message broker
    """

    plugin_name = 'activemq'
    profiles = ('openshift',)
    packages = ('activemq', 'activemq-core')
    files = ('/var/log/activemq',)

    def setup(self):
        if self.get_option("all_logs"):
            self.add_copy_spec(list(self.files))
        else:
            self.add_copy_spec([
                "/var/log/activemq/activemq.log",
                "/var/log/activemq/wrapper.log"
            ])

    def postproc(self):
        # activemq.xml contains credentials in this form:
        #   <authenticationUser ... password="changeme" ... />
        self.do_file_sub(
            '/etc/activemq/activemq.xml',
            r'(\s*password=")[^"]*(".*)',
            r"\1******\2"
        )


class RedHatActiveMq(ActiveMq, RedHatPlugin):

    def setup(self):
        super(RedHatActiveMq, self).setup()
        self.add_copy_spec([
            '/etc/sysconfig/activemq',
            '/etc/activemq/activemq.xml'
        ])


class UbuntuActiveMq(ActiveMq, UbuntuPlugin):
    def setup(self):
        super(UbuntuActiveMq, self).setup()
        self.add_copy_spec([
            '/etc/activemq',
            '/etc/default/activemq'
        ])
