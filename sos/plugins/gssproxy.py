# Copyright (C) 2018 Red Hat, Inc., Robbie Harwood <rharwood@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin


class GSSProxy(Plugin):
    """GSSAPI Proxy
    """

    plugin_name = "gssproxy"
    profiles = ('services', 'security', 'identity')
    packages = ('gssproxy',)

    def setup(self):
        self.add_copy_spec([
            "/etc/gssproxy/*.conf",
            "/etc/gss/mech.d/*"
        ])
