# Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>
# Copyright (C) 2019 Red Hat Inc., Stepan Broz <sbroz@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Libreswan(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Libreswan IPsec
    """

    plugin_name = 'libreswan'
    profiles = ('network', 'security', 'openshift')
    option_list = [
        ("ipsec-barf", "collect the output of the ipsec barf command",
         "slow", False)
    ]

    files = ('/etc/ipsec.conf',)
    packages = ('libreswan', 'openswan')

    def setup(self):
        self.add_copy_spec([
            "/etc/ipsec.conf",
            "/etc/ipsec.d",
            "/proc/net/xfrm_stat"
        ])

        # although this is 'verification' it's normally a very quick
        # operation so is not conditional on --verify
        self.add_cmd_output([
            'ipsec verify',
            'ipsec whack --status',
            'ipsec whack --listall',
            'certutil -L -d sql:/etc/ipsec.d',
            'ip xfrm policy',
            'ip xfrm state'
        ])

        if self.get_option("ipsec-barf"):
            self.add_cmd_output("ipsec barf")

        self.add_forbidden_path([
            '/etc/ipsec.secrets',
            '/etc/ipsec.secrets.d',
            '/etc/ipsec.d/*.db',
            '/etc/ipsec.d/*.secrets'
        ])

    def postproc(self):
        # Remove any sensitive data.
        # "ip xfrm state" output contains encryption or authentication private
        # keys:
        xfrm_state_regexp = r'(aead|auth|auth-trunc|enc)' \
                            r'(\s.*\s)(0x[0-9a-f]+)'
        self.do_cmd_output_sub("state", xfrm_state_regexp,
                               r"\1\2********")

        if self.get_option("ipsec-barf"):
            self.do_cmd_output_sub("barf", xfrm_state_regexp,
                                   r"\1\2********")

# vim: set et ts=4 sw=4 :
