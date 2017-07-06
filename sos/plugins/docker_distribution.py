# Copyright (C) 2017 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>
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
import os


class DockerDistribution(Plugin):

    """Docker Distribution"""

    plugin_name = "docker_distribution"

    def setup(self):
        self.add_copy_spec('/etc/docker-distribution/')
        self.add_journal('docker-distribution')
        if os.path.exists('/etc/docker-distribution/registry/config.yml'):
            with open('/etc/docker-distribution/registry/config.yml') as f:
                for line in f:
                    if 'rootdirectory' in line:
                        loc = line.split()[1]
                        self.add_cmd_output('tree ' + loc)


class RedHatDockerDistribution(DockerDistribution, RedHatPlugin):

    packages = ('docker-distribution',)

    def setup(self):
        self.add_forbidden_path('/etc/docker-distribution/registry/*passwd')
        super(RedHatDockerDistribution, self).setup()
