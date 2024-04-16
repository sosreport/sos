# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


class CanonicaLivepatchOnprem(Plugin, UbuntuPlugin):

    short_desc = 'Canonical Livepatch Onprem Service'

    plugin_name = 'canonical_livepatch_onprem'
    profiles = ('services',)
    services = ("livepatch-server",)

    def setup(self):
        self.add_copy_spec([
            "/etc/livepatchd.yaml",
        ])

    def postproc(self):
        onprem_conf = "/etc/livepatchd.yaml"
        protect_keys = [
            "username",
            "password",
            "token",
            "connection_string",
        ]

        # Redact simple yaml style "key: value".
        keys_regex = fr"(^(-|\s)*({'|'.join(protect_keys)})\s*:\s*)(.*)"
        sub_regex = r"\1*********"
        self.do_path_regex_sub(onprem_conf, keys_regex, sub_regex)

        # Redact conf
        self.do_file_private_sub(onprem_conf)

# vim: set et ts=4 sw=4 :
