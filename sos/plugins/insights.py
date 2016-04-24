# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin


class RedHatAccessInsights(Plugin, RedHatPlugin):
    '''Collect config and log for Red Hat Access Insights
    '''
    plugin_name = 'insights'
    packages = ['redhat-access-insights']
    profiles = ('system', 'sysmgmt')
    conf_file = '/etc/redhat-access-insights/redhat-access-insights.conf'

    def setup(self):
        log_size = self.get_option('log_size')
        self.add_copy_spec(self.conf_file)
        self.add_copy_spec_limit('/var/log/redhat-access-insights/*.log',
                                 sizelimit=log_size)

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
