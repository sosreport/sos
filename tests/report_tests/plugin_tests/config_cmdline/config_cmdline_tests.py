# Copyright (C) 2026 Red Hat, Inc., Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageTwoReportTest


class SkippedPluginConfigCmdlineTest(StageTwoReportTest):
    """Ensure that we handle skipped plugins specified
    in sos.conf and merge them with cmdline properly

    :avocado: tags=stagetwo
    """

    files = [('config_cmdline_skipped_tests_sos.conf', '/etc/sos/sos.conf')]
    sos_cmd = '-n kernel'

    def test_skip_plugins_merged_from_conf_and_cmdline(self):
        # Plugin host is deactivated via sos.conf file
        # Plugin kernel is deactivated via cmdline
        options = r'--skip-plugins (host,kernel|kernel,host)'
        self.assertSosLogContains(f"effective options now: .*{options}")
        self.assertPluginNotIncluded('host')
        self.assertPluginNotIncluded('kernel')


class EnabledPluginConfigCmdlineTest(StageTwoReportTest):
    """Ensure that we handle enabled plugins specified in sos.conf
    and merge them with cmdline properly

    :avocado: tags=stagetwo
    """

    files = [('config_cmdline_enabled_tests_sos.conf', '/etc/sos/sos.conf')]
    sos_cmd = '-e memory'

    def test_enabled_plugins_merged_from_conf_and_cmdline(self):
        # Plugin networking is enabled via sos.conf file
        # Plugin memory is enabled via cmdline
        options = r'--enable-plugins (networking,memory|memory,networking)'
        self.assertSosLogContains(f"effective options now: .*{options}")
        self.assertPluginIncluded('networking')
        self.assertPluginIncluded('memory')


class PreferPluginPresetConfigTest(StageTwoReportTest):
    """Test that the preset takes precedence over config file

    :avocado: tags=stagetwo
    """

    files = [('config_preset_precedence_tests_sos.conf', '/etc/sos/sos.conf'),
             ('config_preset_precedence_tests.json',
              '/etc/sos/presets.d/plugins_preset')]
    sos_cmd = '--preset plugins_preset'

    def test_precedence_preset_config(self):
        # Plugin memory is enabled via sos.conf file
        # Plugin memory is skipped via preset file
        options = r'--skip-plugins memory'
        self.assertSosLogContains(f"effective options now: .*{options}")
        self.assertPluginNotIncluded('memory')


class OnlyPluginConfigCmdlineTest(StageTwoReportTest):
    """Test that only-plugins from cmdline replaces rather than merges
    config value

    Unlike skip-plugins and enable-plugins, which merge, only-plugins uses
    replacement since it defines an exclusive set.

    :avocado: tags=stagetwo
    """

    files = [('config_cmdline_only_tests_sos.conf', '/etc/sos/sos.conf')]
    sos_cmd = '-o kernel'

    def test_only_plugins_cmdline_replaces_config(self):
        # Plugin host is enabled (only) via sos.conf file
        # Plugin kernel is specified via cmdline
        options = r'--only-plugins kernel'
        self.assertSosLogContains(f"effective options now: .*{options}")
        self.assertPluginIncluded('kernel')
        self.assertPluginNotIncluded('host')
