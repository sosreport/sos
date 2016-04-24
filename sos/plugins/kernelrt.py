# -*- python -*-
# -*- coding: utf-8 -*-

#
# Copyright 2012 Red Hat Inc.
# Guy Streeter <streeter@redhat.com>
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; version 2.
#
#   This application is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.

from sos.plugins import Plugin, RedHatPlugin


class KernelRT(Plugin, RedHatPlugin):
    '''Realtime kernel variant
    '''

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
