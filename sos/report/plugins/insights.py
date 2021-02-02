# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class RedHatInsights(Plugin, RedHatPlugin):

    short_desc = 'Collect config and logs for Red Hat Insights'
    plugin_name = 'insights'
    packages = ['redhat-access-insights', 'insights-client']
    profiles = ('system', 'sysmgmt')
    config = (
        '/etc/insights-client/insights-client.conf',
        '/etc/insights-client/.registered',
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

        # Collect insights-client report data into given dump dir
        path = self.get_cmd_output_path(name="insights-client-dump")
        self.add_cmd_output("insights-client --offline --output-dir %s" % path,
                            suggest_filename="insights-client-dump.log")

    def postproc(self):
        for conf in self.config:
            self.do_file_sub(
                conf, r'(password[\t\ ]*=[\t\ ]*)(.+)', r'\1********'
            )

            self.do_file_sub(
                conf, r'(proxy[\t\ ]*=.*)(:)(.*)(@.*)', r'\1\2********\4'
            )

# vim: set et ts=4 sw=4 :
