# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os

from sos_tests import StageOneOutputTest, SOS_REPO_ROOT

DRIVER = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                      'bash_driver.sh')
INSTALLED_SCRIPT = '/usr/share/bash-completion/completions/sos'
REPO_SCRIPT = os.path.join(SOS_REPO_ROOT, 'completions/bash/sos')


class CompletionHelperTest(StageOneOutputTest):
    """Ensure that the hidden completion subcommand used by the shell
    completion scripts produces the expected output

    :avocado: tags=stageone
    """

    sos_cmd = '_complete bash 2 -- sos report --all-l'

    def test_bash_output_format(self):
        self.assertEqual(self.cmd_output.stdout.splitlines(),
                         ['words 0', '', '', '--all-logs'])


class BashCompletionTest(StageOneOutputTest):
    """Ensure that the bash completion script completes sos command lines as
    expected, using bash-completion if it is installed

    :avocado: tags=stageone
    """

    driver_opts = ''
    lines = {
        'components': 'rep',
        'option': 'report --all-l',
        'option_equals': 'report --compression-type=g',
        'plugin_list': 'report -e kernel,kern',
        'plugin_option': 'report -k kernel.trace=',
        'help_topic': 'help report.plugins.kern',
        'dirs': 'report --tmp-dir /tm',
        'file_list': 'report --skip-files /etc/hosts,/etc/passw',
    }

    def _generate_sos_command(self):
        # not all packaging formats install the script, e.g. snaps
        script = REPO_SCRIPT
        if (self.params.get('TESTLOCAL') == 'true' and
                os.path.exists(INSTALLED_SCRIPT)):
            script = INSTALLED_SCRIPT
        lines = ' '.join(f"'{line}'" for line in self.lines.values())
        return (f"bash {DRIVER} {self.driver_opts} {script} {self.sos_bin} "
                f"{lines}")

    def get_replies(self, name):
        """Return the COMPREPLY output by the driver for the named line"""
        section = self.cmd_output.stdout.split(f"### {self.lines[name]}\n")[1]
        return section.split('### ')[0].splitlines()

    def test_components(self):
        self.assertEqual(sorted(self.get_replies('components')),
                         ['rep', 'report'])

    def test_option(self):
        self.assertEqual(self.get_replies('option'), ['--all-logs'])

    def test_option_equals(self):
        self.assertEqual(self.get_replies('option_equals'), ['gzip'])

    def test_plugin_list(self):
        self.assertEqual(self.get_replies('plugin_list'), ['kernel,kernelrt'])

    def test_plugin_option(self):
        self.assertEqual(self.get_replies('plugin_option'), ['false', 'true'])

    def test_help_topic(self):
        self.assertIn('report.plugins.kernel', self.get_replies('help_topic'))

    def test_dirs(self):
        self.assertIn(self.get_replies('dirs')[0], ['/tmp', '/tmp/'])

    def test_file_list(self):
        self.assertIn('/etc/hosts,/etc/passwd', self.get_replies('file_list'))


class BashCompletionFallbackTest(BashCompletionTest):
    """Ensure that the bash completion script works without bash-completion

    :avocado: tags=stageone
    """

    driver_opts = '--no-bash-completion'

# vim: set et ts=4 sw=4 :
