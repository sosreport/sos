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


class OpenStackInstack(Plugin):
    """OpenStack Instack
    """
    plugin_name = "openstack_instack"
    profiles = ('openstack', 'openstack_undercloud')

    def setup(self):
        self.add_copy_spec("/home/stack/.instack/install-undercloud.log")
        self.add_copy_spec("/home/stack/instackenv.json")
        self.add_copy_spec("/home/stack/undercloud.conf")
        if self.get_option("verify"):
            self.add_cmd_output("rpm -V %s" % ' '.join(self.packages))

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec(["/var/log/mistral/",
                                "/var/log/containers/mistral/"],
                               sizelimit=self.limit)
            self.add_copy_spec(["/var/log/zaqar/",
                                "/var/log/containers/zaqar/"],
                               sizelimit=self.limit)
        else:
            self.add_copy_spec(["/var/log/mistral/*.log",
                                "/var/log/containers/mistral/*.log"],
                               sizelimit=self.limit)
            self.add_copy_spec(["/var/log/zaqar/*.log",
                                "/var/log/containers/zaqar/*.log"],
                               sizelimit=self.limit)

        vars_all = [p in os.environ for p in [
                    'OS_USERNAME', 'OS_PASSWORD']]

        vars_any = [p in os.environ for p in [
                    'OS_TENANT_NAME', 'OS_PROJECT_NAME']]

        if not (all(vars_all) and any(vars_any)):
            self.soslog.warning("Not all environment variables set. Source "
                                "the environment file for the user intended "
                                "to connect to the OpenStack environment.")
        else:
            # get status of overcloud stack and resources
            self.add_cmd_output("openstack stack show overcloud")
            self.add_cmd_output(
                "openstack stack resource list -n 10 overcloud",
                timeout=600)

            # get details on failed deployments
            cmd = "openstack stack resource list -f value -n 5 overcloud"
            deployments = self.call_ext_prog(cmd, timeout=600)['output']
            for deployment in deployments.splitlines():
                if 'FAILED' in deployment:
                    check = [
                        "OS::Heat::StructuredDeployment",
                        "OS::Heat::SoftwareDeployment"]
                    if any(x in deployment for x in check):
                        deployment = deployment.split()[1]
                        cmd = "openstack software deployment show " \
                            "--long %s" % (deployment)
                        self.add_cmd_output(
                            cmd,
                            suggest_filename="failed-deployment-" +
                            deployment + ".log",
                            timeout=600)

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

    packages = [
        'instack',
        'instack-undercloud',
        'openstack-tripleo',
        'openstack-tripleo-common',
        'openstack-tripleo-heat-templates',
        'openstack-tripleo-image-elements',
        'openstack-tripleo-puppet-elements',
        'openstack-tripleo-ui',
        'openstack-tripleo-validations',
        'puppet-tripleo',
        'python-tripleoclient'
    ]

    def setup(self):
        super(RedHatRDOManager, self).setup()

# vim: set et ts=4 sw=4 :
