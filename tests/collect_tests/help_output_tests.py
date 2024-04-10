# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import glob
import os
import re

from avocado.utils import software_manager
from sos_tests import StageOneOutputTest, SOS_REPO_ROOT, skipIf

installer = software_manager
sm = installer.manager.SoftwareManager()

PEXPECT_PRESENT = sm.check_installed('python3-pexpect')


class CollectHelpOutputTest(StageOneOutputTest):
    """Ensure that --help is behaving as expected, based on if the placeholder
    component is being used or not

    Note that this is tagged for both stageone and stagetwo due to the config
    of the GCE images used - pexpect is not normally installed, but we will
    install it as part of the CirrusCI setup for stagetwo. This allows us to
    perform checks for both the real and placeholder components in CI, without
    creating a output tests for stagetwo, which would be silly for tests run on
    contributor workstations

    :avocado: tags=stageone,stagetwo
    """

    sos_cmd = 'collect --help'

    @skipIf(
        PEXPECT_PRESENT,
        "python3-pexpect is installed, placeholder will not be used"
    )
    def test_placeholder_warning_shown(self):
        self.assertOutputContains(
            "WARNING: `collect` is not available with this installation!"
        )

    @skipIf(PEXPECT_PRESENT is False, "python3-pexpect not installed locally")
    def test_help_sections_present(self):
        self.assertOutputNotContains(
            "WARNING: `collect` is not available with this installation!"
        )
        self.assertOutputContains("Global Options:")
        self.assertOutputContains("Report Passthru Options:")
        self.assertOutputContains("Collector Options:")


class CollectOptionsHelpTest(StageOneOutputTest):
    """Ensure that available cluster profiles and their options are printed

    Note that this is tagged for both stageone and stagetwo due to the config
    of the GCE images used - pexpect is not normally installed, but we will
    install it as part of the CirrusCI setup for stagetwo. This allows us to
    perform checks for both the real and placeholder components in CI, without
    creating a output tests for stagetwo, which would be silly for tests run on
    contributor workstations

    :avocado: tags=stageone,stagetwo
    """

    _exception_expected = not PEXPECT_PRESENT
    sos_cmd = 'collect --list-options'

    @skipIf(PEXPECT_PRESENT is False, "python3-pexpect not installed locally")
    def test_cluster_profiles_shown(self):
        _out = re.search("Use the short name with --cluster-type or cluster "
                         r"options \(-c\)(.*?)The following cluster options "
                         "are available:",
                         self.cmd_output.stdout, re.S).group(1).splitlines()
        _profs = {}
        for ln in _out:
            if not ln:
                continue
            ln = [c for c in ln.lstrip().split('  ') if c]
            _profs[ln[0]] = ln[1]

        clusters = []
        # get a list of names of profile pyfiles
        for pyfile in glob.glob(os.path.join(SOS_REPO_ROOT,
                                             'sos/collector/clusters/*.py')):
            pyf = os.path.basename(pyfile)
            if pyf.startswith('__'):
                continue
            clusters.append(pyf.split('.py')[0])

        assert len(_profs.keys()) > 0, "No profiles detected in output"

        # make sure each pyfile is reported for supported cluster types
        # this has the secondary effect of enforcing a stylistic requirement
        # where at least one profile must match the pyfile name
        for clus in clusters:
            assert \
                clus in _profs, \
                f"Cluster '{clus}' not displayed in --list-options"

    @skipIf(PEXPECT_PRESENT is False, "python3-pexpect not installed locally")
    def test_cluster_options_shown(self):
        _opts = re.search(" Cluster                   Option Name     "
                          "Type       Default    Description(.*?)Options "
                          "take the form of cluster.name=value",
                          self.cmd_output.stdout, re.S).group(1).splitlines()

        _opts = [o for o in _opts if o]

        assert _opts, "No option output detected"

    @skipIf(
        PEXPECT_PRESENT,
        "python3-pexpect is installed, placeholder will be unused"
    )
    def test_placeholder_component_used(self):
        self.assertOutputContains(
            "(unavailable) Collect an sos report from multiple nodes"
        )
