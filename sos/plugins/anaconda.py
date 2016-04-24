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
import os


class Anaconda(Plugin, RedHatPlugin):
    """Anaconda installer
    """

    plugin_name = 'anaconda'
    profiles = ('system',)

    files = (
        '/var/log/anaconda.log',
        '/var/log/anaconda'
    )

    def setup(self):

        paths = [
            "/root/anaconda-ks.cfg"
        ]

        if os.path.isdir('/var/log/anaconda'):
            # new anaconda
            paths.append('/var/log/anaconda')
        else:
            paths = paths + [
                "/var/log/anaconda.*"
                "/root/install.log",
                "/root/install.log.syslog"
            ]

        self.add_copy_spec(paths)

    def postproc(self):
        self.do_file_sub(
            "/root/anaconda-ks.cfg",
            r"(\s*rootpw\s*).*",
            r"\1********"
        )
        self.do_file_sub(
            "/root/anaconda-ks.cfg",
            r"(user.*--password=*\s*)\s*(\S*)",
            r"\1********"
        )

# vim: set et ts=4 sw=4 :
