# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class SEDUtility(Plugin, IndependentPlugin):
    """
    Collects information about SED drives installed on host system.
    This plugin will capture data using sedutil utility
    """

    short_desc = 'Self Encrypting Drives'
    plugin_name = 'sedutil'
    profiles = ('security', 'system', 'storage', 'hardware')
    packages = ('sedutil',)

    option_list = [
        PluginOpt('debug', default=False, desc='capture debug data'),
    ]

    def setup(self):
        sed_list = []
        result = self.collect_cmd_output('sedutil-cli --scan')

        if self.get_option("debug"):
            if 0 == result['status']:
                # iterate over all the devices returned and
                # create a list of SED drives.
                for line in result['output'].splitlines():
                    if line.startswith("/dev/"):
                        line = line.split()
                        disk, tcg_opal_dev = line[:2]
                        # Check if it is SED device or not
                        if "2" == tcg_opal_dev:
                            sed_list.append(disk)
            self.do_debug(sed_list)

    def do_debug(self, sed_list):
        """ Collect debug logs """
        for device in sed_list:
            self.add_cmd_output(f"sedutil-cli --query {device}")

# vim: set et ts=4 sw=4 :
