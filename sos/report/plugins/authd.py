# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


# See the docs: https://documentation.ubuntu.com/authd/
class Authd(Plugin, UbuntuPlugin):

    short_desc = 'Authd daemon & broker information'

    plugin_name = 'authd'

    apt_packages = (
        'authd',
    )

    snap_packages = (
        'authd-msentraid',
        'authd-google',
    )

    packages = apt_packages + snap_packages

    services = (
        'authd',
        'snap.authd-msentraid.authd-msentraid',
        'snap.authd-google.authd-google',
    )

    def setup(self):
        self.add_dir_listing([
            "/etc/authd/brokers.d",
        ])

        self.add_copy_spec([
            "/etc/authd/brokers.d/msentraid.conf",
            "/etc/authd/brokers.d/google.conf",
            "/var/snap/authd-google/current/broker.conf",
            "/var/snap/authd-google/current/broker.conf.d/*",
            "/var/snap/authd-msentraid/current/broker.conf",
            "/var/snap/authd-msentraid/current/broker.conf.d/*",
        ])

        self.add_cmd_output([
            f"apt-cache policy {' '.join(self.apt_packages)}",
            f"snap list --all {' '.join(self.snap_packages)}",
            "/usr/libexec/authd version",
        ])

    def postproc(self):
        # Entra uses hex encoded IDs/secrets so just filter all hex data (with
        # `-`) to be safe. These can be generated with uuidgen:
        # $ uuidgen
        # dd591ced-483e-4c47-beaf-ff46f68aab0a
        self.do_path_regex_sub(
            r".*",
            r"[a-fA-F0-9-]{18,}",
            r"******",
        )

        # Google's encoding is less clear, so we'll just filter out the values
        # of the config fields (client_id and client_secret):
        # client_secret = some.base64.stuff.with.domain
        self.do_path_regex_sub(
            r".*",
            r"(.*_(id|secret)\s*=\s*)(.*)",
            r"\1******",
        )
