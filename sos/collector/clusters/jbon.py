# Copyright Red Hat 2020, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.collector.clusters import Cluster


class jbon(Cluster):
    """
    Used when --cluster-type=none (or jbon) to avoid cluster checks, and just
    use the provided --nodes list.

    Using this profile will skip any and all operations that a cluster profile
    normally performs, and will not set any plugins, plugin options, or presets
    for the sos report generated on the nodes provided by --nodes.
    """

    cluster_name = 'Just a Bunch Of Nodes (no cluster)'
    packages = None

    def get_nodes(self):
        return []

    def check_enabled(self):
        # This should never be called, but as insurance explicitly never
        # allow this to be enabled via the determine_cluster() path
        return False

# vim: set et ts=4 sw=4 :
