# Copyright 2023 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins.openshift import Openshift
from sos.utilities import is_executable


class Microshift(Openshift):
    """
    For Microshift users, this plugin does not need to perform any oauth steps
    of any kind. Users should see the `microshift` plugin enable and NOT the
    `openshift` plugin during a normal execution of `sos report`. All plugin
    options are otherwise the same, however users should note that the `token`
    option is ignored by the Microshift plugin variant.
    """

    short_desc = 'Microshift Container Platform'
    plugin_name = 'microshift'
    packages = ('microshift',)
    services = ('microshift',)
    profiles = ()
    master_localhost_kubeconfig = ''  # TODO: is there a default kubeconfig?

    def _check_oc_function(self):
        """Microshift does not have the oauth bits that enable the ``oc login``
        or ``oc whoami`` commands. As such, the ``oc`` commands are otherwise
        simply available for use. In this case, don't block API collections
        as the Openshift plugin would when these non-existent commands fail.
        """
        # is there an `oc` command we can run that's not `oc whoami` safely
        # that we can use with microshift?
        return is_executable('oc')

    def get_global_resource_list(self):
        return []  # TODO: define non-namespaced resources to collect

    def get_namespaced_resource_list(self):
        """
        Microshift does not support all the same resources as OCP does, so we
        need to define a shorter list here that only specifies the resources
        we care about in a microshift environment.
        """
        return [
            'configmaps',
            'daemonsets',
            'deployments',
            'events',
            'ingresscontrollers',
            'ingresses',
            'pods',
            'pvc',
            'resourcequotas',
            'routes',
            'secrets',
            'services',
            'statefulsets',
        ]

    def setup(self):
        super(Microshift, self).setup()
        # TODO: add microshift-specific collections here that should not be
        # included in the parent openshift plugin
