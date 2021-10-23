# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Hpssm(Plugin, IndependentPlugin):

    short_desc = 'HP Smart Storage Management'

    plugin_name = 'hpssm'
    profiles = ('system', 'storage', 'hardware',)
    packages = ('ilorest', 'ssacli', 'ssaducli',)

    option_list = [
        PluginOpt('debug', default=False, desc='capture debug data')
    ]

    def setup(self):
        self.add_cmd_output([
            'ssacli ctrl slot=0 array all show detail',
            'ssacli ctrl slot=0 ld all show detail',
            'ssacli ctrl slot=0 pd all show detail',
            'ssacli ctrl slot=0 show detail',
        ])

        logpath = self.get_cmd_output_path()

        self.add_cmd_output(
            'ssaducli -v -adu -f %s/adu-log.zip' % logpath,
            suggest_filename='ssaducli_-v_-adu.log')

        if self.get_option("debug"):
            self.do_debug(logpath)

    def do_debug(self, logpath):
        self.add_cmd_output(
            'ilorest serverlogs --selectlog=AHS',
            runat=logpath, suggest_filename='ilorest.log')

# vim: set et ts=4 sw=4 :
