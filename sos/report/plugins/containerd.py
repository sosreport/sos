# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Containerd(Plugin, IndependentPlugin):

    short_desc = 'Containerd containers'
    plugin_name = 'containerd'
    profiles = ('container',)
    packages = ('containerd', 'containerd.io',)

    def setup(self):
        self.add_copy_spec([
            "/etc/containerd/",
            "/etc/cni/net.d/",
        ])

        self.add_cmd_output('containerd config dump')
        self.add_cmd_output('ctr deprecations list')

        pre_cmd = 'ctr -n k8s.io'

        self.add_cmd_output([
            f'{pre_cmd} image ls',
            f'{pre_cmd} container ls',
        ])

        # collect the containerd logs.
        self.add_journal(units='containerd')

# vim: set et ts=4 sw=4 :
