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


def journalctl_commands(opts, all_logs=False, since_when='--since="-3days"'):
    """ Adds journalctl commands in two formats.

        @param list opts: special options to be added to all commands
        @param bool all_logs: True if all logs are required
        @param str since_when: option string indicating start time
        @returns: a list of journalctl commands as a list

        Default all_logs value is False. If True, since_when value is ignored.
        Default since_when value is '--since="-3days"'. The empty string means
        since the beginning of logging. All strings must conform to
        journalctl command line syntax.
    """
    since_when = "" if all_logs else since_when
    std_opts = ["--all", "--no-pager"]
    opts = std_opts + opts + [since_when]

    format_opts = ["", "--output=json"]
    return [["journalctl"] + [x for x in opts + [a] if x] for a in format_opts]

# vim: set et ts=4 sw=4 :
