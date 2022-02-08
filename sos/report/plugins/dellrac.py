# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class DellRAC(Plugin, IndependentPlugin):

    short_desc = 'Dell Remote Access Controller Administration'

    plugin_name = 'dellrac'
    profiles = ('system', 'storage', 'hardware',)
    packages = ('srvadmin-idracadm7',)

    option_list = [
        PluginOpt('debug', default=False, desc='capture support assist data')
    ]

    racadm = '/opt/dell/srvadmin/bin/idracadm7'
    prefix = 'idracadm7'

    def setup(self):
        for subcmd in ['getniccfg', 'getsysinfo']:
            self.add_cmd_output(
                '%s %s' % (self.racadm, subcmd),
                suggest_filename='%s_%s' % (self.prefix, subcmd))

        if self.get_option("debug"):
            self.do_debug()

    def do_debug(self):
        # ensure the sos_commands/dellrac directory does exist in either case
        # as we will need to run the command at that dir, and also ensure
        # logpath is properly populated in either case as well
        try:
            logpath = self.get_cmd_output_path()
        except FileExistsError:
            logpath = self.get_cmd_output_path(make=False)
        subcmd = 'supportassist collect -f'
        self.add_cmd_output(
            '%s %s support.zip' % (self.racadm, subcmd),
            runat=logpath, suggest_filename='%s_%s' % (self.prefix, subcmd))

# vim: set et ts=4 sw=4 :
