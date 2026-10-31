# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import importlib.util
import os
import unittest
from datetime import datetime, timedelta, timezone

SCRIPT = os.path.join(os.path.dirname(__file__), '..', '..', '.github',
                      'scripts', 'sos_bot.py')
spec = importlib.util.spec_from_file_location('sos_bot', SCRIPT)
sos_bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sos_bot)

NOW = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
AUTHOR = 'contributor'
MAINTAINER = 'maintainer'


def days_ago(days):
    return NOW - timedelta(days=days)


PLUGIN_SOURCE = """\
from sos.report.plugins import Plugin, IndependentPlugin


class Foo(Plugin, IndependentPlugin):

    short_desc = 'Foo'
    plugin_name = 'foo'

    def setup(self):
        self.add_cmd_output([
            "foo -m",
            "foo -h",
            "foo --summary",
        ])
        if self.get_option('all_logs'):
            self.add_copy_spec('/var/log/foo')
"""

# Adds "foo -h" to the add_cmd_output() list, as in sos PR #4567
LIST_ITEM_PATCH = """\
@@ -9,6 +9,7 @@ def setup(self):
     def setup(self):
         self.add_cmd_output([
             "foo -m",
+            "foo -h",
             "foo --summary",
         ])
         if self.get_option('all_logs'):"""

# Removes "foo -h" from the add_cmd_output() list, as in sos PR #4556
REMOVAL_PATCH = """\
@@ -9,7 +9,6 @@ def setup(self):
     def setup(self):
         self.add_cmd_output([
             "foo -m",
-            "foo -h",
             "foo --summary",
         ])
         if self.get_option('all_logs'):"""

# Adds the get_option() condition only
CONDITION_PATCH = """\
@@ -13,3 +13,4 @@ def setup(self):
             "foo --summary",
         ])
-        self.add_copy_spec('/var/log/foo')
+        if self.get_option('all_logs'):
+            self.add_copy_spec('/var/log/foo')"""

# Changes the get_option() condition only
OPTION_PATCH = """\
@@ -14,3 +14,3 @@ def setup(self):
         ])
-        if self.get_option('all'):
+        if self.get_option('all_logs'):
             self.add_copy_spec('/var/log/foo')"""


class FakeVersions():

    def __init__(self, before=None, after=None):
        self.before_source = before
        self.after_source = after

    def before(self, _path):
        return self.before_source

    def after(self, _path):
        return self.after_source


def plugin_file(patch, status='modified', name='foo.py'):
    return {'filename': f'sos/report/plugins/{name}', 'status': status,
            'patch': patch}


class PluginLabelTest(unittest.TestCase):

    def labels(self, files, before=PLUGIN_SOURCE, after=PLUGIN_SOURCE):
        return sos_bot.plugin_labels(files, FakeVersions(before, after))

    def test_changed_lines(self):
        self.assertEqual(sos_bot.changed_lines(LIST_ITEM_PATCH),
                         (set(), {12}))
        self.assertEqual(sos_bot.changed_lines(REMOVAL_PATCH), ({12}, set()))
        self.assertEqual(sos_bot.changed_lines(OPTION_PATCH), ({15}, {15}))

    def test_new_plugin(self):
        self.assertEqual(self.labels([plugin_file('+import os', 'added')]),
                         {'Kind/New plugin'})

    def test_added_list_item(self):
        self.assertEqual(self.labels([plugin_file(LIST_ITEM_PATCH)]),
                         {'Kind/Collection'})

    def test_removed_list_item(self):
        self.assertEqual(self.labels([plugin_file(REMOVAL_PATCH)]),
                         {'Kind/Collection'})

    def test_changed_collection_call(self):
        self.assertEqual(self.labels([plugin_file(CONDITION_PATCH)]),
                         {'Kind/Collection'})

    def test_non_collection_change(self):
        before = PLUGIN_SOURCE.replace("'all_logs'", "'all'")
        self.assertEqual(self.labels([plugin_file(OPTION_PATCH)], before),
                         set())

    def test_fallback_without_source(self):
        self.assertEqual(self.labels([plugin_file(CONDITION_PATCH)],
                                     None, None),
                         {'Kind/Collection'})
        self.assertEqual(self.labels([plugin_file(LIST_ITEM_PATCH)],
                                     None, None),
                         set())

    def test_ignored_files(self):
        files = [plugin_file("@@ -1 +1 @@\n+    def add_copy_spec(self):",
                             name='__init__.py'),
                 {'filename': 'sos/report/plugins/large.py',
                  'status': 'modified'},
                 {'filename': 'sos/cleaner/__init__.py', 'status': 'added'}]
        self.assertEqual(self.labels(files), set())


