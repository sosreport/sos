# Copyright 2023 Red Hat, Inc. Pablo Acevedo <pacevedo@redhat.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt
import re


class Microshift(Plugin, RedHatPlugin):
    """This is the plugin for MicroShift 4.X. Even though it shares some of
    the OpenShift components, its IoT/Edge target makes the product nimble and
    light, thus requiring different a approach when operating it.

    When enabled, this plugin will collect cluster information (such as
    systemd service logs, configuration, versions, etc.)and also inspect API
    resources in certain namespaces. The namespaces to scan are kube.* and
    openshift.*. Other namespaces may be collected by making use of the
    ``only-namespaces`` or ``add-namespaces`` options.
    """

    short_desc = 'Microshift'
    plugin_name = 'microshift'
    plugin_timeout = 900
    packages = ('microshift', 'microshift-selinux', 'microshift-networking',)
    services = (plugin_name, 'microshift-etcd.scope',)
    profiles = (plugin_name,)
    localhost_kubeconfig = '/var/lib/microshift/resources/kubeadmin/kubeconfig'

    option_list = [
        PluginOpt('kubeconfig', default=localhost_kubeconfig, val_type=str,
                  desc='Path to a locally available kubeconfig file'),
        PluginOpt('only-namespaces', default='', val_type=str,
                  desc='colon-delimited list of namespaces to collect from'),
        PluginOpt('add-namespaces', default='', val_type=str,
                  desc=('colon-delimited list of namespaces to add to the '
                        'default collection list'))
    ]

    def _setup_namespace_regexes(self):
        """Combine a set of regexes for collection with any namespaces passed
        to sos via the -k openshift.add-namespaces option. Note that this does
        allow for end users to specify namespace regexes of their own.
        """
        if self.get_option('only-namespaces'):
            return [n for n in self.get_option('only-namespaces').split(':')]

        collect_regexes = [
            r'^openshift\-.+$',
            r'^kube\-.+$'
        ]

        if self.get_option('add-namespaces'):
            for nsp in self.get_option('add-namespaces').split(':'):
                collect_regexes.append(r'^%s$' % nsp)

        return collect_regexes

    def _reduce_namespace_list(self, nsps):
        """Reduce the namespace listing returned to just the ones we want to
        collect from. By default, as requested by OCP support personnel, this
        must include all 'openshift' prefixed namespaces

            :param nsps list:            Namespace names from oc output
        """

        def _match_namespace(namespace):
            """Match a particular namespace for inclusion (or not) in the
            collection phases

                :param namespace str:   The name of a namespace
            """

            for regex in self.collect_regexes:
                if re.match(regex, namespace):
                    return True
            return False

        self.collect_regexes = self._setup_namespace_regexes()

        return list(set([n for n in nsps if _match_namespace(n)]))

    def _get_namespaces(self):
        res = self.exec_cmd(
            'oc get namespaces'
            ' -o custom-columns=NAME:.metadata.name'
            ' --no-headers'
            ' --kubeconfig=%s' % self.get_option('kubeconfig'))
        if res['status'] == 0:
            return self._reduce_namespace_list(res['output'].split('\n'))
        return []

    def _get_cluster_resources(self):
        """Get cluster-level (non-namespaced) resources to collect
        """
        global_resources = [
            'apiservices',
            'certificatesigningrequests',
            'clusterrolebindings',
            'clusterroles',
            'componentstatuses',
            'csidrivers',
            'csinodes',
            'customresourcedefinitions',
            'flowschemas',
            'ingressclasses',
            'logicalvolumes',
            'mutatingwebhookconfigurations',
            'nodes',
            'persistentvolumes',
            'priorityclasses',
            'prioritylevelconfigurations',
            'rangeallocations',
            'runtimeclasses',
            'securitycontextconstraints',
            'selfsubjectaccessreviews',
            'selfsubjectrulesreviews',
            'storageclasses',
            'subjectaccessreviews',
            'tokenreviews',
            'validatingwebhookconfigurations',
            'volumeattachments'
        ]

        _filtered_resources = []

        for resource in global_resources:
            res = self.exec_cmd(
                "oc get --kubeconfig %s %s" % (
                    self.get_option('kubeconfig'), resource),
                timeout=Microshift.plugin_timeout)
            if res['status'] == 0:
                _filtered_resources.append(resource)
        return _filtered_resources

    def setup(self):
        """The setup() phase of this plugin will first gather system
        information and then iterate through all default namespaces, and/or
        those specified via the `add-namespaces` and `only-namespaces` plugin
        options. Both of these options accept shell-style regexes.

        Output format for this function is based on `oc adm inspect` command,
        which is used to retrieve all API resources from the cluster.
        """

        self.add_copy_spec('/etc/microshift')

        if self.path_exists('/var/lib/microshift-backups'):
            self.add_copy_spec(['/var/lib/microshift-backups/*/version',
                                '/var/lib/microshift-backups/*.json'])
        self.add_copy_spec(['/var/log/kube-apiserver/*.log'])

        self.add_cmd_output([
            'microshift version',
            'microshift show-config -m effective'
        ])

        _cluster_resources_to_collect = ",".join(
            self._get_cluster_resources())
        _namespaces_to_collect = " ".join(
            ['ns/%s' % n for n in self._get_namespaces()])

        if self.is_service_running(Microshift.plugin_name):
            _subdir = self.get_cmd_output_path(make=False)
            _kubeconfig = self.get_option('kubeconfig')
            self.add_cmd_output(
                'oc adm inspect --kubeconfig %s --dest-dir %s %s' % (
                    _kubeconfig, _subdir, _cluster_resources_to_collect),
                suggest_filename='inspect_cluster_resources.log',
                timeout=Microshift.plugin_timeout)
            self.add_cmd_output(
                'oc adm inspect --kubeconfig %s --dest-dir %s %s' % (
                    _kubeconfig, _subdir, _namespaces_to_collect),
                suggest_filename='inspect_namespaces.log',
                timeout=Microshift.plugin_timeout)
