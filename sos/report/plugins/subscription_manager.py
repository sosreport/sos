# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from configparser import NoOptionError, NoSectionError
import glob
from sos.report.plugins import Plugin, RedHatPlugin


class SubscriptionManager(Plugin, RedHatPlugin):

    short_desc = 'subscription-manager information'

    plugin_name = 'subscription_manager'
    profiles = ('system', 'packagemanager', 'sysmgmt')

    files = ('/etc/rhsm/rhsm.conf',)
    packages = ('subscription-manager',)

    def get_proxy_string(self, config):
        """ return curl options --proxy[-user] per RHSM config """
        proxy = ""
        proxy_hostname = config.get('server', 'proxy_hostname')
        if proxy_hostname:
            proxy_scheme = config.get('server', 'proxy_scheme')
            proxy_port = config.get('server', 'proxy_port')
            if proxy_port:
                proxy_port = ":" + proxy_port
            proxy = f"--proxy {proxy_scheme}://{proxy_hostname}{proxy_port}"
        proxy_user = config.get('server', 'proxy_user')
        if proxy and proxy_user:
            proxy += f" --proxy-user {proxy_user}"
            proxy_password = config.get('server', 'proxy_password')
            if proxy_password:
                proxy += f":{proxy_password}"
        return proxy

    def get_server_url(self, config):
        """ return URL per RHSM config for curl command """
        secure = "s" if config.get('server', 'insecure') != '1' else ""
        port = config.get('server', 'port')
        # if port is set, prepend it by ':' separating it from hostname
        if len(port) > 0:
            port = ":" + port
        return (f"http{secure}://{config.get('server', 'hostname')}{port}"
                f"{config.get('server', 'prefix')}")

    def setup(self):
        # rhsm config and logs
        self.add_copy_spec([
            "/etc/rhsm/",
            "/var/lib/rhsm/",
            "/var/log/rhsm/rhsm.log",
            "/var/log/rhsm/rhsmcertd.log"])
        self.add_cmd_output("subscription-manager identity",
                            tags="subscription_manager_id")
        self.add_cmd_output("subscription-manager list --consumed",
                            tags="subscription_manager_list_consumed")
        self.add_cmd_output("subscription-manager list --installed",
                            tags="subscription_manager_installed")
        self.add_cmd_output([
            "subscription-manager list --available",
            "subscription-manager list --all --available",
            "subscription-manager release --show",
            "subscription-manager release --list",
            "syspurpose show",
            "subscription-manager syspurpose --show",
            "subscription-manager status",
        ], cmd_as_tag=True)
        self.add_cmd_output("rhsm-debug system --sos --no-archive "
                            "--no-subscriptions --destination "
                            f"{self.get_cmd_output_path()}")

        certs = glob.glob('/etc/pki/product-default/*.pem')
        self.add_cmd_output([f"rct cat-cert {cert}" for cert in certs],
                            tags='subscription_manager_installed_product_ids')

        # try curl to the RHSM server for potential certificate/proxy issue
        curlcmd = "curl -vv --cacert /etc/rhsm/ca/redhat-uep.pem " \
                  "https://subscription.rhsm.redhat.com:443/subscription"
        env = None  # for no_proxy
        try:
            from rhsm.config import get_config_parser  # pylint: disable=C0415
            config = get_config_parser()
            proxy = self.get_proxy_string(config)
            server_url = self.get_server_url(config)
            curlcmd = (f"curl -vv {server_url} --cacert "
                       f"{config.get('rhsm', 'repo_ca_cert')} {proxy}")
            # honour os.environ no_proxy, if set
            no_proxy = config.get('server', 'no_proxy')
            if no_proxy:
                env = {'NO_PROXY': no_proxy}
        except (ModuleNotFoundError, ImportError, NoOptionError,
                NoSectionError) as err:
            self._log_debug(f"Error checking for RHSM cert/proxy issue: {err}")
        self.add_cmd_output(curlcmd, env=env, timeout=30)

    def postproc(self):
        passwdreg = r"(proxy_password(\s)*=(\s)*)(\S+)\n"
        repl = r"\1********\n"
        self.do_path_regex_sub("/etc/rhsm/rhsm.conf", passwdreg, repl)
        # Scrub passwords in repositories
        # Example of scrubbing:
        #
        #   password=hackme
        # To:
        #   password=********
        #
        # Whitespace around '=' is allowed.
        regexp = r"(password(\s)*=(\s)*)(\S+)\n"
        repl = r"\1********\n"
        self.do_path_regex_sub("/var/lib/rhsm/repo_server_val/*", regexp, repl)

# vim: et ts=4 sw=4
