# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, UbuntuPlugin


class Ubuntu(Plugin, UbuntuPlugin):
    """ Ubuntu specific information
    """

    plugin_name = 'ubuntu'
    profiles = ('system',)

    option_list = [
        ('support-show-all',
         'Show all packages with their status', '', False),
    ]

    def setup(self):
        cmd = ["ubuntu-support-status"]

        if self.get_option('support-show-all'):
            cmd.append("--show-all")

        self.add_cmd_output(" ".join(cmd),
                            suggest_filename='ubuntu-support-status.txt')
