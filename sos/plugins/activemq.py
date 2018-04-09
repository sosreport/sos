# Copyright (C) 2014 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
