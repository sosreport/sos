# Copyright 2012 Red Hat Inc.
# Guy Streeter <streeter@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class KernelRT(Plugin, RedHatPlugin):

    short_desc = 'Realtime kernel variant'

    plugin_name = 'kernelrt'
    profiles = ('system', 'hardware', 'kernel', 'mrg')

    # this file exists only when the realtime kernel is booted
    # this plugin will not be called is this file does not exist
    files = ('/sys/kernel/realtime',)

    def setup(self):
        clocksource_path = '/sys/devices/system/clocksource/clocksource0/'
        self.add_copy_spec([
            '/etc/rtgroups',
            '/proc/sys/kernel/sched_rt_period_us',
            '/proc/sys/kernel/sched_rt_runtime_us',
            '/sys/kernel/realtime',
            clocksource_path + 'available_clocksource',
            clocksource_path + 'current_clocksource'
        ])
        # note: rhbz#1059685 'tuna - NameError: global name 'cgroups' is not
        # defined this command throws an exception on versions prior to
        # 0.10.4-5.
        self.add_cmd_output('tuna -CP')

# vim: set et ts=4 sw=4 :
