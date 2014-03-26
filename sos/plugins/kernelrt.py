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
    '''Information specific to the realtime kernel
    '''

    plugin_name = 'kernelrt'

    # this file exists only when the realtime kernel is booted
    # this plugin will not be called is this file does not exist
    files = ('/sys/kernel/realtime',)

    def setup(self):
        self.add_copy_spec('/etc/rtgroups')
        self.add_copy_spec('/proc/sys/kernel/sched_rt_period_us')
        self.add_copy_spec('/proc/sys/kernel/sched_rt_runtime_us')
        self.add_copy_spec('/sys/kernel/realtime')
        self.add_copy_spec('/sys/devices/system/clocksource/clocksource0/available_clocksource')
        self.add_copy_spec('/sys/devices/system/clocksource/clocksource0/current_clocksource')
        if self.is_installed('tuna'):
            self.add_cmd_output('tuna -CP | /usthead -20')

# vim: et ts=4 sw=4
