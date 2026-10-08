# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.report.plugins import Plugin, IndependentPlugin


class Puppet(Plugin, IndependentPlugin):

    short_desc = 'Puppet/Openvox services'

    plugin_name = 'puppet'
    profiles = ('services',)
    packages = ('openvox-agent', 'openvox-server', 'openvoxdb',
                'puppet', 'puppet-agent', 'puppet-common', 'puppet-server',
                'puppetserver', 'puppetmaster', 'puppet-master', 'puppetdb')
    services = ('puppet', 'puppetserver', 'puppetdb')

    def setup(self):
        _hostname = self.exec_cmd('hostname')['output']
        _hostname = _hostname.strip()
        x509_opts = '-noout -dates -subject'
        crl_opts = '-noout -lastupdate -nextupdate -issuer -crlnumber'
        ssl_dir = '/etc/puppetlabs/puppet/ssl'

        self.add_copy_spec([
            # Agent
            "/etc/puppet/*.conf",
            "/etc/puppet/hiera.yaml",
            "/etc/puppet/rack/*",
            "/etc/puppet/manifests/*",
            "/etc/puppetlabs/puppet/*.conf",
            "/etc/puppetlabs/puppet/hiera.yaml",
            "/etc/puppetlabs/puppet/routes.yaml",
            # Server
            "/etc/puppetlabs/puppetserver/*.xml",
            "/etc/puppetlabs/puppetserver/conf.d/*",
            "/etc/puppetlabs/puppetserver/services.d/*",
            # Database
            "/etc/puppetlabs/puppetdb/*.cfg",
            "/etc/puppetlabs/puppetdb/*.xml",
            "/etc/puppetlabs/puppetdb/conf.d/*",
            # Code
            "/etc/puppetlabs/code/hiera.yaml",
            "/etc/puppetlabs/r10k/r10k.yaml",
            # Startup
            "/etc/sysconfig/puppet*",
            "/etc/default/puppet*",
            # State
            "/opt/puppetlabs/puppet/cache/state/*.txt",
            "/opt/puppetlabs/puppet/cache/state/*.lock",
            "/opt/puppetlabs/puppet/cache/state/*.yaml",
            "/opt/puppetlabs/puppet/public/last_run_summary.yaml",
            # Logs
            "/var/log/puppet/*.log*",
            "/var/log/puppetlabs/puppet/*.log*",
            "/var/log/puppetlabs/puppetdb/*.log*",
            "/var/log/puppetlabs/puppetserver/*.log*",
            # Certs/Inventory
            "/etc/puppetlabs/puppet/ssl/ca/ca_crl.pem",
            "/etc/puppetlabs/puppet/ssl/ca/ca_crt.pem",
            "/etc/puppetlabs/puppet/ssl/ca/inventory.txt",
            "/var/lib/puppetlabs/puppet/ssl/ca/inventory.txt",
            "/var/lib/puppet/ssl/ca/inventory.txt",
            "/var/lib/puppet/ssl/certs/ca.pem",
            f"/etc/puppetlabs/puppet/ssl/certs/{_hostname}.pem",
            f"/var/lib/puppet/ssl/certs/{_hostname}.pem",
        ])
        self.add_copy_spec("/etc/puppetlabs/puppet/ssl/certs/ca.pem",
                           tags="puppet_ssl_cert_ca_pem")

        self.env = {'PATH': "/opt/puppetlabs/puppet/bin"
                    f":{os.environ['PATH']}"
                    ":/opt/puppetlabs/bin"}
        self.add_cmd_output([
            # Agent
            'facter',
            'puppet --version',
            'puppet config print --section main',
            'gem list --local',
            # Server
            'puppet config print --section server',
            'puppetserver --version',
            'puppetserver gem list --local',
            # Code
            'puppet module list --tree',
            # State
            'curl -k https://localhost:8140/status/v1/services?level=debug',
            'curl http://localhost:8080/pdb/admin/v1/summary-stats',
            'curl http://localhost:8080/status/v1/services?level=debug',
            # Certs/Inventory
            f'openssl x509 -in {ssl_dir}/ca/ca_crt.pem {x509_opts}',
            f'openssl x509 -in {ssl_dir}/certs/ca.pem {x509_opts}',
            f'openssl crl -in {ssl_dir}/crl.pem {crl_opts}',
        ], env=self.env)

        self.add_dir_listing([
            '/etc/puppet/modules',
            '/etc/puppetlabs/code/modules'
        ], recursive=True)

    def postproc(self):
        # Sorry in advance, but it's this or writing for every variant of
        # every file. We select a list of common phrases...
        sensitive_list = [
            'access[_-]?key', 'api[_-]?key', '(?<!by)pass',
            'forge_authorization', 'password', 'passwd', 'passphrase',
            'secret', 'secret_id', 'secret[_-]?key', 'token',
        ]
        # stitched into a bunch of 'or' operators...
        joined_list = "|".join(sensitive_list)
        # with an exception made (this value is a useful file path)...
        not_a_secret = r"(?!oauth[_-]token\b)"
        # combined, along with any prefix of characters (ie "auth_pass")...
        param = not_a_secret + r"[\w.:-]*(" + joined_list + r")"
        # find the proceding non-empty sequence with spaces as delimiters...
        not_none = r"(?!none\b)"
        value = not_none + r"\S.*"
        # ...and turn it into these little monsters, which makes it case
        # insensitive, per-line, regardless of comment symbols, and accounting
        # for various permutations (ini, YAML, json etc) it selects the value.
        ec2_regex = r"(?ms)^(ec2_userdata => ).*?(\n[\w.-]+ => |\Z)"
        export_regex = (r"(?im)^([ \t#]*export[ \t]+" + param
                        + r"=)" + value)
        # https://www.yaml.info/learn/flowstyle.html
        flow_style_regex = (r"(?i)([{,][ \t]*[\"']?" + param
                            + r"[\"']?[ \t]*[:=][ \t]*)[^,}\n]+")
        hashrocket_regex = (r"(?im)^([ \t#]*[\"']?" + param
                            + r"[\"']?[ \t]*=>[ \t])" + value)
        ini_regex = (r"(?im)^([ \t#;/]*[\"']?" + param
                     + r"[\"']?[ \t]*=(?!>)[ \t]*)" + value)
        java_args_regex = r"(?i)(-D[\w.]*(pass|password)=[\"']?)[^\s\"']+"
        tokenbearer_regex = (r"(?i)(authorization:[ \t]*[\"']?(bearer|basic) )"
                             + r"[^\"'\s]+")
        url_pass_regex = r"(\b\w+://[^:@/?#\s]*:)[^@/?#\s]+@"
        url_query_regex = (r"(?i)([?&]"
                           + r"(enable|\w*password|\w*token|\w*secret)"
                           + r"=)[^&\s]+")
        url_token_regex = r"(?i)(\bhttps?://)[^@/?#\s]+@"
        variable_regex = (r"(?im)^([ \t#]*\$" + param
                          + r"[ \t]*=[ \t]*)" + value)
        yaml_regex = (r"(?im)^([ \t#;/]*(?:-[ \t]+)?[\"']?" + param
                      + r"[\"']?[ \t]*:[ \t]*)" + value)

        files = r".*(?<!\.gz)$"
        for regex in (export_regex, flow_style_regex, hashrocket_regex,
                      ini_regex, java_args_regex, tokenbearer_regex,
                      url_pass_regex, url_query_regex, url_token_regex,
                      variable_regex, yaml_regex):
            self.do_path_regex_sub(files, regex, r"\1********")
            self.do_cmd_output_sub("*", regex, r"\1********")
        self.do_cmd_output_sub("facter", ec2_regex, r"\1********\2")

# vim: et ts=4 sw=4
