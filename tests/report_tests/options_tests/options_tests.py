# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos_tests import StageTwoReportTest


class OptionsFromConfigTest(StageTwoReportTest):
    """Ensure that we handle options specified in sos.conf properly

    :avocado: tags=stagetwo
    """

    files = [('options_tests_sos.conf', '/etc/sos/sos.conf')]
    sos_cmd = '-v '

    def test_case_id_from_config(self):
        self.assertTrue('8675309' in self.archive)

    def test_plugins_only_from_config(self):
        self.assertOnlyPluginsIncluded(['host', 'kernel'])

    def test_plugopts_logged_from_config(self):
        self.assertSosLogContains(
            "Set kernel plugin option to \(name=with-timer, desc='gather /proc/timer\* statistics', value=True, default=False\)"
        )
        self.assertSosLogContains(
            "Set kernel plugin option to \(name=trace, desc='gather /sys/kernel/debug/tracing/trace file', value=True, default=False\)"
        )

    def test_disabled_plugopts_not_loaded(self):
        self.assertSosLogNotContains("Set networking plugin option to")

    def test_plugopts_actually_set(self):
        self.assertFileCollected('sys/kernel/debug/tracing/trace')

    def test_effective_options_logged_correctly(self):
        self.assertSosLogContains(
            "effective options now: --batch --case-id 8675309 --only-plugins host,kernel --plugopts kernel.with-timer=on,kernel.trace=yes"
        )
