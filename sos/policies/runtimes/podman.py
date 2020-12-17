# Copyright (C) 2020 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.policies.runtimes import ContainerRuntime


class PodmanContainerRuntime(ContainerRuntime):
    """Runtime class to use for systems running Podman"""

    name = 'podman'
    binary = 'podman'


# vim: set et ts=4 sw=4 :
