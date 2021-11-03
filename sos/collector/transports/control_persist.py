# Copyright Red Hat 2021, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


import os
import pexpect
import subprocess

from sos.collector.transports import RemoteTransport
from sos.collector.exceptions import (InvalidPasswordException,
                                      TimeoutPasswordAuthException,
                                      PasswordRequestException,
                                      AuthPermissionDeniedException,
                                      ConnectionException,
                                      ConnectionTimeoutException,
                                      ControlSocketMissingException,
                                      ControlPersistUnsupportedException)
from sos.utilities import sos_get_command_output


class SSHControlPersist(RemoteTransport):
    """
    A transport for collect that leverages OpenSSH's ControlPersist
    functionality which uses control sockets to transparently keep a connection
    open to the remote host without needing to rebuild the SSH connection for
    each and every command executed on the node.

    This transport will by default assume the use of SSH keys, meaning keys
    have already been distributed to target nodes. If this is not the case,
    users will need to provide a password using the --password or
    --password-per-node option, depending on if the password to connect to all
    nodes is the same or not. Note that these options prevent the use of the
    --batch option, as they require user input.
    """

    name = 'control_persist'

    def _check_for_control_persist(self):
        """Checks to see if the local system supported SSH ControlPersist.

        ControlPersist allows OpenSSH to keep a single open connection to a
        remote host rather than building a new session each time. This is the
        same feature that Ansible uses in place of paramiko, which we have a
        need to drop in sos-collector.

        This check relies on feedback from the ssh binary. The command being
        run should always generate stderr output, but depending on what that
        output reads we can determine if ControlPersist is supported or not.

        For our purposes, a host that does not support ControlPersist is not
        able to run sos-collector.

        Returns
            True if ControlPersist is supported, else raise Exception.
        """
        ssh_cmd = ['ssh', '-o', 'ControlPersist']
        cmd = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        out, err = cmd.communicate()
        err = err.decode('utf-8')
        if 'Bad configuration option' in err or 'Usage:' in err:
            raise ControlPersistUnsupportedException
        return True

    def _connect(self, password=''):
        """
        Using ControlPersist, create the initial connection to the node.

        This will generate an OpenSSH ControlPersist socket within the tmp
        directory created or specified for sos-collector to use.

        At most, we will wait 30 seconds for a connection. This involves a 15
        second wait for the initial connection attempt, and a subsequent 15
        second wait for a response when we supply a password.

        Since we connect to nodes in parallel (using the --threads value), this
        means that the time between 'Connecting to nodes...' and 'Beginning
        collection of sosreports' that users see can be up to an amount of time
        equal to 30*(num_nodes/threads) seconds.

        Returns
            True if session is successfully opened, else raise Exception
        """
        try:
            self._check_for_control_persist()
        except ControlPersistUnsupportedException:
            self.log_error("OpenSSH ControlPersist is not locally supported. "
                           "Please update your OpenSSH installation.")
            raise
        self.log_info('Opening SSH session to create control socket')
        self.control_path = ("%s/.sos-collector-%s" % (self.tmpdir,
                                                       self.address))
        self.ssh_cmd = ''
        connected = False
        ssh_key = ''
        ssh_port = ''
        if self.opts.ssh_port != 22:
            ssh_port = "-p%s " % self.opts.ssh_port
        if self.opts.ssh_key:
            ssh_key = "-i%s" % self.opts.ssh_key

        cmd = ("ssh %s %s -oControlPersist=600 -oControlMaster=auto "
               "-oStrictHostKeyChecking=no -oControlPath=%s %s@%s "
               "\"echo Connected\"" % (ssh_key,
                                       ssh_port,
                                       self.control_path,
                                       self.opts.ssh_user,
                                       self.address))
        res = pexpect.spawn(cmd, encoding='utf-8')

        connect_expects = [
            u'Connected',
            u'password:',
            u'.*Permission denied.*',
            u'.* port .*: No route to host',
            u'.*Could not resolve hostname.*',
            pexpect.TIMEOUT
        ]

        index = res.expect(connect_expects, timeout=15)

        if index == 0:
            connected = True
        elif index == 1:
            if password:
                pass_expects = [
                    u'Connected',
                    u'Permission denied, please try again.',
                    pexpect.TIMEOUT
                ]
                res.sendline(password)
                pass_index = res.expect(pass_expects, timeout=15)
                if pass_index == 0:
                    connected = True
                elif pass_index == 1:
                    # Note that we do not get an exitstatus here, so matching
                    # this line means an invalid password will be reported for
                    # both invalid passwords and invalid user names
                    raise InvalidPasswordException
                elif pass_index == 2:
                    raise TimeoutPasswordAuthException
            else:
                raise PasswordRequestException
        elif index == 2:
            raise AuthPermissionDeniedException
        elif index == 3:
            raise ConnectionException(self.address, self.opts.ssh_port)
        elif index == 4:
            raise ConnectionException(self.address)
        elif index == 5:
            raise ConnectionTimeoutException
        else:
            raise Exception("Unknown error, client returned %s" % res.before)
        if connected:
            if not os.path.exists(self.control_path):
                raise ControlSocketMissingException
            self.log_debug("Successfully created control socket at %s"
                           % self.control_path)
            return True
        return False

    def _disconnect(self):
        if os.path.exists(self.control_path):
            try:
                os.remove(self.control_path)
                return True
            except Exception as err:
                self.log_debug("Could not disconnect properly: %s" % err)
                return False
        self.log_debug("Control socket not present when attempting to "
                       "terminate session")

    @property
    def connected(self):
        """Check if the SSH control socket exists

        The control socket is automatically removed by the SSH daemon in the
        event that the last connection to the node was greater than the timeout
        set by the ControlPersist option. This can happen for us if we are
        collecting from a large number of nodes, and the timeout expires before
        we start collection.
        """
        return os.path.exists(self.control_path)

    @property
    def remote_exec(self):
        if not self.ssh_cmd:
            self.ssh_cmd = "ssh -oControlPath=%s %s@%s" % (
                self.control_path, self.opts.ssh_user, self.address
            )
        return self.ssh_cmd

    def _retrieve_file(self, fname, dest):
        cmd = "/usr/bin/scp -oControlPath=%s %s@%s:%s %s" % (
            self.control_path, self.opts.ssh_user, self.address, fname, dest
        )
        res = sos_get_command_output(cmd)
        return res['status'] == 0

# vim: set et ts=4 sw=4 :
