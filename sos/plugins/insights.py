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
    packages = ['redhat-access-insights', 'insights-client']
    profiles = ('system', 'sysmgmt')
    config = (
        '/etc/insights-client/insights-client.conf',
        '/etc/redhat-access-insights/redhat-access-insights.conf'
    )

    def setup(self):
        self.add_copy_spec(self.config)

        # Legacy log file location
        self.add_copy_spec("/var/log/redhat-access-insights/*.log")

        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/insights-client/*.log*")
        else:
            self.add_copy_spec("/var/log/insights-client/insights-client.log")

    def postproc(self):
        for conf in self.config:
            self.do_file_sub(
                conf, r'(password[\t\ ]*=[\t\ ]*)(.+)', r'\1********'
            )

            self.do_file_sub(
                conf, r'(proxy[\t\ ]*=.*)(:)(.*)(@.*)', r'\1\2********\4'
            )
