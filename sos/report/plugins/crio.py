# Copyright (C) 2018 Red Hat, Inc. Daniel Walsh <dwalsh@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, UbuntuPlugin,
                                SoSPredicate, PluginOpt)


class CRIO(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'CRI-O containers'
    plugin_name = 'crio'
    profiles = ('container',)
    packages = ('cri-o', 'cri-tools')
    services = ('crio',)

    option_list = [
        PluginOpt('all', default=False,
                  desc='collect for all containers, even terminated ones'),
        PluginOpt('logs', default=False,
                  desc='collect stdout/stderr logs for containers')
    ]

    def setup(self):
        self.add_copy_spec([
            "/etc/containers",
            "/etc/crictl.yaml",
            "/etc/crio/crio.conf",
            "/etc/crio/seccomp.json",
            "/etc/crio/crio.conf.d/",
            "/etc/systemd/system/cri-o.service",
            "/etc/sysconfig/crio-*"
        ])

        self.add_env_var([
            'HTTP_PROXY',
            'HTTPS_PROXY',
            'NO_PROXY',
            'ALL_PROXY'
        ])

        self.add_cmd_output([
            "ls -alhR /etc/cni",
            "crio config"
        ])

        # base cri-o installation does not require cri-tools, which is what
        # supplies the crictl utility
        self.set_cmd_predicate(SoSPredicate(self, packages=['cri-tools']))

        subcmds = [
            'info',
            'images',
            'pods',
            'ps',
            'ps -a',
            'ps -v',
            'stats',
            'version',
        ]

        self.add_cmd_output(["crictl %s" % s for s in subcmds])

        ps_cmd = 'crictl ps --quiet'
        if self.get_option('all'):
            ps_cmd = "%s -a" % ps_cmd

        img_cmd = 'crictl images --quiet'
        pod_cmd = 'crictl pods --quiet'

        containers = self._get_crio_list(ps_cmd)
        images = self._get_crio_list(img_cmd)
        pods = self._get_crio_list(pod_cmd)

        self._get_crio_goroutine_stacks()

        for container in containers:
            self.add_cmd_output("crictl inspect %s" % container,
                                subdir="containers")
            if self.get_option('logs'):
                self.add_cmd_output("crictl logs -t %s" % container,
                                    subdir="containers/logs", priority=100)

        for image in images:
            self.add_cmd_output("crictl inspecti %s" % image, subdir="images")

        for pod in pods:
            self.add_cmd_output("crictl inspectp %s" % pod, subdir="pods")

    def _get_crio_list(self, cmd):
        ret = []
        result = self.exec_cmd(cmd)
        if result['status'] == 0:
            for ent in result['output'].splitlines():
                ret.append(ent)
            # Prevent the socket deprecation warning from being iterated over
            if ret and 'deprecated' in ret[0]:
                ret.pop(0)
        return ret

    def _get_crio_goroutine_stacks(self):
        result = self.exec_cmd("pidof crio")
        if result['status'] != 0:
            return
        pid = result['output'].strip()
        result = self.exec_cmd("kill -USR1 " + pid)
        if result['status'] == 0:
            self.add_copy_spec("/tmp/crio-goroutine-stacks*.log")

# vim: set et ts=4 sw=4 :
