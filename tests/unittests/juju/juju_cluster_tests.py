# Copyright (c) 2023 Canonical Ltd., Chi Wai Chan <chiwai.chan@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import json
import pathlib
import unittest
from unittest.mock import call, patch

from sos.collector.clusters.juju import _parse_option_string, juju, _get_index
from sos.options import ClusterOption


class MockOptions:

    def __init__(self):
        self.cluster_options = []


def get_juju_output(model):
    _dir = pathlib.Path(__file__).parent.resolve()
    with open(_dir / "data" / f"juju_output_{model}.json",
              encoding='utf-8') as f:
        return f.read()


def get_juju_status(cmd):
    if "-m" in cmd:
        model = cmd.split()[3]
    else:
        model = "sos"

    return {
        "status": 0,
        "output": get_juju_output(model),
    }


def get_juju_version():
    return "2.9.45"


def test_parse_option_string():
    result = _parse_option_string("    a,b,c")
    assert result == ["a", "b", "c"]

    result = _parse_option_string()
    assert result == []


class JujuTest(unittest.TestCase):
    """Test for juju cluster."""

    @patch(
        "sos.collector.clusters.juju.juju.exec_primary_cmd",
        side_effect=get_juju_status,
    )
    # pylint: disable=unused-argument
    def test_get_nodes_no_filter(self, mock_exec_primary_cmd):
        """No filter."""
        mock_opts = MockOptions()
        cluster = juju(
            commons={
                "tmpdir": "/tmp",
                "cmdlineopts": mock_opts,
            }
        )
        nodes = cluster.get_nodes()
        assert not nodes

    @patch(
        "sos.collector.clusters.juju.juju._get_juju_version",
        side_effect=get_juju_version,
    )
    @patch(
        "sos.collector.clusters.juju.juju.exec_primary_cmd",
        side_effect=get_juju_status,
    )
    # pylint: disable=unused-argument
    def test_get_nodes_app_filter(
        self, mock_exec_primary_cmd, mock_get_juju_version
    ):
        """Application filter."""
        mock_opts = MockOptions()
        mock_opts.cluster_options.append(
            ClusterOption(
                name="apps",
                opt_type=str,
                value="ubuntu",
                cluster=juju.__name__,
            )
        )
        cluster = juju(
            commons={
                "tmpdir": "/tmp",
                "cmdlineopts": mock_opts,
            }
        )
        nodes = cluster.get_nodes()
        nodes.sort()
        assert nodes == [":0", ":2", ":3"]
        mock_exec_primary_cmd.assert_called_once_with(
            "juju status  --format json"
        )

    @patch(
        "sos.collector.clusters.juju.juju._get_juju_version",
        side_effect=get_juju_version,
    )
    @patch(
        "sos.collector.clusters.juju.juju.exec_primary_cmd",
        side_effect=get_juju_status,
    )
    # pylint: disable=unused-argument
    def test_get_nodes_app_regex_filter(
        self, mock_exec_primary_cmd, mock_get_juju_version
    ):
        """Application filter."""
        mock_opts = MockOptions()
        mock_opts.cluster_options.append(
            ClusterOption(
                name="apps",
                opt_type=str,
                value="ubuntu|nginx",
                cluster=juju.__name__,
            )
        )
        cluster = juju(
            commons={
                "tmpdir": "/tmp",
                "cmdlineopts": mock_opts,
            }
        )
        nodes = cluster.get_nodes()
        nodes.sort()
        assert nodes == [":0", ":2", ":3", ":4"]
        mock_exec_primary_cmd.assert_called_once_with(
            "juju status  --format json"
        )

    @patch(
        "sos.collector.clusters.juju.juju._get_juju_version",
        side_effect=get_juju_version,
    )
    @patch(
        "sos.collector.clusters.juju.juju.exec_primary_cmd",
        side_effect=get_juju_status,
    )
    # pylint: disable=unused-argument
    def test_get_nodes_model_filter_multiple_models(
        self, mock_exec_primary_cmd, mock_get_juju_version
    ):
        """Multiple model filter."""
        mock_opts = MockOptions()
        mock_opts.cluster_options.append(
            ClusterOption(
                name="models",
                opt_type=str,
                value="sos,sos2",
                cluster=juju.__name__,
            ),
        )
        mock_opts.cluster_options.append(
            ClusterOption(
                name="apps",
                opt_type=str,
                value="ubuntu",
                cluster=juju.__name__,
            ),
        )
        cluster = juju(
            commons={
                "tmpdir": "/tmp",
                "cmdlineopts": mock_opts,
            }
        )
        nodes = cluster.get_nodes()
        nodes.sort()
        assert nodes == [
            "sos2:0",
            "sos2:1",
            "sos:0",
            "sos:2",
            "sos:3",
        ]
        mock_exec_primary_cmd.assert_has_calls(
            [
                call("juju status -m sos --format json"),
                call("juju status -m sos2 --format json"),
            ]
        )

    @patch(
        "sos.collector.clusters.juju.juju._get_juju_version",
        side_effect=get_juju_version,
    )
    @patch(
        "sos.collector.clusters.juju.juju.exec_primary_cmd",
        side_effect=get_juju_status,
    )
    # pylint: disable=unused-argument
    def test_get_nodes_model_filter(
        self, mock_exec_primary_cmd, mock_get_juju_version
    ):
        """Model filter."""
        mock_opts = MockOptions()
        mock_opts.cluster_options.append(
            ClusterOption(
                name="models",
                opt_type=str,
                value="sos",
                cluster=juju.__name__,
            )
        )
        mock_opts.cluster_options.append(
            ClusterOption(
                name="apps",
                opt_type=str,
                value="ubuntu",
                cluster=juju.__name__,
            ),
        )
        cluster = juju(
            commons={
                "tmpdir": "/tmp",
                "cmdlineopts": mock_opts,
            }
        )
        nodes = cluster.get_nodes()
        nodes.sort()
        assert nodes == [
            "sos:0",
            "sos:2",
            "sos:3",
        ]
        mock_exec_primary_cmd.assert_has_calls(
            [
                call("juju status -m sos --format json"),
            ]
        )

    @patch(
        "sos.collector.clusters.juju.juju._get_juju_version",
        side_effect=get_juju_version,
    )
    @patch(
        "sos.collector.clusters.juju.juju.exec_primary_cmd",
        side_effect=get_juju_status,
    )
    # pylint: disable=unused-argument
    def test_get_nodes_unit_filter(
        self, mock_exec_primary_cmd, mock_get_juju_version
    ):
        """Node filter."""
        mock_opts = MockOptions()
        mock_opts.cluster_options.append(
            ClusterOption(
                name="units",
                opt_type=str,
                value="ubuntu/0,ubuntu/1",
                cluster=juju.__name__,
            )
        )
        cluster = juju(
            commons={
                "tmpdir": "/tmp",
                "cmdlineopts": mock_opts,
            }
        )
        nodes = cluster.get_nodes()
        nodes.sort()
        assert nodes == [":0", ":2"]

    @patch(
        "sos.collector.clusters.juju.juju._get_juju_version",
        side_effect=get_juju_version,
    )
    @patch(
        "sos.collector.clusters.juju.juju.exec_primary_cmd",
        side_effect=get_juju_status,
    )
    # pylint: disable=unused-argument
    def test_get_nodes_machine_filter(
        self, mock_exec_primary_cmd, mock_get_juju_version
    ):
        """Machine filter."""
        mock_opts = MockOptions()
        mock_opts.cluster_options.append(
            ClusterOption(
                name="machines",
                opt_type=str,
                value="0,2",
                cluster=juju.__name__,
            )
        )
        cluster = juju(
            commons={
                "tmpdir": "/tmp",
                "cmdlineopts": mock_opts,
            }
        )
        nodes = cluster.get_nodes()
        nodes.sort()
        print(nodes)
        assert nodes == [":0", ":2"]

    @patch(
        "sos.collector.clusters.juju.juju._get_juju_version",
        side_effect=get_juju_version,
    )
    @patch(
        "sos.collector.clusters.juju.juju.exec_primary_cmd",
        side_effect=get_juju_status,
    )
    # pylint: disable=unused-argument
    def test_subordinates(self, mock_exec_primary_cmd, mock_get_juju_version):
        """Subordinate filter."""
        mock_opts = MockOptions()
        mock_opts.cluster_options.append(
            ClusterOption(
                name="apps",
                opt_type=str,
                value="nrpe",
                cluster=juju.__name__,
            )
        )
        cluster = juju(
            commons={
                "tmpdir": "/tmp",
                "cmdlineopts": mock_opts,
            }
        )
        nodes = cluster.get_nodes()
        nodes.sort()
        assert nodes == [":0", ":2", ":3"]
        mock_exec_primary_cmd.assert_called_once_with(
            "juju status  --format json"
        )


class IndexTest(unittest.TestCase):

    def test_subordinate_parent_miss_units(self):
        """Fix if subordinate's parent is missing units."""
        model = "sos"
        index = _get_index(model_name=model)

        juju_status = json.loads(get_juju_output(model=model))
        juju_status["applications"]["ubuntu"].pop("units")

        # Ensure these commands won't fall even when
        # subordinate's parent's units is missing.
        index.add_principals(juju_status)
        index.add_subordinates(juju_status)

    def test_subordinate_miss_parent(self):
        """Fix if subordinate is missing parent."""
        model = "sos"
        index = _get_index(model_name=model)

        juju_status = json.loads(get_juju_output(model=model))
        index.add_principals(juju_status)

        index.apps.pop("ubuntu")
        # Ensure command won't fall even when
        # subordinate's parent is missing
        index.add_subordinates(juju_status)


# vim: set et ts=4 sw=4 :
