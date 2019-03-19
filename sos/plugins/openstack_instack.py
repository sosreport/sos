# Copyright (C) 2015 Red Hat, Inc., Lee Yarwood <lyarwood@redhat.com>
# Copyright (C) 2017 Red Hat, Inc., Martin Schuppert <mschuppert@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin
import os
import re


NON_CONTAINERIZED_DEPLOY = [
        '/home/stack/.instack/install-undercloud.log',
        '/home/stack/instackenv.json',
        '/home/stack/undercloud.conf'
]
CONTAINERIZED_DEPLOY = [
        '/var/log/heat-launcher/',
        '/home/stack/install-undercloud.log',
        '/home/stack/undercloud-install-*.tar.bzip2'
]


class OpenStackInstack(Plugin):
    """OpenStack Instack
    """
    plugin_name = "openstack_instack"
    profiles = ('openstack', 'openstack_undercloud')

    def setup(self):
        self.add_copy_spec(NON_CONTAINERIZED_DEPLOY + CONTAINERIZED_DEPLOY)
        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

        if self.get_option("all_logs"):
            self.add_copy_spec([
                "/var/log/mistral/",
                "/var/log/containers/mistral/",
                "/var/log/zaqar/",
                "/var/log/containers/zaqar/"
            ])
        else:
            self.add_copy_spec([
                "/var/log/mistral/*.log",
                "/var/log/containers/mistral/*.log",
                "/var/log/zaqar/*.log",
                "/var/log/containers/zaqar/*.log"
            ])

        vars_all = [p in os.environ for p in [
                    'OS_USERNAME', 'OS_PASSWORD']]

        vars_any = [p in os.environ for p in [
                    'OS_TENANT_NAME', 'OS_PROJECT_NAME']]

        if not (all(vars_all) and any(vars_any)):
            self.soslog.warning("Not all environment variables set. Source "
                                "the environment file for the user intended "
                                "to connect to the OpenStack environment.")
        else:
            # capture all the possible stack uuids
            get_stacks = "openstack stack list"
            stacks = self.call_ext_prog(get_stacks)['output']
            stack_ids = re.findall(r'(\s(\w+-\w+)+\s)', stacks)
            # get status of overcloud stack and resources
            for sid in stack_ids:
                self.add_cmd_output([
                    "openstack stack show %s" % sid[0],
                    "openstack stack resource list -n 10 %s" % sid[0]
                ])

                # get details on failed deployments
                cmd = "openstack stack resource list -f value -n 5 %s" % sid[0]
                deployments = self.call_ext_prog(cmd)['output']
                for deployment in deployments.splitlines():
                    if 'FAILED' in deployment:
                        check = [
                            "OS::Heat::StructuredDeployment",
                            "OS::Heat::SoftwareDeployment"
                        ]
                        if not any(x in deployment for x in check):
                            continue
                        deploy = deployment.split()[1]
                        cmd = ("openstack software deployment "
                               "show --long %s" % (deployment))
                        fname = "failed-deployment-%s.log" % deploy
                        self.add_cmd_output(cmd, suggest_filename=fname)

            self.add_cmd_output("openstack object save "
                                "tripleo-ui-logs tripleo-ui.logs --file -")

    def postproc(self):
        protected_keys = [
            "UNDERCLOUD_TUSKAR_PASSWORD", "UNDERCLOUD_ADMIN_PASSWORD",
            "UNDERCLOUD_CEILOMETER_METERING_SECRET",
            "UNDERCLOUD_CEILOMETER_PASSWORD",
            "UNDERCLOUD_CEILOMETER_SNMPD_PASSWORD",
            "UNDERCLOUD_DB_PASSWORD", "UNDERCLOUD_GLANCE_PASSWORD",
            "UNDERCLOUD_HEAT_PASSWORD",
            "UNDERCLOUD_HEAT_STACK_DOMAIN_ADMIN_PASSWORD",
            "UNDERCLOUD_HORIZON_SECRET_KEY", "UNDERCLOUD_IRONIC_PASSWORD",
            "UNDERCLOUD_NEUTRON_PASSWORD", "UNDERCLOUD_NOVA_PASSWORD",
            "UNDERCLOUD_RABBIT_PASSWORD", "UNDERCLOUD_SWIFT_PASSWORD",
            "UNDERCLOUD_TUSKAR_PASSWORD", "OS_PASSWORD",
            "undercloud_db_password", "undercloud_admin_password",
            "undercloud_glance_password", "undercloud_heat_password",
            "undercloud_neutron_password", "undercloud_nova_password",
            "undercloud_ironic_password", "undercloud_tuskar_password",
            "undercloud_ceilometer_password",
            "undercloud_ceilometer_metering_secret",
            "undercloud_ceilometer_snmpd_password",
            "undercloud_swift_password", "undercloud_rabbit_password",
            "undercloud_heat_stack_domain_admin_password"
        ]
        regexp = r"((?m)(%s)=)(.*)" % "|".join(protected_keys)
        self.do_file_sub("/home/stack/.instack/install-undercloud.log",
                         regexp, r"\1*********")
        self.do_file_sub("/home/stack/undercloud.conf", regexp, r"\1*********")

        protected_json_keys = ["pm_password", "ssh-key", "password"]
        json_regexp = r'((?m)"(%s)": )(".*?")' % "|".join(protected_json_keys)
        self.do_file_sub("/home/stack/instackenv.json", json_regexp,
                         r"\1*********")


class RedHatRDOManager(OpenStackInstack, RedHatPlugin):

    packages = ('openstack-selinux',)

    def setup(self):
        super(RedHatRDOManager, self).setup()

# vim: set et ts=4 sw=4 :
