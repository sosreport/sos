# Copyright Red Hat 2022, Trevor Benson <trevor.benson@gmail.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import contextlib
import json
import os
import shutil
from sos.collector.transports import RemoteTransport
from sos.collector.exceptions import (ConnectionException,
                                      SaltStackMasterUnsupportedException)
from sos.utilities import (is_executable,
                           sos_get_command_output)


class SaltStackMaster(RemoteTransport):
    """
    A transport for collect that leverages SaltStack's Master Pub/Sub
    functionality to send commands to minions.

    This transport will by default assume the use cmd.shell module to
    execute commands on the minions.
    """

    name = 'saltstack'

    def _convert_output_json(self, json_output):
        return list(json.loads(json_output).values())[0]

    def run_command(self, cmd, timeout=180, need_root=False, env=None,
                    use_shell=False):
        """
        Run a command on the remote host using SaltStack Master.
        If the output is json, convert it to a string.
        """
        ret = super().run_command(
            cmd, timeout, need_root, env, use_shell)
        with contextlib.suppress(Exception):
            ret['output'] = self._convert_output_json(ret['output'])
        return ret

    def _salt_retrieve_file(self, node, fname, dest):
        """
        Execute cp.push on the remote host using SaltStack Master
        """
        cmd = f"salt {node} cp.push {fname}"
        res = sos_get_command_output(cmd)
        if res['status'] == 0:
            cachedir = f"/var/cache/salt/master/minions/{self.address}/files"
            cachedir_file = os.path.join(cachedir, fname.lstrip('/'))
            shutil.move(cachedir_file, dest)
            return True
        return False

    @property
    def connected(self):
        """Check if the remote host is responding using SaltStack Master."""
        up = self.run_command("echo Connected", timeout=10)
        return up['status'] == 0

    # pylint: disable=unused-argument
    def _check_for_saltstack(self, password=None):
        """Checks to see if the local system supported SaltStack Master.

        This check relies on feedback from the salt binary. The command being
        run should always generate stderr output, but depending on what that
        output reads we can determine if SaltStack Master is supported or not.

        For our purposes, a host that does not support SaltStack Master is not
        able to run sos collect.

        Returns
            True if SaltStack Master is supported, else raise Exception
        """

        cmd = 'salt-run manage.status'
        res = sos_get_command_output(cmd)
        if res['status'] == 0:
            return res['status'] == 0
        raise SaltStackMasterUnsupportedException

    def _connect(self, password=None):
        """Connect to the remote host using SaltStack Master.

        This method will attempt to connect to the remote host using SaltStack
        Master. If the connection fails, an exception will be raised.

        If the connection is successful, the connection will be stored in the
        self._connection attribute.
        """
        if not is_executable('salt'):
            self.log_error("salt command is not executable. ")
            return False

        try:
            self._check_for_saltstack()
        except ConnectionException:
            self.log_error("Transport is not locally supported. ")
            raise
        self.log_info("Transport is locally supported and service running. ")
        cmd = "echo Connected"
        result = self.run_command(cmd, timeout=180)
        if result['status'] == 1:
            raise ConnectionException(self.address)
        return result['status'] == 0

    def _disconnect(self):
        return True

    @property
    def remote_exec(self):
        """The remote execution command to use for this transport."""
        salt_args = "--out json --static --no-color"
        return f"salt {salt_args} {self.address} cmd.shell "

    def _retrieve_file(self, fname, dest):
        """Retrieve a file from the remote host using saltstack

        Parameters
            fname       The path to the file on the remote host
            dest        The path to the destination directory on the master

        Returns
            True if the file was retrieved, else False
        """
        return (
            self._salt_retrieve_file(self.address, fname, dest)
            if self.connected
            else False
        )

# vim: set et ts=4 sw=4 :
