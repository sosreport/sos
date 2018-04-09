# Copyright (C) 2017 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin
import os


class DockerDistribution(Plugin):

    """Docker Distribution"""

    plugin_name = "docker_distribution"
    profiles = ('container',)

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
