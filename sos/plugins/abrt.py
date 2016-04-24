# Copyright (C) 2010 Red Hat, Inc., Tomas Smetana <tsmetana@redhat.com>

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


class Abrt(Plugin, RedHatPlugin):
    """Automatic Bug Reporting Tool
    """

    plugin_name = "abrt"
    profiles = ('system', 'debug')
    packages = ('abrt-cli', 'abrt-gui', 'abrt')
    files = ('/var/spool/abrt',)

    option_list = [
        ("backtraces", 'collect backtraces for every report', 'slow', False)
    ]

    def do_backtraces(self):
        result = self.call_ext_prog('sqlite3 '
                                    '/var/spool/abrt/abrt-db \'select UUID '
                                    'from abrt_v4\'')
        try:
            for uuid in result['output'].split():
                self.add_cmd_output("abrt-cli -ib %s" % uuid,
                                    suggest_filename=("backtrace_%s" % uuid))
        except IndexError:
            pass

    def setup(self):
        self.add_cmd_output("abrt-cli -lf", suggest_filename="abrt-log")
        if self.get_option('backtraces'):
            self.do_backtraces()

# vim: set et ts=4 sw=4 :
