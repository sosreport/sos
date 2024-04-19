# Copyright Red Hat 2021, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
import tempfile
import os

from sos.collector.transports import RemoteTransport
from sos.utilities import (is_executable, sos_get_command_output,
                           SoSTimeoutError)


class OCTransport(RemoteTransport):
    """
    This transport leverages the execution of commands via a locally
    available and configured ``oc`` binary for OCPv4 environments.

    The location of the oc binary MUST be in the $PATH used by the locally
    loaded SoS policy. Specifically this means that the binary cannot be in the
    running user's home directory, such as ~/.local/bin.

    OCPv4 clusters generally discourage the use of SSH, so this transport may
    be used to remove our use of SSH in favor of the environment provided
    method of connecting to nodes and executing commands via debug pods.

    The debug pod created will be a privileged pod that mounts the host's
    filesystem internally so that sos report collections reflect the host, and
    not the container in which it runs.

    This transport will execute within a temporary 'sos-collect-tmp' project
    created by the OCP cluster profile. The project will be removed at the end
    of execution.

    In the event of failures due to a misbehaving OCP API or oc binary, it is
    recommended to fallback to the control_persist transport by manually
    setting the --transport option.
    """

    name = 'oc'
    project = 'sos-collect-tmp'

    def run_oc(self, cmd, **kwargs):
        """Format and run a command with `oc` in the project defined for our
        execution
        """
        return sos_get_command_output(
            f"oc -n {self.project} {cmd}",
            **kwargs
        )

    @property
    def connected(self):
        up = self.run_oc(
            f"wait --timeout=0s --for=condition=ready pod/{self.pod_name}"
        )
        return up['status'] == 0

    def get_node_pod_config(self):
        """Based on our template for the debug container, add the node-specific
        items so that we can deploy one of these on each node we're collecting
        from
        """
        return {
            "kind": "Pod",
            "apiVersion": "v1",
            "metadata": {
                "name": f"{self.address.split('.')[0]}-sos-collector",
                "namespace": self.project
            },
            "priorityClassName": "system-cluster-critical",
            "spec": {
                "volumes": [
                    {
                        "name": "host",
                        "hostPath": {
                            "path": "/",
                            "type": "Directory"
                        }
                    },
                    {
                        "name": "run",
                        "hostPath": {
                            "path": "/run",
                            "type": "Directory"
                        }
                    },
                    {
                        "name": "varlog",
                        "hostPath": {
                            "path": "/var/log",
                            "type": "Directory"
                        }
                    },
                    {
                        "name": "machine-id",
                        "hostPath": {
                            "path": "/etc/machine-id",
                            "type": "File"
                        }
                    }
                ],
                "containers": [
                    {
                        "name": "sos-collector-tmp",
                        "image": "registry.redhat.io/rhel8/support-tools"
                                if not self.opts.image else self.opts.image,
                        "command": [
                            "/bin/bash"
                        ],
                        "env": [
                            {
                                "name": "HOST",
                                "value": "/host"
                            }
                        ],
                        "resources": {},
                        "volumeMounts": [
                            {
                                "name": "host",
                                "mountPath": "/host"
                            },
                            {
                                "name": "run",
                                "mountPath": "/run"
                            },
                            {
                                "name": "varlog",
                                "mountPath": "/var/log"
                            },
                            {
                                "name": "machine-id",
                                "mountPath": "/etc/machine-id"
                            }
                        ],
                        "securityContext": {
                            "privileged": True,
                            "runAsUser": 0
                        },
                        "stdin": True,
                        "stdinOnce": True,
                        "tty": True
                    }
                ],
                "imagePullPolicy":
                    "Always" if self.opts.force_pull_image else "IfNotPresent",
                "restartPolicy": "Never",
                "nodeName": self.address,
                "hostNetwork": True,
                "hostPID": True,
                "hostIPC": True
            }
        }

    def _connect(self, password):
        # the oc binary must be _locally_ available for this to work
        if not is_executable('oc'):
            return False

        # deploy the debug container we'll exec into
        podconf = self.get_node_pod_config()
        self.pod_name = podconf['metadata']['name']
        fd, self.pod_tmp_conf = tempfile.mkstemp(dir=self.tmpdir)
        with open(fd, 'w') as cfile:
            json.dump(podconf, cfile)
        self.log_debug(f"Starting sos collector container '{self.pod_name}'")
        # this specifically does not need to run with a project definition
        out = sos_get_command_output(
            f"oc create -f {self.pod_tmp_conf}"
        )
        if (out['status'] != 0 or f"pod/{self.pod_name} created" not in
                out['output']):
            self.log_error("Unable to deploy sos collect pod")
            self.log_debug(f"Debug pod deployment failed: {out['output']}")
            return False
        self.log_debug(f"Pod '{self.pod_name}' successfully deployed, waiting "
                       "for pod to enter ready state")

        # wait for the pod to report as running
        try:
            up = self.run_oc(f"wait --for=condition=Ready pod/{self.pod_name} "
                             "--timeout=30s",
                             # timeout is for local safety, not oc
                             timeout=40)
            if not up['status'] == 0:
                self.log_error("Pod not available after 30 seconds")
                return False
        except SoSTimeoutError:
            self.log_error("Timeout while polling for pod readiness")
            return False
        except Exception as err:
            self.log_error(f"Error while waiting for pod to be ready: {err}")
            return False

        return True

    def _format_cmd_for_exec(self, cmd):
        if cmd.startswith('oc'):
            return (f"oc -n {self.project} exec --request-timeout=0 "
                    f"{self.pod_name} -- chroot /host {cmd}")
        return super(OCTransport, self)._format_cmd_for_exec(cmd)

    def run_command(self, cmd, timeout=180, need_root=False, env=None,
                    use_shell=False):
        # debug pod setup is slow, extend all timeouts to account for this
        if timeout:
            timeout += 10

        # since we always execute within a bash shell, force disable use_shell
        # to avoid double-quoting
        return super(OCTransport, self).run_command(cmd, timeout, need_root,
                                                    env, use_shell=False)

    def _disconnect(self):
        if os.path.exists(self.pod_tmp_conf):
            os.unlink(self.pod_tmp_conf)
        removed = self.run_oc(f"delete pod {self.pod_name}")
        if "deleted" not in removed['output']:
            self.log_debug(f"Calling delete on pod '{self.pod_name}' failed: "
                           f"{removed}")
            return False
        return True

    @property
    def remote_exec(self):
        return (f"oc -n {self.project} exec --request-timeout=0 "
                f"{self.pod_name} -- /bin/bash -c")

    def _retrieve_file(self, fname, dest):
        # check if --retries flag is available for given version of oc
        result = self.run_oc("cp --retries", stderr=True)
        flags = '' if "unknown flag" in result["output"] else '--retries=5'
        cmd = self.run_oc(f"cp {flags} {self.pod_name}:{fname} {dest}")
        return cmd['status'] == 0
