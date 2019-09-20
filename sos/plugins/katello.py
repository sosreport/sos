# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin
import os.path


class Katello(Plugin, RedHatPlugin):
    """Katello application life-cycle management"""

    plugin_name = 'katello'
    packages = ('katello',)

    def setup(self):
        self.add_copy_spec([
            "/var/log/httpd/katello-reverse-proxy_access_ssl.log*",
            "/var/log/httpd/katello-reverse-proxy_error_ssl.log*"
        ])

        # certificate file location relies on katello version, it can be either
        # /etc/pki/katello/qpid_client_striped.crt (for older versions) or
        # /etc/pki/pulp/qpid/client.crt (for newer versions)
        cert = "/etc/pki/pulp/qpid/client.crt"
        if not os.path.isfile(cert):
            cert = "/etc/pki/katello/qpid_client_striped.crt"
        self.add_cmd_output([
            "qpid-stat -%s --ssl-certificate=%s -b amqps://localhost:5671" %
            (opt, cert) for opt in "quc"
        ])


# vim: set et ts=4 sw=4 :
