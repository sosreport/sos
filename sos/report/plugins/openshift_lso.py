# openshift_lso.py
# Copyright (C) 2007-2025 Red Hat, Inc., Jon Magrini <jmagrini@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin)

class OpenshiftLSO(Plugin, RedHatPlugin):
    """
    This plugin is used to collect Openshift LSO details. This expands 
    the ceph_osd plugin since storage nodes by default are not setup for
    ceph access. When gathering data from an OpenShift node when LSO is in use, 
    we currently do not collect the symlink data location for LSO, 
    which is always under /mnt (basically two layers lower, 
    but the names can change). This is useful in determining if LSO 
    is setup correctly when also having a must-gather output.  
    Many times the LSO directory has pointers to paths instead of devices. 
    This can cause issues with lost access to the OCP backend storage 
    used by OpenShift.
    """

    short_desc = 'Openshift LSO'
    
    plugin_name = "openshift_lso"
    profiles = ('storage', 'openshift', 'ceph')
    # Each node runs the ceph-osd daemon,
    # which interacts with logical disks attached to the node.
    files = '/run/ceph/**/ceph-osd*'
    
    def setup(self):
        self.add_cmd_output([
            'ls -lanR /mnt'
        ])
