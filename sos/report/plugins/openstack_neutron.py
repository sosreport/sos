# Copyright (C) 2013 Red Hat, Inc., Brent Eagles <beagles@redhat.com>
# Copyright (C) 2017 Red Hat, Inc., Martin Schuppert <mschuppert@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenStackNeutron(Plugin):

    short_desc = 'OpenStack Networking'
    plugin_name = "openstack_neutron"
    profiles = ('openstack', 'openstack_controller',
                'openstack_compute', 'openstack_edpm')

    var_puppet_gen = "/var/lib/config-data/puppet-generated/neutron"

    def setup(self):
        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/neutron/",
            ])
        else:
            self.add_copy_spec([
                "/var/log/neutron/*.log",
            ])

        self.add_copy_spec([
            "/etc/neutron/",
            self.var_puppet_gen + "/etc/neutron/",
            self.var_puppet_gen + "/etc/default/neutron-server",
            self.var_puppet_gen + "/etc/my.cnf.d/tripleo.cnf"
        ])
        # copy whole /var/lib/neutron except for potentially huge lock subdir;
        # rather take a list of files in the dir only
        self.add_copy_spec("/var/lib/neutron/")
        self.add_forbidden_path("/var/lib/neutron/lock")
        self.add_dir_listing('/var/lib/neutron/lock', recursive=True)

        if self.path_exists(self.var_puppet_gen):
            ml2_pre = self.var_puppet_gen
        else:
            ml2_pre = ""

        ml2_conf_file = f"{ml2_pre}/etc/neutron/plugins/ml2/ml2_conf.ini"

        ml2_certs = []

        ml2_cert_keys = [
            'ovn_nb_private_key',
            'ovn_nb_certificate',
            'ovn_nb_ca_cert',
            'ovn_sb_private_key',
            'ovn_sb_certificate',
            'ovn_sb_ca_cert',
        ]

        try:
            with open(ml2_conf_file, 'r', encoding='UTF-8') as cfile:
                for line in cfile.read().splitlines():
                    if not line:
                        continue
                    words = line.split('=')
                    if words[0].strip() in ml2_cert_keys:
                        ml2_certs.append(words[1].strip())
        except IOError as error:
            self._log_error(f'Could not open conf file {ml2_conf_file}:'
                            f' {error}')

        self.add_forbidden_path(ml2_certs)

        vars_all = [p in os.environ for p in [
                    'OS_USERNAME', 'OS_PASSWORD']]

        vars_any = [p in os.environ for p in [
                    'OS_TENANT_NAME', 'OS_PROJECT_NAME']]

        if not (all(vars_all) and any(vars_any)):
            self.soslog.warning("Not all environment variables set. Source "
                                "the environment file for the user intended "
                                "to connect to the OpenStack environment.")
        else:
            cmds = [
                "subnet",
                "port",
                "router",
                "network agent",
                "network",
                "extension",
                "floating ip",
                "security group",
            ]

            for cmd in cmds:
                res = self.collect_cmd_output(f"openstack {cmd} list")

                if res['status'] == 0:
                    neutron_items = res['output']
                    for item in neutron_items.splitlines()[3:-1]:
                        item = item.split()[1]
                        show_cmd = f"openstack {cmd} show {item}"
                        self.add_cmd_output(show_cmd)

        self.add_file_tags({
            ".*/etc/neutron/plugins/ml2/ml2_conf.ini": "neutronml2_conf",
            "/var/log/neutron/server.log": "neutron_server_log"
        })

    def apply_regex_sub(self, regexp, subst):
        """ Apply regex substitution """
        self.do_path_regex_sub("/etc/neutron/*", regexp, subst)
        self.do_path_regex_sub(
            self.var_puppet_gen + "/etc/neutron/*",
            regexp, subst
        )

    def postproc(self):
        protect_keys = [
            "(.*_)?(key|password|secret)",
            "server_?auth",
            "transport_url",
        ]
        connection_keys = ["connection"]

        join_con_keys = "|".join(connection_keys)

        self.apply_regex_sub(
            fr"(^\s*({'|'.join(protect_keys)})\s*=\s*)(.*)",
            r"\1*********"
        )
        self.apply_regex_sub(
            fr"(^\s*({join_con_keys})\s*=\s*(.*)://(\w*):)(.*)(@(.*))",
            r"\1*********\6"
        )


class DebianNeutron(OpenStackNeutron, DebianPlugin, UbuntuPlugin):
    packages = (
        'neutron-common',
        'neutron-plugin-cisco',
        'neutron-plugin-linuxbridge-agent',
        'neutron-plugin-nicira',
        'neutron-plugin-openvswitch',
        'neutron-plugin-openvswitch-agent',
        'neutron-plugin-ryu',
        'neutron-plugin-ryu-agent',
        'neutron-server',
        'python-neutron',
        'python3-neutron',
    )

    def check_enabled(self):
        return self.is_installed("neutron-common")

    def setup(self):
        super().setup()
        self.add_copy_spec("/etc/sudoers.d/neutron_sudoers")


class RedHatNeutron(OpenStackNeutron, RedHatPlugin):

    packages = ('openstack-selinux',)
    var_ansible_gen = "/var/lib/config-data/ansible-generated/"

    def setup(self):
        super().setup()
        self.add_copy_spec([
            "/etc/sudoers.d/neutron-rootwrap",
            self.var_ansible_gen + "/neutron-dhcp-agent/",
            self.var_ansible_gen + "/neutron-dhcp-ovn/",
            self.var_ansible_gen + "/neutron-sriov-agent/"
        ])

# vim: set et ts=4 sw=4 :
