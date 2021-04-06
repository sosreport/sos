# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re


from avocado.utils import process
from sos_tests import StageOneReportTest, SOS_BIN, skipIf, RH_DIST


# These are the header strings in --list-plugins output
DISABLED = 'The following plugins are currently disabled:'
OPTIONS = 'The following options are available for ALL plugins:'


class AllPluginSmokeTest(StageOneReportTest):
    """This test forcibly enables ALL plugins available to the local branch
    and aims to make sure that there are no exceptions generated during the
    execution

    :avocado: tags=stageone
    """

    def pre_sos_setup(self):
        _cmd = '%s report --list-plugins' % SOS_BIN
        out = process.run(_cmd, timeout=300).stdout.decode()
        reg = DISABLED + '(.*?)' + OPTIONS
        self.plugs = []
        for result in re.findall(reg, out, re.S):
            for line in result.splitlines():
                try:
                    self.plugs.append(line.split()[0])
                except Exception:
                    pass

        self.sos_cmd = '-e %s' % ','.join(p for p in self.plugs)

    def test_all_plugins_ran(self):
        for plugin in self.plugs:
            self.assertPluginIncluded(plugin)

    @skipIf(lambda x: x.local_distro not in RH_DIST, "Not distro relevant")
    def test_expected_warnings_displayed(self):
        """We can expect specific plugins to always generate a warning during
        setup if they are enabled on systems that are not configured for those
        plugins.

        Make sure our warnings are displayed
        """
        self.assertOutputContains('Not logged in to OCP API, and no login token provided. Will not collect `oc` commands')
        self.assertOutputContains('Source the environment file for the user intended to connect to the OpenStack environment.')
        self.assertOutputContains('Some or all of the skydive params are not set properly.')
