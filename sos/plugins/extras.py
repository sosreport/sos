# Copyright (C) 2019 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin
import os


class Extras(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """Extras plugin to collect user declared commands outputs
       The plugin traverses /etc/sos.extras.d directory and for each
       file there, it executes each line as a bash command.
    """

    plugin_name = 'extras'

    def setup(self):
        _dir = '/etc/sos.extras.d'

        if os.path.isdir(_dir):
            try:
                for _file in os.listdir(_dir):
                    # ignore hidden files
                    if _file.startswith("."):
                        continue
                    p = os.path.join(_dir, _file)
                    for line in open(p).read().splitlines():
                        self.add_cmd_output(line, subdir=_file)
            except IOError as e:
                # fallback when the cfg file is not accessible
                self._log_warn("Unable to exec extras due to %s" % e)


# vim: et ts=4 sw=4
