# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt


class Veritas(Plugin, RedHatPlugin):

    short_desc = 'Veritas software'

    plugin_name = 'veritas'
    profiles = ('cluster', 'storage')

    # Information about VRTSexplorer obtained from
    # http://seer.entsupport.symantec.com/docs/243150.htm
    option_list = [
        PluginOpt('script', default='/opt/VRTSspt/VRTSexplorer',
                  desc='Path to VRTSexploer script')
    ]

    def check_enabled(self):
        return self.path_isfile(self.get_option("script"))

    def setup(self):
        """ interface with vrtsexplorer to capture veritas related data """
        r = self.exec_cmd(self.get_option("script"))
        if r['status'] == 0:
            tarfile = ""
            for line in r['output']:
                line = line.strip()
                tarfile = self.do_regex_find_all(r"ftp (.*tar.gz)", line)
            if len(tarfile) == 1:
                self.add_copy_spec(tarfile[0])

# vim: set et ts=4 sw=4 :
