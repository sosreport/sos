# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos_tests import StageTwoReportTest


class OptionsConfigPresetCmdlineTest(StageTwoReportTest):
    """Ensure that we handle options specified in sos.conf and
    merge them with cmdline and preset properly

    :avocado: tags=stagetwo
    """

    files = [('options_tests_sos.conf', '/etc/sos/sos.conf')]
    sos_cmd = '--preset minimal --journal-size 20 --cmd-timeout 60'

    def test_case_id_from_config(self):
        self.assertTrue('8675309' in self.archive)

    def test_plugins_only_from_config(self):
        self.assertOnlyPluginsIncluded(['host', 'kernel'])

    def test_plugopts_logged_from_config(self):
        self.assertSosLogContains(
            r"Set kernel plugin option to \(name=with-timer, "
            r"desc='gather /proc/timer\* statistics', value=True, "
            r"default=False\)"
        )
        self.assertSosLogContains(
            r"Set kernel plugin option to \(name=trace, "
            "desc='gather /sys/kernel/debug/tracing/trace file', "
            r"value=True, default=False\)"
        )

    def test_disabled_plugopts_not_loaded(self):
        self.assertSosLogNotContains("Set networking plugin option to")

    def test_plugopts_actually_set(self):
        self.assertFileCollected('sys/kernel/debug/tracing/trace')

    def test_effective_options_logged_correctly(self):
        for option in [
            "--case-id 8675309",
            "--only-plugins host,kernel",
            "--plugopts kernel.with-timer=on,kernel.trace=yes",
            "--preset minimal",
            "--cmd-timeout 60",      # cmdline beats config and preset
            "--journal-size 20",     # cmdline beats preset
            "--log-size 10",         # preset setting is honored
            "--plugin-timeout 30",   # preset beats config file
        ]:
            self.assertSosLogContains(f"effective options now: .* {option}")


class PlugOptsConfigPresetCmdlineTest(StageTwoReportTest):
    """Ensure that plugin options specified in sos.conf or preset or cmdline
    are handled and merged properly.

    :avocado: tags=stagetwo
    """

    files = [
        ('options_tests_sos.conf', '/etc/sos/sos.conf'),
        ('options_tests_preset.json', '/etc/sos/presets.d/plugopts_preset')
    ]
    sos_cmd = '--preset plugopts_preset --container-runtime=none ' \
              '-k crio.timeout=10,networking.timeout=20 -o crio,networking'
    redhat_only = True

    def test_effective_plugopts_logged_correctly(self):
        for option in [
            "--only-plugins crio,networking",
            "--preset plugopts_preset",
            "networking.timeout=20",                # cmd beats config&preset
            "crio.timeout=10",                      # cmdline beats preset
            "networking.ethtool-namespaces=False",  # preset setting is honored
            "networking.namespaces=200",            # preset beats config file
        ]:
            self.assertSosLogContains(f"effective options now: .*{option}")
