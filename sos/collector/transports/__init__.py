# Copyright Red Hat 2021, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import inspect
import logging
import re
from shlex import quote

import pexpect

from sos.collector.exceptions import (ConnectionException,
                                      CommandTimeoutException)
from sos.utilities import bold


class RemoteTransport():
    """The base class used for defining supported remote transports to connect
    to remote nodes in conjunction with `sos collect`.

    This abstraction is used to manage the backend connections to nodes so that
    SoSNode() objects can be leveraged generically to connect to nodes, inspect
    those nodes, and run commands on them.
    """

    name = 'undefined'
    default_user = None

    def __init__(self, address, commons):
        self.address = address
        self.opts = commons['cmdlineopts']
        self.tmpdir = commons['tmpdir']
        self.need_sudo = commons['need_sudo']
        self._hostname = None
        self.soslog = logging.getLogger('sos')
        self.ui_log = logging.getLogger('sos_ui')

    def _sanitize_log_msg(self, msg):
        """Attempts to obfuscate sensitive information in log messages such as
        passwords"""
        reg = r'(?P<var>(pass|key|secret|PASS|KEY|SECRET).*?=)(?P<value>.*?\s)'
        return re.sub(reg, r'\g<var>****** ', msg)

    def log_info(self, msg):
        """Used to print and log info messages"""
        caller = inspect.stack()[1][3]
        lmsg = f'[{self.hostname}:{caller}] {msg}'
        self.soslog.info(lmsg)

    def log_error(self, msg):
        """Used to print and log error messages"""
        caller = inspect.stack()[1][3]
        lmsg = f'[{self.hostname}:{caller}] {msg}'
        self.soslog.error(lmsg)

    def log_debug(self, msg):
        """Used to print and log debug messages"""
        msg = self._sanitize_log_msg(msg)
        caller = inspect.stack()[1][3]
        msg = f'[{self.hostname}:{caller}] {msg}'
        self.soslog.debug(msg)

    @property
    def hostname(self):
        if self._hostname and 'localhost' not in self._hostname:
            return self._hostname
        return self.address

    @property
    def connected(self):
        """Is the transport __currently__ connected to the node, or otherwise
        capable of seamlessly running a command or similar on the node?
        """
        return False

    @property
    def remote_exec(self):
        """This is the command string needed to leverage the remote transport
        when executing commands. For example, for an SSH transport this would
        be the `ssh <options>` string prepended to any command so that the
        command is executed by the ssh binary.

        This is also referenced by the `remote_exec` parameter for policies
        when loading a policy for a remote node
        """
        return None

    @classmethod
    def display_help(cls, section):
        if cls is RemoteTransport:
            return cls.display_self_help(section)
        section.set_title(f"{cls.name.title().replace('_', ' ')} "
                          "Transport Detailed Help")
        if cls.__doc__ and cls.__doc__ is not RemoteTransport.__doc__:
            section.add_text(cls.__doc__)
        else:
            section.add_text(
                'Detailed information not available for this transport'
            )
        return None

    @classmethod
    def display_self_help(cls, section):
        section.set_title('SoS Remote Transport Help')
        section.add_text(
            "\nTransports define how SoS connects to nodes and executes "
            f"commands on them for the purposes of an {bold('sos collect')} "
            "run. Generally, this means transports define how commands are "
            "wrapped locally so that they are executed on the remote node(s) "
            "instead."
        )

        section.add_text(
            "Transports are generally selected by the cluster profile loaded "
            "for a given execution, however users may explicitly set one "
            f"using '{bold('--transport=$transport_name')}'. Note that not all"
            " transports will function for all cluster/node types."
        )

        section.add_text(
            'By default, OpenSSH Control Persist is attempted. Additional '
            'information for each supported transport is available in the '
            'following help sections:\n'
        )

        from sos.collector.sosnode import TRANSPORTS
        for transport in TRANSPORTS:
            _sec = bold(f"collect.transports.{transport}")
            _desc = f"The '{transport.lower()}' transport"
            section.add_text(
                f"{' ':>8}{_sec:<45}{_desc:<30}",
                newline=False
            )

    def connect(self, password):
        """Perform the connection steps in order to ensure that we are able to
        connect to the node for all future operations. Note that this should
        not provide an interactive shell at this time.
        """
        if self._connect(password):
            if not self._hostname:
                self._get_hostname()
            return True
        return False

    def _connect(self, password):
        """Actually perform the connection requirements. Should be overridden
        by specific transports that subclass RemoteTransport
        """
        raise NotImplementedError(
            f"Transport {self.name} does not define connect")

    def reconnect(self, password):
        """Attempts to reconnect to the node using the standard connect()
        but does not do so indefinitely. This imposes a strict number of retry
        attempts before failing out
        """
        attempts = 1
        last_err = 'unknown'
        while attempts < 5:
            self.log_debug(f"Attempting reconnect (#{attempts}) to node")
            try:
                if self.connect(password):
                    return True
            except Exception as err:
                self.log_debug(f"Attempt #{attempts} exception: {err}")
                last_err = err
            attempts += 1
        self.log_error("Unable to reconnect to node after 5 attempts, "
                       "aborting.")
        raise ConnectionException(f"last exception from transport: {last_err}")

    def disconnect(self):
        """Perform whatever steps are necessary, if any, to terminate any
        connection to the node
        """
        try:
            if self._disconnect():
                self.log_debug("Successfully disconnected from node")
            else:
                self.log_error("Unable to successfully disconnect, see log for"
                               " more details")
        except Exception as err:
            self.log_error(f"Failed to disconnect: {err}")

    def _disconnect(self):
        raise NotImplementedError(
            f"Transport {self.name} does not define disconnect")

    @property
    def _need_shell(self):
        """
        Transports may override this to control when/if commands executed over
        the transport needs to utilize a shell on the remote host.
        """
        return False

    def run_command(self, cmd, timeout=180, need_root=False, env=None,
                    use_shell='auto'):
        """Run a command on the node, returning its output and exit code.
        This should return the exit code of the command being executed, not the
        exit code of whatever mechanism the transport uses to execute that
        command

        :param cmd:         The command to run
        :type cmd:          ``str``

        :param timeout:     The maximum time in seconds to allow the cmd to run
        :type timeout:      ``int```

        :param need_root:   Does ``cmd`` require root privileges?
        :type need_root:   ``bool``

        :param env:         Specify env vars to be passed to the ``cmd``
        :type env:          ``dict``

        :param use_shell:     Does ``cmd`` require execution within a shell?
        :type use_shell:      ``bool`` or ``auto`` for transport-determined

        :returns:           Output of ``cmd`` and the exit code
        :rtype:             ``dict`` with keys ``output`` and ``status``
        """
        self.log_debug(f'Running command {cmd}')
        if (use_shell is True or
                (self._need_shell if use_shell == 'auto' else False)):
            cmd = f"/bin/bash -c {quote(cmd)}"
            self.log_debug(f"Shell requested, command is now {cmd}")
        # currently we only use/support the use of pexpect for handling the
        # execution of these commands, as opposed to directly invoking
        # subprocess.Popen() in conjunction with tools like sshpass.
        # If that changes in the future, we'll add decision making logic here
        # to route to the appropriate handler, but for now we just go straight
        # to using pexpect
        return self._run_command_with_pexpect(cmd, timeout, need_root, env)

    def _format_cmd_for_exec(self, cmd):
        """Format the command in the way needed for the remote transport to
        successfully execute it as one would when manually executing it

        :param cmd:     The command being executed, as formatted by SoSNode
        :type cmd:      ``str``


        :returns:       The command further formatted as needed by this
                        transport
        :rtype:         ``str``
        """
        cmd = f"{self.remote_exec} {quote(cmd)}"
        cmd = cmd.lstrip()
        return cmd

    def _run_command_with_pexpect(self, cmd, timeout, need_root, env):
        """Execute the command using pexpect, which allows us to more easily
        handle prompts and timeouts compared to directly leveraging the
        subprocess.Popen() method.

        :param cmd:     The command to execute. This will be automatically
                        formatted to use the transport.
        :type cmd:      ``str``

        :param timeout: The maximum time in seconds to run ``cmd``
        :type timeout:  ``int``

        :param need_root:   Does ``cmd`` need to run as root or with sudo?
        :type need_root:    ``bool``

        :param env:     Any env vars that ``cmd`` should be run with
        :type env:      ``dict``
        """
        cmd = self._format_cmd_for_exec(cmd)

        # if for any reason env is empty, set it to None as otherwise
        # pexpect interprets this to mean "run this command with no env vars of
        # any kind"
        if not env:
            env = None

        try:
            result = pexpect.spawn(cmd, encoding='utf-8', env=env)
        except pexpect.exceptions.ExceptionPexpect as err:
            self.log_debug(err.value)
            return {'status': 127, 'output': ''}

        _expects = [pexpect.EOF, pexpect.TIMEOUT]
        if need_root and self.opts.ssh_user != 'root':
            _expects.extend([
                '\\[sudo\\] password for .*:',
                'Password:'
            ])

        index = result.expect(_expects, timeout=timeout)

        if index in [2, 3]:
            self._send_pexpect_password(index, result)
            index = result.expect(_expects, timeout=timeout)

        if index == 0:
            out = result.before
            result.close()
            return {'status': result.exitstatus, 'output': out}
        if index == 1:
            raise CommandTimeoutException(cmd)
        # if we somehow manage to flow to this point, use this bogus exit code
        # as a signal to debugging efforts that whatever went sideways did so
        # as part of the above block
        self.log_debug(f"Unexpected index {index} from pexpect: {result}")
        return {'status': 999, 'output': ''}

    def _send_pexpect_password(self, index, result):
        """Handle password prompts for sudo and su usage for non-root SSH users

        :param index:       The index pexpect.spawn returned to match against
                            either a sudo or su prompt
        :type index:        ``int``

        :param result:      The spawn running the command
        :type result:       ``pexpect.spawn``
        """
        if index == 2:
            if not self.opts.sudo_pw and not self.opts.nopasswd_sudo:
                msg = ("Unable to run command: sudo password "
                       "required but not provided")
                self.log_error(msg)
                raise Exception(msg)
            result.sendline(self.opts.sudo_pw)
        elif index == 3:
            if not self.opts.root_password:
                msg = "Unable to run command as root: no root password given"
                self.log_error(msg)
                raise Exception(msg)
            result.sendline(self.opts.root_password)

    def _get_hostname(self):
        """Determine the hostname of the node and set that for future reference
        and logging

        :returns:   The hostname of the system, per the `hostname` command
        :rtype:     ``str``
        """
        _out = self.run_command('hostname')
        if _out['status'] == 0:
            self._hostname = _out['output'].strip()

        if not self._hostname:
            self._hostname = self.address
        self.log_info(f"Hostname set to {self._hostname}")
        return self._hostname

    def copy_file_to_remote(self, fname, dest):
        """Copy a local file, fname, to dest on the remote node

        :param fname:   The name of the file to copy
        :type fname:    ``str``

        :param dest:    Where to save the file to remotely
        :type dest:     ``str``

        :returns:   True if file was successfully copied to remote, or False
        :rtype:     ``bool``
        """
        attempts = 0
        try:
            while attempts < 3:
                attempts += 1
                ret = self._copy_file_to_remote(fname, dest)
                if ret:
                    return True
                self.log_info(f"File copy attempt {attempts} failed")
            self.log_info("File copy failed after 3 attempts")
            return False
        except Exception as err:
            self.log_error("Exception encountered during config copy attempt "
                           f"{attempts} for {fname}: {err}")
            raise err

    def _copy_file_to_remote(self, fname, dest):
        raise NotImplementedError(
            f"Transport {self.name} does not support file copying")

    def retrieve_file(self, fname, dest):
        """Copy a remote file, fname, to dest on the local node

        :param fname:   The name of the file to retrieve
        :type fname:    ``str``

        :param dest:    Where to save the file to locally
        :type dest:     ``str``

        :returns:   True if file was successfully copied from remote, or False
        :rtype:     ``bool``
        """
        attempts = 0
        try:
            while attempts < 5:
                attempts += 1
                ret = self._retrieve_file(fname, dest)
                if ret:
                    return True
                self.log_info(f"File retrieval attempt {attempts} failed")
            self.log_info("File retrieval failed after 5 attempts")
            return False
        except Exception as err:
            self.log_error("Exception encountered during retrieval attempt "
                           f"{attempts} for {fname}: {err}")
            raise err

    def _retrieve_file(self, fname, dest):
        raise NotImplementedError(
            f"Transport {self.name} does not support file copying")

    def read_file(self, fname):
        """Read the given file fname and return its contents

        :param fname:   The name of the file to read
        :type fname:    ``str``

        :returns:   The content of the file
        :rtype:     ``str``
        """
        self.log_debug(f"Reading file {fname}")
        return self._read_file(fname)

    def _read_file(self, fname):
        res = self.run_command(f"cat {fname}", timeout=10)
        if res['status'] == 0:
            return res['output']
        if 'No such file' in res['output']:
            self.log_debug(f"File {fname} does not exist on node")
        else:
            self.log_error(f"Error reading {fname}: "
                           f"{res['output'].split(':')[1:]}")
        return ''

# vim: set et ts=4 sw=4 :
