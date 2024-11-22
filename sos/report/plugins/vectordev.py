# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class VectorDev(Plugin, IndependentPlugin):

    short_desc = 'A tool for building observability pipelines'

    plugin_name = "vectordev"
    profiles = ('observability',)
    files = ('/etc/vector/',)

    def setup(self):
        self.add_copy_spec([
            "/etc/vector/"
        ])

    def postproc(self):

        vector_config_path = "/etc/vector/*"
        protect_keys = [
            "auth.password",
            "auth.token",
            "tls.key_pass",
        ]

        # Redact yaml and ini style "key (:|=) value".
        keys_regex = fr"(^\s*({'|'.join(protect_keys)})\s*(:|=)\s*)(.*)"
        sub_regex = r"\1*********"
        self.do_path_regex_sub(vector_config_path, keys_regex, sub_regex)
        # Redact certificates
        self.do_file_private_sub(vector_config_path)


# vim: et ts=4 sw=4