class PathLabelTest(unittest.TestCase):

    def test_components(self):
        self.assertEqual(sos_bot.path_labels([
            'sos/report/plugins/__init__.py',
            'sos/collector/clusters/ocp.py',
            'sos/report/__init__.py',
        ]), {'Kind/Plugin', 'Kind/collect', 'Kind/report'})

    def test_plugin_is_not_plugin_class(self):
        self.assertEqual(sos_bot.path_labels(['sos/report/plugins/foo.py']),
                         set())

    def test_documentation_only(self):
        self.assertEqual(sos_bot.path_labels(['man/en/sos-report.1',
                                              'docs/index.rst',
                                              'README.md']),
                         {'Kind/Documentation'})
        self.assertEqual(sos_bot.path_labels(['man/en/sos-report.1',
                                              'sos/report/__init__.py']),
                         {'Kind/report'})

    def test_testing_only(self):
        self.assertEqual(sos_bot.path_labels([
            'tests/unittests/plugin_tests.py',
            '.github/workflows/avocado.yaml',
        ]), {'Kind/Testing'})

    def test_no_files(self):
        self.assertEqual(sos_bot.path_labels([]), set())


class BotTest(unittest.TestCase):

    def test_is_bot(self):
        self.assertTrue(sos_bot.is_bot({'login': 'packit-as-a-service[bot]',
                                        'type': 'Bot'}))
        self.assertTrue(sos_bot.is_bot({'login': 'sos-bot[bot]'}))
        self.assertTrue(sos_bot.is_bot(None))
        self.assertFalse(sos_bot.is_bot({'login': AUTHOR, 'type': 'User'}))

    def test_parse_time(self):
        self.assertEqual(sos_bot.parse_time('2026-10-31T12:00:00Z'), NOW)


class LifecycleDecisionTest(unittest.TestCase):

    def decide(self, activity, nudges=(), abandoned_at=None):
        return sos_bot.decide(NOW, activity, AUTHOR, list(nudges),
                              abandoned_at, sos_bot.DEFAULT_THRESHOLDS)

    def test_active(self):
        self.assertIsNone(self.decide([(days_ago(89), AUTHOR)]))

    def test_nudge(self):
        self.assertEqual(self.decide([(days_ago(90), MAINTAINER)]), 'nudge')

    def test_nudged_waiting(self):
        self.assertIsNone(self.decide([(days_ago(179), AUTHOR)],
                                      nudges=[days_ago(89)]))

    def test_abandon(self):
        self.assertEqual(self.decide([(days_ago(180), AUTHOR)],
                                     nudges=[days_ago(90)]), 'abandon')

    def test_backlog_gets_full_period_after_nudge(self):
        self.assertIsNone(self.decide([(days_ago(400), AUTHOR)],
                                      nudges=[days_ago(10)]))

    def test_activity_after_nudge_resets(self):
        self.assertIsNone(self.decide([(days_ago(200), AUTHOR),
                                       (days_ago(30), MAINTAINER)],
                                      nudges=[days_ago(110)]))

    def test_abandoned_waiting(self):
        self.assertIsNone(self.decide([(days_ago(269), AUTHOR)],
                                      abandoned_at=days_ago(89)))

    def test_close(self):
        self.assertEqual(self.decide([(days_ago(400), AUTHOR)],
                                     abandoned_at=days_ago(90)), 'close')

    def test_author_returns(self):
        self.assertEqual(self.decide([(days_ago(400), AUTHOR),
                                      (days_ago(5), AUTHOR)],
                                     abandoned_at=days_ago(100)),
                         'unabandon')

    def test_maintainer_comment_does_not_unabandon(self):
        self.assertEqual(self.decide([(days_ago(400), AUTHOR),
                                      (days_ago(100), MAINTAINER)],
                                     abandoned_at=days_ago(100)), 'close')


if __name__ == '__main__':
    unittest.main()
