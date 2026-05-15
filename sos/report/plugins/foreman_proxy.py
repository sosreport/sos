# Copyright (C) 2021 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin)


class ForemanProxy(Plugin):

    short_desc = 'Foreman Smart Proxy systems management'

    plugin_name = 'foreman_proxy'
    profiles = ('sysmgmt',)
    packages = ('foreman-proxy', 'foremanctl', )
    containers = ('foreman-proxy', )
    apachepkg = None

    def setup(self):
        self.container = (
            'foreman-proxy'
            if self.container_exists('foreman-proxy')
            else None
        )

        self.add_file_tags({
            '/var/log/foreman-proxy/proxy.log': 'foreman_proxy_log',
            '/etc/foreman-proxy/settings.yml': 'foreman_proxy_conf'
        })
        self.add_cmd_tags({
            'journalctl.*foreman-proxy.service': 'foreman_proxy_log'
        })

        self.add_forbidden_path([
            "/etc/foreman-proxy/*key.pem"
        ])

        self.add_copy_spec(["/etc/foreman-proxy/"], container=self.container)
        if self.container:
            self.add_journal(units="foreman-proxy.service")
        else:
            self.add_copy_spec(["/var/log/foreman-proxy/*log*"])

        self.add_copy_spec([
            f"/var/log/{self.apachepkg}*/katello-reverse-proxy_error_ssl.log*",
            f"/var/log/{self.apachepkg}*/rhsm-pulpcore-https-*access_ssl.log*",
            f"/var/log/{self.apachepkg}*/rhsm-pulpcore-https-*error_ssl.log*",
            f"/var/log/{self.apachepkg}*/katello-reverse-proxy_access_ssl.log*"
        ])

    def postproc(self):
        self.do_path_regex_sub(
            r"/etc/foreman-proxy/(.*)((conf)(.*)?)",
            r"((\:|\s*)(passw|cred|token|secret|key).*(\:\s|=))(.*)",
            r"\1********")
        # yaml values should be alphanumeric
        self.do_path_regex_sub(
            r"/etc/foreman-proxy/(.*)((yaml|yml)(.*)?)",
            r"((\:|\s*)(passw|cred|token|secret|key).*(\:\s|=))(.*)",
            r'\1"********"')


# Child classes needed to declare the apachepkg attr properly per distro

class RedHatForemanProxy(ForemanProxy, RedHatPlugin):

    apachepkg = 'httpd'


class DebianForemanProxy(ForemanProxy, DebianPlugin, UbuntuPlugin):

    apachepkg = 'apache2'


# vim: set et ts=4 sw=4 :
