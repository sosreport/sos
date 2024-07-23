# Copyright (c) 2023 Canonical Ltd., Chi Wai Chan <chiwai.chan@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import subprocess
import unittest
from unittest.mock import patch

from sos.collector.exceptions import JujuNotInstalledException
from sos.collector.transports.juju import JujuSSH


class MockCmdLineOpts(object):
    ssh_user = "user_abc"
    sudo_pw = "pw_abc"
    root_password = "root_pw_abc"


class JujuSSHTest(unittest.TestCase):
    def setUp(self):
        self.juju_ssh = JujuSSH(
            commons={
                "cmdlineopts": MockCmdLineOpts,
                "tmpdir": "/tmp/sos-juju/",
                "need_sudo": False,
            },
            address="model_abc:unit_abc",
        )

    @patch("sos.collector.transports.juju.subprocess.check_output")
    def test_check_juju_installed_err(self, mock_subprocess_check_output):
        """Raise error if juju is not installed."""
        mock_subprocess_check_output.side_effect = (
            subprocess.CalledProcessError(returncode="127", cmd="cmd_abc")
        )
        with self.assertRaises(JujuNotInstalledException):
            self.juju_ssh._check_juju_installed()

    @patch("sos.collector.transports.juju.subprocess.check_output")
    # pylint: disable=unused-argument
    def test_check_juju_installed_true(self, mock_subprocess_check_output):
        """Return True if juju is installed."""
        result = self.juju_ssh._check_juju_installed()
        assert result

    @patch("sos.collector.transports.juju.subprocess.check_output")
    def test_chmod(self, mock_subprocess_check_output):
        self.juju_ssh._chmod(fname="file_abc")
        mock_subprocess_check_output.assert_called_with(
            f"{self.juju_ssh.remote_exec} sudo chmod o+r file_abc",
            stderr=subprocess.STDOUT,
            shell=True,
        )

    @patch(
        "sos.collector.transports.juju.JujuSSH._check_juju_installed",
        return_value=True,
    )
    # pylint: disable=unused-argument
    def test_connect(self, mock_result):
        self.juju_ssh.connect(password=None)
        assert self.juju_ssh.connected

    def test_remote_exec(self):
        assert (
            self.juju_ssh.remote_exec == "juju ssh -m model_abc unit_abc"
        )

    @patch(
        "sos.collector.transports.juju.sos_get_command_output",
        return_value={"status": 0},
    )
    @patch("sos.collector.transports.juju.JujuSSH._chmod", return_value=True)
    # pylint: disable=unused-argument
    def test_retrieve_file(self, mock_chmod, mock_sos_get_cmd_output):
        self.juju_ssh._retrieve_file(fname="file_abc", dest="/tmp/sos-juju/")
        mock_sos_get_cmd_output.assert_called_with(
            "juju scp -m model_abc -- -r unit_abc:file_abc /tmp/sos-juju/"
        )


# vim: set et ts=4 sw=4 :
