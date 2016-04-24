# Copyright (C) 2007 Red Hat, Inc., Eugene Teo <eteo@redhat.com>

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


class Sendmail(Plugin):
    """sendmail service
    """

    plugin_name = "sendmail"
    profiles = ('services', 'mail')

    packages = ('sendmail',)


class RedHatSendmail(Sendmail, RedHatPlugin):

    files = ('/etc/rc.d/init.d/sendmail',)
    packages = ('sendmail',)

    def setup(self):
        super(RedHatSendmail, self).setup()
        self.add_copy_spec([
            "/etc/mail/*",
            "/var/log/maillog"
        ])


class DebianSendmail(Sendmail, DebianPlugin, UbuntuPlugin):

    files = ('/etc/init.d/sendmail',)
    packages = ('sendmail',)

    def setup(self):
        super(DebianSendmail, self).setup()
        self.add_copy_spec([
            "/etc/mail/*",
            "/var/log/mail.*"
        ])

# vim: set et ts=4 sw=4 :
