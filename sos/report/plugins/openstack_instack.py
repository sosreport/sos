# Copyright (C) 2015 Red Hat, Inc., Lee Yarwood <lyarwood@redhat.com>
# Copyright (C) 2017 Red Hat, Inc., Martin Schuppert <mschuppert@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import configparser
import os
import re
from sos.report.plugins import Plugin, RedHatPlugin


NON_CONTAINERIZED_DEPLOY = [
        '/home/stack/.instack/install-undercloud.log',
        '/home/stack/instackenv.json',
        '/home/stack/undercloud.conf'
]
CONTAINERIZED_DEPLOY = [
        '/var/log/heat-launcher/',
        '/home/stack/ansible.log',
        '/home/stack/config-download/',
        '/home/stack/install-undercloud.log',
        '/home/stack/undercloud-install-*.tar.bzip2',
        '/home/stack/.tripleo/history',
        '/var/lib/tripleo-config/',
        '/var/log/tripleo-container-image-prepare.log',
]
UNDERCLOUD_CONF_PATH = '/home/stack/undercloud.conf'


class OpenStackInstack(Plugin):

    short_desc = 'OpenStack Instack'
    plugin_name = "openstack_instack"
    profiles = ('openstack', 'openstack_undercloud')

    def setup(self):
        self.add_copy_spec(NON_CONTAINERIZED_DEPLOY + CONTAINERIZED_DEPLOY)

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/zaqar/",
            ])
        else:
            self.add_copy_spec([
                "/var/log/zaqar/*.log",
            ])

        self.add_file_tags({
            "/var/log/mistral/executor.log": "mistral_executor_log"
        })

        vars_all = [p in os.environ for p in [
                    'OS_USERNAME', 'OS_PASSWORD']]

        vars_any = [p in os.environ for p in [
                    'OS_TENANT_NAME', 'OS_PROJECT_NAME']]

        self.capture_undercloud_yamls()

        if not (all(vars_all) and any(vars_any)):
            self.soslog.warning("Not all environment variables set. Source "
                                "the environment file for the user intended "
                                "to connect to the OpenStack environment.")
        else:
            # capture all the possible stack uuids
            get_stacks = "openstack stack list"
            stacks = self.collect_cmd_output(get_stacks)['output']
            stack_ids = re.findall(r'(\|\s(((\w+-){4})\w+)\s\|)', stacks)
            # get status of overcloud stack and resources
            for _sid in stack_ids:
                sid = _sid[1]
                self.add_cmd_output([
                    f"openstack stack show {sid}",
                    f"openstack stack resource list -n 10 {sid}"
                ])

                # get details on failed deployments
                cmd = f"openstack stack resource list -f value -n 5 {sid}"
                deployments = self.exec_cmd(cmd)
                for deployment in deployments['output'].splitlines():
                    if 'FAILED' in deployment:
                        check = [
                            "OS::Heat::StructuredDeployment",
                            "OS::Heat::SoftwareDeployment"
                        ]
                        if not any(x in deployment for x in check):
                            continue
                        deploy = deployment.split()[1]
                        cmd = ("openstack software deployment "
                               f"show --long {deployment}")
                        fname = f"failed-deployment-{deploy}.log"
                        self.add_cmd_output(cmd, suggest_filename=fname)

            self.add_cmd_output("openstack object save "
                                "tripleo-ui-logs tripleo-ui.logs --file -")

    def capture_undercloud_yamls(self):
        """ capture yaml files to define overrides """
        uc_config = configparser.ConfigParser()
        try:
            uc_config.read(UNDERCLOUD_CONF_PATH)
            override_opts = ['hieradata_override', 'net_config_override']
            for opt in override_opts:
                path = uc_config.get('DEFAULT', opt)
                if path:
                    if not os.path.isabs(path):
                        path = self.path_join('/home/stack', path)
                    self.add_copy_spec(path)
        except Exception:  # pylint: disable=broad-except
            pass

    def postproc(self):
        # do_file_sub is case insensitive, so protected_keys can be lowercase
        # only
        protected_keys = [
            "os_password",
            "undercloud_admin_password",
            "undercloud_ceilometer_metering_secret",
            "undercloud_ceilometer_password",
            "undercloud_ceilometer_snmpd_password",
            "undercloud_db_password",
            "undercloud_glance_password",
            "undercloud_heat_password",
            "undercloud_heat_stack_domain_admin_password",
            "undercloud_horizon_secret_key",
            "undercloud_ironic_password",
            "undercloud_neutron_password",
            "undercloud_nova_password",
            "undercloud_rabbit_password",
            "undercloud_swift_password",
            "undercloud_tuskar_password",
        ]
        regexp = fr"(({'|'.join(protected_keys)})=)(.*)"
        self.do_file_sub("/home/stack/.instack/install-undercloud.log",
                         regexp, r"\1*********")
        self.do_file_sub(UNDERCLOUD_CONF_PATH, regexp, r"\1*********")

        protected_json_keys = ["pm_password", "ssh-key", "password"]
        json_regexp = fr'("({"|".join(protected_json_keys)})": )(".*?")'
        self.do_file_sub("/home/stack/instackenv.json", json_regexp,
                         r"\1*********")
        self.do_file_sub('/home/stack/.tripleo/history',
                         r'(password=)\w+',
                         r'\1*********')


class RedHatRDOManager(OpenStackInstack, RedHatPlugin):

    packages = ('openstack-selinux',)

# vim: set et ts=4 sw=4 :
