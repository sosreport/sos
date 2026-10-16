# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import unittest

from sos import SoS
from sos.completion import Completion
from sos.completion.shells import BashFormatter

try:
    import sos.collector  # noqa: F401 pylint: disable=unused-import
    HAS_COLLECT = True
except ImportError:
    HAS_COLLECT = False


class CompletionTest(unittest.TestCase):
    """Tests for determining completion candidates, independent of any shell
    """

    @classmethod
    def setUpClass(cls):
        # pylint: disable=protected-access
        cls.completer = SoS(['_complete'])._component

    def complete(self, line):
        """Complete the last space-delimited word of ``line``"""
        words = line.split(' ')
        return self.completer.complete(words, len(words) - 1)

    def candidates(self, line):
        result = self.complete(line)
        self.assertEqual(result.kind, Completion.WORDS)
        return result.candidates

    def test_components(self):
        cands = self.candidates('sos ')
        for comp in ('report', 'rep', 'clean', 'cleaner', 'mask', 'collect',
                     'help', 'upload'):
            self.assertIn(comp, cands)

    def test_component_prefix(self):
        self.assertEqual(self.candidates('sos cl'), ['clean', 'cleaner'])

    def test_top_level_options(self):
        self.assertEqual(self.candidates('sos --v'), ['--version'])

    def test_unknown_component(self):
        self.assertEqual(self.complete('sos foo --b').kind, Completion.NONE)

    def test_long_option(self):
        self.assertEqual(self.candidates('sos report --all-l'),
                         ['--all-logs'])

    def test_alias_uses_component_options(self):
        self.assertEqual(self.candidates('sos rep --all-l'), ['--all-logs'])

    def test_empty_word_offers_long_options_only(self):
        cands = self.candidates('sos report ')
        self.assertIn('--batch', cands)
        self.assertNotIn('-a', cands)

    def test_short_option(self):
        self.assertEqual(self.candidates('sos report -a'), ['-a'])

    def test_choices(self):
        self.assertEqual(sorted(self.candidates('sos report -z ')),
                         ['auto', 'gzip', 'none', 'xz'])

    def test_option_equals_value(self):
        self.assertEqual(self.candidates('sos report --compression-type=g'),
                         ['--compression-type=gzip'])

    def test_abbreviated_option_value(self):
        self.assertIn('gzip', self.candidates('sos report --compression '))

    def test_flag_does_not_consume_word(self):
        self.assertEqual(self.candidates('sos report -a --bat'), ['--batch'])

    def test_option_value_consumed(self):
        self.assertEqual(self.candidates('sos report -t 4 --bat'),
                         ['--batch'])

    def test_attached_short_value(self):
        self.assertEqual(self.candidates('sos report -t4 --bat'), ['--batch'])

    def test_grouped_short_options(self):
        self.assertIn('gzip', self.candidates('sos report -vqz '))

    def test_free_text_value(self):
        self.assertEqual(self.complete('sos report --case-id ').kind,
                         Completion.NONE)

    def test_report_chroot(self):
        self.assertEqual(self.candidates('sos report -c '),
                         ['auto', 'always', 'never'])

    def test_report_profiles(self):
        self.assertIn('system', self.candidates('sos report -p '))

    def test_plugins(self):
        self.assertIn('kernel', self.candidates('sos report -e kern'))

    def test_plugin_list(self):
        self.assertEqual(self.candidates('sos report -o kernel,kern'),
                         ['kernel,kernelrt'])

    def test_plugin_option_plugins(self):
        result = self.complete('sos report -k kerne')
        self.assertEqual(result.candidates, ['kernel.', 'kernelrt.'])
        self.assertTrue(result.nospace)

    def test_plugin_option_names(self):
        cands = self.candidates('sos report -k kernel.')
        for opt in ('kernel.trace', 'kernel.timeout', 'kernel.postproc'):
            self.assertIn(opt, cands)

    def test_plugin_option_bool_value(self):
        self.assertEqual(self.candidates('sos report -k kernel.trace='),
                         ['kernel.trace=false', 'kernel.trace=true'])

    def test_presets(self):
        cands = self.candidates('sos report --preset ')
        self.assertIn('minimal', cands)
        self.assertIn('none', cands)

    def test_cleaner_parsers(self):
        self.assertEqual(self.candidates('sos clean --disable-parsers '),
                         ['hostname', 'ip', 'ipv6', 'keyword', 'mac',
                          'username'])

    def test_container_runtimes(self):
        cands = self.candidates('sos report --container-runtime ')
        self.assertIn('auto', cands)
        self.assertIn('podman', cands)

    def test_help_topics_one_level(self):
        cands = self.candidates('sos help ')
        self.assertIn('report', cands)
        self.assertIn('report.', cands)
        self.assertNotIn('report.plugins.kernel', cands)

    def test_help_plugin_topics(self):
        self.assertIn('report.plugins.kernel',
                      self.candidates('sos help report.plugins.kern'))

    def test_clean_target(self):
        result = self.complete('sos clean /tm')
        self.assertEqual(result.kind, 'files')
        self.assertEqual(result.value, '/tm')

    def test_upload_file(self):
        self.assertEqual(self.complete('sos upload /tm').kind, 'files')

    def test_end_of_options(self):
        result = self.complete('sos clean -- --foo')
        self.assertEqual(result.kind, 'files')
        self.assertEqual(result.value, '--foo')

    def test_directory_option(self):
        self.assertEqual(self.complete('sos report --tmp-dir /t').kind,
                         'dirs')

    def test_file_list_option(self):
        result = self.complete('sos report --skip-files /etc/a,/etc/b')
        self.assertEqual(result.kind, 'files')
        self.assertEqual(result.prefix, '/etc/a,')
        self.assertEqual(result.value, '/etc/b')

    @unittest.skipUnless(HAS_COLLECT, 'sos collect is not available')
    def test_collect_cluster_options(self):
        self.assertIn('ocp.', self.candidates('sos collect -c '))
        self.assertIn('ocp.label', self.candidates('sos collect -c ocp.'))

    @unittest.skipUnless(HAS_COLLECT, 'sos collect is not available')
    def test_collect_short_options_differ(self):
        self.assertEqual(self.complete('sos collect -p ').kind,
                         Completion.NONE)
        self.assertEqual(self.candidates('sos collect -l --bat'),
                         ['--batch'])

    @unittest.skipUnless(HAS_COLLECT, 'sos collect is not available')
    def test_collect_cluster_types(self):
        self.assertIn('ocp', self.candidates('sos collect --cluster-type '))

    @unittest.skipUnless(HAS_COLLECT, 'sos collect is not available')
    def test_collect_transports(self):
        self.assertIn('control_persist',
                      self.candidates('sos collect --transport '))

    @unittest.skipUnless(HAS_COLLECT, 'sos collect is not available')
    def test_collect_nodes(self):
        result = self.complete('sos collect --nodes node1,no')
        self.assertEqual(result.kind, 'hosts')
        self.assertEqual(result.prefix, 'node1,')
        self.assertEqual(result.value, 'no')


