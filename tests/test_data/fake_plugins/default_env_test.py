# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class DefaultEnv(Plugin, IndependentPlugin):

    plugin_name = 'default_env_test'
    short_desc = 'Fake plugin to test default env var handling'

    def setup(self):
        self.set_default_cmd_environment({
            'TORVALDS': 'Linus',
            'GREATESTSPORT': 'hockey'
        })

        self.add_cmd_output(
            "sh -c 'echo Does '$TORVALDS' play '$GREATESTSPORT'?'",
            suggest_filename='env_var_test'
        )

        self.add_env_var(['TORVALDS', 'GREATESTSPORT'])
