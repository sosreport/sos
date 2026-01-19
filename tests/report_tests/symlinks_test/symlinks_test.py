# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from avocado.utils import process
from sos_tests import StageTwoReportTest


class BrokenLink(StageTwoReportTest):  # Test for bz1640141
    """This test creates broken link and checks warnings

    :avocado: tags=stagetwo
    """

    install_plugins = ['symlinks']

    sos_cmd = '-vvv -o symlinks'

    def pre_sos_setup(self):
        process.run('mkdir -p /var/lib/symlink')
        process.run('ln -s \
                /etc/symlink/symlink.ini-missing /var/lib/symlink/symlink.ini')

    def test_broken_link(self):
        self.assertSosLogContains('Could not open conf file')
        self.assertSosLogContains('not collected, substitution skipped')
        self.assertFileCollected('/var/lib/symlink/plugin.ini')

    def post_sos_tear_down(self):
        process.run('rm -rf /var/lib/symlink')


class RelativeLink(StageTwoReportTest):  # Test for bz717962
    """This test creates relative symlink and checks its collection

    :avocado: tags=stagetwo
    """

    install_plugins = ['symlinks']

    sos_cmd = '-vvv -o symlinks'

    files = [('symlink.conf', '/etc/symlink/symlink.conf')]

    def pre_sos_setup(self):
        process.run('mkdir -p /etc/relative')
        process.run('rm -f /etc/relative/symlink')
        process.run('ln -s ../symlink/symlink.conf /etc/relative/symlink')

    def test_relative_link(self):
        self.assertFileCollected('/etc/relative/symlink')

    def post_test_tear_down(self):
        process.run('rm -rf /etc/relative')


class AbsoluteLink(StageTwoReportTest):  # Test for bz717962
    """This test creates absolute symlink and checks its collection

    :avocado: tags=stagetwo
    """

    install_plugins = ['symlinks']

    sos_cmd = '-vvv -o symlinks'

    files = [('symlink.conf', '/etc/symlink/symlink.conf')]

    def pre_sos_setup(self):
        process.run('mkdir -p /etc/absolute')
        process.run('rm -f /etc/absolute/symlink')
        process.run('ln -s /etc/symlink/symlink.conf /etc/absolute/symlink')

    def test_absolute_link(self):
        self.assertFileCollected('/etc/absolute/symlink')

    def post_test_tear_down(self):
        process.run('rm -rf /etc/absolute')


class RecursiveLink(StageTwoReportTest):
    """This test creates recursive symlink and checks its collection

    :avocado: tags=stagetwo
    """

    install_plugins = ['symlinks']

    sos_cmd = '-vvv -o symlinks'

    files = [('symlink.conf', '/etc/symlink/symlink.conf')]

    def pre_sos_setup(self):
        process.run('mkdir -p /etc/recursive')
        process.run('ln -s symlink.conf /etc/recursive/symlink.conf')

    def test_recursive_link(self):
        self.assertFileCollected('/etc/recursive/symlink.conf')
