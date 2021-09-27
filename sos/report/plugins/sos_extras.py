# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin
import os
import stat


class SosExtras(Plugin, IndependentPlugin):

    short_desc = 'Collect extra data defined in /etc/sos/extras.d'

    """The plugin traverses 'extras_dir' directory and for each file there,
    it executes commands or collects files optionally with sizelimit. Expected
    content of a file:
    - empty lines or those starting with '#' are ignored
    - add_copy_spec called to lines starting by ':', optionally followed by
      sizelimit
    - otherwise, whole line will be executed as a command.
    Example:
    command1 --arg1 val1
    command2
    :/path/to/file
    :/path/to/files* sizelimit

    WARNING: be careful what files to collect or what commands to execute:
    - prevent calling potentially dangerous or system altering commands, like:
      - using multiple commands on a line (via pipes, semicolon etc.)
      - executing commands on background
      - setting env.variables (as those will be ignored)
      - altering a system (not only by "rm -rf")
    - be aware, no secret obfuscation is made
    """

    plugin_name = "sos_extras"

    extras_dir = '/etc/sos/extras.d/'

    files = (extras_dir,)

    def setup(self):
        try:
            st = os.stat(self.extras_dir)
            if (st.st_uid != 0) or (st.st_mode & stat.S_IWGRP) or \
               (st.st_mode & stat.S_IWOTH):
                self._log_warn("Skipping sos extras as %s has too wide"
                               " permissions or ownership." % self.extras_dir)
                return
        except OSError:
            self._log_warn("can't stat %s, skipping sos extras" %
                           self.extras_dir)
            return

        for path, dirlist, filelist in os.walk(self.extras_dir):
            for f in filelist:
                _file = self.path_join(path, f)
                self._log_warn("Collecting data from extras file %s" % _file)
                try:
                    for line in open(_file).read().splitlines():
                        # ignore empty lines or comments
                        if len(line.split()) == 0 or line.startswith('#'):
                            continue
                        # lines starting by ':' specify file pattern to collect
                        # optionally followed by sizelimit
                        if line.startswith(':'):
                            words = line.split()
                            limit = None
                            if len(words) > 1:
                                try:
                                    limit = int(words[1])
                                except ValueError:
                                    self._log_warn("Can't decode integer"
                                                   " sizelimit on line '%s'"
                                                   " in file %s, using"
                                                   " default."
                                                   % (line, _file))
                            self.add_copy_spec(words[0][1:], sizelimit=limit)
                        else:
                            # command to execute
                            self.add_cmd_output(line, subdir=f)

                except IOError:
                    self._log_warn("unable to read extras file %s" % _file)

# vim: set et ts=4 sw=4 :
