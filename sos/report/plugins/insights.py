# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class RedHatInsights(Plugin, RedHatPlugin):
    """Plugin to capture configuration and logging for the Red Hat Insights
    client. Insights is used to provide ongoing analysis of systems for
    proactive problem mitigation, with the client being one of the primary
    sources of data for the service.

    This plugin will capture configuration information under
    /etc/insighits-client, as well as logs from /var/log/insights-client. A
    single connection test via the `insights-client` command is performed and
    recorded as well for troubleshooting purposes.
    """

    short_desc = 'Red Hat Insights configuration and client'
    plugin_name = 'insights'
    packages = ('redhat-access-insights', 'insights-client')
    profiles = ('system', 'sysmgmt')
    config = (
        '/etc/insights-client/insights-client.conf',
        '/etc/insights-client/.registered',
        '/etc/redhat-access-insights/redhat-access-insights.conf'
    )

    def setup(self):
        self.add_copy_spec(self.config)
        self.add_copy_spec('/var/lib/insights')

        # Legacy log file location
        self.add_copy_spec("/var/log/redhat-access-insights/*.log")

        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/insights-client/*.log*")
        else:
            self.add_copy_spec("/var/log/insights-client/insights-client.log")

        self.add_cmd_output(
            "insights-client --test-connection --net-debug",
            timeout=30
        )

    def postproc(self):
        for conf in self.config:
            self.do_file_sub(
                conf, r'(password[\t\ ]*=[\t\ ]*)(.+)', r'\1********'
            )

            self.do_file_sub(
                conf, r'(proxy[\t\ ]*=.*)(:)(.*)(@.*)', r'\1\2********\4'
            )

# vim: set et ts=4 sw=4 :
