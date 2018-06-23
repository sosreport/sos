# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class RedHatInsights(Plugin, RedHatPlugin):
    '''Collect config and log for Red Hat Insights
    '''
    plugin_name = 'insights'
    packages = ['redhat-access-insights']
    profiles = ('system', 'sysmgmt')
    conf_file = '/etc/redhat-access-insights/redhat-access-insights.conf'

    def setup(self):
        self.add_copy_spec(self.conf_file)
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/redhat-access-insights/*.log*")
        else:
            self.add_copy_spec("/var/log/redhat-access-insights/*.log")

    def postproc(self):
        self.do_file_sub(
            self.conf_file,
            r'(password[\t\ ]*=[\t\ ]*)(.+)',
            r'\1********'
        )

        self.do_file_sub(
            self.conf_file,
            r'(proxy[\t\ ]*=.*)(:)(.*)(@.*)',
            r'\1\2********\4'
        )