class BashFormatterTest(unittest.TestCase):
    """Tests for the output consumed by the bash completion script"""

    wordbreaks = '"\'><=;|&(:'

    def format(self, completion, cur, wordbreaks=None):
        fmt = BashFormatter([wordbreaks or self.wordbreaks])
        return fmt.format(completion, cur).splitlines()

    def test_words(self):
        comp = Completion(candidates=['report', 'rep'])
        self.assertEqual(self.format(comp, 're'),
                         ['words 0', '', '', 'report', 'rep'])

    def test_nospace(self):
        comp = Completion(candidates=['kernel.'], nospace=True)
        self.assertEqual(self.format(comp, 'kern')[0], 'words 1')

    def test_strip_equals_wordbreak(self):
        comp = Completion(candidates=['--preset=minimal'])
        self.assertEqual(self.format(comp, '--preset=mi')[3], 'minimal')

    def test_strip_colon_wordbreak(self):
        comp = Completion(candidates=['ocp.label=a:bc'])
        self.assertEqual(self.format(comp, 'ocp.label=a:b')[3], 'bc')

    def test_no_strip_without_wordbreak(self):
        comp = Completion(candidates=['--preset=minimal'])
        self.assertEqual(self.format(comp, '--preset=mi', ' ')[3],
                         '--preset=minimal')

    def test_files_prefix(self):
        comp = Completion('files', prefix='--skip-files=/etc/a,',
                          value='/etc/b')
        self.assertEqual(self.format(comp, '--skip-files=/etc/a,/etc/b'),
                         ['files 0', '/etc/a,', '/etc/b'])


if __name__ == "__main__":
    unittest.main()

# vim: set et ts=4 sw=4 :
