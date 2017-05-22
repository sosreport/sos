# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

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
        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/redhat-access-insights/*.log*",
                               sizelimit=self.limit)
        else:
            self.add_copy_spec("/var/log/redhat-access-insights/*.log",
                               sizelimit=self.limit)

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
