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

class kernel_rt(Plugin, RedHatPlugin):
    '''Information specific to the realtime kernel
    '''

    # this file exists only when the realtime kernel is booted
    # this plugin will not be called is this file does not exist
    files = ('/sys/kernel/realtime',)

    def setup(self):
        self.addCopySpec('/etc/rtgroups')
        self.addCopySpec('/proc/sys/kernel/sched_rt_period_us')
        self.addCopySpec('/proc/sys/kernel/sched_rt_runtime_us')
        self.addCopySpec('/sys/kernel/realtime')
        self.addCopySpec('/sys/devices/system/clocksource/clocksource0/available_clocksource')
        self.addCopySpec('/sys/devices/system/clocksource/clocksource0/current_clocksource')
        if self.isInstalled('tuna'):
            self.collectExtOutput('/usr/bin/tuna -CP | /ust/bin/head -20')
