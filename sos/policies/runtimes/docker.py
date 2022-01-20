# Copyright (C) 2020 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.policies.runtimes import ContainerRuntime
from sos.utilities import is_executable


class DockerContainerRuntime(ContainerRuntime):
    """Runtime class to use for systems running Docker"""

    name = 'docker'
    binary = 'docker'

    def check_is_active(self, sysroot=None):
        # the daemon must be running
        if (is_executable('docker', sysroot) and
                (self.policy.init_system.is_running('docker') or
                 self.policy.init_system.is_running('snap.docker.dockerd'))):
            self.active = True
            return True
        return False

    def check_can_copy(self):
        return self.check_is_active(sysroot=self.policy.sysroot)

# vim: set et ts=4 sw=4 :
