# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin
import os.path


# This plugin handles OpenShift Enterprise versions up to 2.x
# which are based in the upstream code of OpenShift Origin M4
# located here: https://github.com/openshift/origin-server
#
# For later of OpenShift Origin based on: https://github.com/openshift/origin
# like OpenShift Enterprise 3.x see the origin.py plugin
class Openshift(Plugin, RedHatPlugin):
    '''Openshift 2.x node and broker'''

    plugin_name = "openshift"
    profiles = ('virt', 'openshift')

    # The 'broker' and 'node' options are obsolete but are maintained
    # here for compatibility with external programs that call sosreport
    # with these names.
    option_list = [("broker", "Gathers broker specific files", "slow", False),
                   ("node", "Gathers node specific files", "slow", False)]

    ruby = "ruby193"
    vendor = "rh"
    mco_config_dir = "/opt/%s/%s/root/etc/mcollective" % (vendor, ruby)

    gear_base_dir = "/var/lib/openshift"
    node_settings_dir = os.path.join(gear_base_dir, ".settings")
    node_proxy_dir = os.path.join(gear_base_dir, ".httpd.d")
    httpd_config_dir = "/etc/httpd/conf.d"

    def is_broker(self):
        return os.path.exists("/etc/openshift/broker.conf")

    def is_node(self):
        return os.path.exists("/etc/openshift/node.conf")

    def setup(self):
        self.add_copy_spec([
            "/etc/openshift-enterprise-release",
            "/var/log/openshift",
            "/etc/openshift/*.conf",
            "/etc/openshift/upgrade",
        ])

        self.add_cmd_output("oo-diagnostics -v")

        if self.is_broker():
            self.add_copy_spec([
                "/etc/openshift/quickstarts.json",
                "/etc/openshift/plugins.d/*.conf",
                os.path.join(self.mco_config_dir, "client.cfg"),
                "/var/www/openshift/broker/httpd/httpd.conf",
                "/var/www/openshift/broker/httpd/conf.d/*.conf",
                "/var/www/openshift/console/httpd/httpd.conf",
                "/var/www/openshift/console/httpd/conf.d/*.conf",
            ])

            self.add_cmd_output([
                "oo-accept-broker -v",
                "oo-admin-chk -v",
                "oo-mco ping",
            ])

        if self.is_node():
            self.add_copy_spec([
                "/etc/openshift/node-plugins.d/*.conf",
                "/etc/openshift/cart.conf.d",
                "/etc/openshift/iptables.*.rules",
                "/etc/openshift/env",
                os.path.join(self.httpd_config_dir,
                             "openshift-vhost-logconf.include"),
                os.path.join(self.httpd_config_dir,
                             "openshift-http-vhost.include"),
                os.path.join(self.httpd_config_dir,
                             "openshift_restorer.include"),
                os.path.join(self.mco_config_dir, "server.cfg"),
                os.path.join(self.mco_config_dir, "facts.yaml"),
                os.path.join(self.node_settings_dir, "district.info"),
                os.path.join(self.node_proxy_dir, "*.conf"),
                os.path.join(self.node_proxy_dir, "aliases.txt"),
                os.path.join(self.node_proxy_dir, "nodes.txt"),
                os.path.join(self.node_proxy_dir, "idler.txt"),
                os.path.join(self.node_proxy_dir, "sts.txt"),
                os.path.join(self.node_proxy_dir, "routes.json"),
                os.path.join(self.node_proxy_dir, "geardb.json"),
                os.path.join(self.node_proxy_dir, "sniproxy.json"),
                "/var/log/httpd/openshift_log",
                "/var/log/mcollective.log",
                "/var/log/node-web-proxy/access.log",
                "/var/log/node-web-proxy/error.log",
                "/var/log/node-web-proxy/websockets.log",
                "/var/log/node-web-proxy/supervisor.log",
            ])

            self.add_cmd_output([
                "oo-accept-node -v",
                "oo-admin-ctl-gears list",
                "ls -laZ %s" % self.gear_base_dir,
                "ls -la %s" % self.node_proxy_dir
            ])

    def postproc(self):
        # Redact broker's MongoDB credentials:
        # MONGO_PASSWORD="PasswordForOpenshiftUser"
        self.do_file_sub('/etc/openshift/broker.conf',
                         r"(MONGO_PASSWORD\s*=\s*)(.*)",
                         r"\1*******")

        # Redact session SHA keys:
        # SESSION_SECRET=0c31...a7c8
        self.do_file_sub('/etc/openshift/broker.conf',
                         r"(SESSION_SECRET\s*=\s*)(.*)",
                         r"\1*******")
        self.do_file_sub('/etc/openshift/console.conf',
                         r"(SESSION_SECRET\s*=\s*)(.*)",
                         r"\1*******")

        # Redact passwords of the form:
        # plugin.activemq.pool.1.password = Pa$sW0Rd
        self.do_file_sub(os.path.join(self.mco_config_dir, "server.cfg"),
                         r"(.*password\s*=\s*)\S+",
                         r"\1********")
        self.do_file_sub(os.path.join(self.mco_config_dir, "client.cfg"),
                         r"(.*password\s*=\s*)\S+",
                         r"\1********")

        # Redact DNS plugin credentials
        # Dynect DNS: DYNECT_PASSWORD=s0ME-p4$_w0RD._
        plugin_dir = '/etc/openshift/plugins.d/'
        self.do_file_sub(plugin_dir + 'openshift-origin-dns-dynect.conf',
                         r"(DYNECT_PASSWORD\s*=\s*)(.*)",
                         r"\1********")
        # Fog cloud: FOG_RACKSPACE_API_KEY="apikey"
        self.do_file_sub(plugin_dir + 'openshift-origin-dns-fog.conf',
                         r"(FOG_RACKSPACE_API_KEY\s*=\s*)(.*)",
                         r"\1********")
        # ISC bind: BIND_KEYVALUE="rndc key"
        self.do_file_sub(plugin_dir + 'openshift-origin-dns-nsupdate.conf',
                         r"(BIND_KEYVALUE\s*=\s*)(.*)",
                         r"\1********")
        # LDAP authentication:  AuthLDAPBindPassword "IShouldNotBeHere"
        ldap_paths = '/var/www/openshift/(broker|console)/httpd/conf.d/.*'
        self.do_path_regex_sub(ldap_paths,
                               r"(AuthLDAPBindPassword)\s*(.*)",
                               r"\1********")

# vim: set et ts=4 sw=4 :
