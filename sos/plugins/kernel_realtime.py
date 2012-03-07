# Copyright 2012 Red Hat Inc.
# Guy Streeter <streeter redhat com>
# Bryn M. Reeves <bmr@redhat.com>
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; version 2.
#
#   This application is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.

import sos.plugintools
import os

class kernel_realtime(sos.plugintools.PluginBase):
    '''Information specific to the realtime kernel
    '''

    def checkenabled(self):
        if os.path.exists('/sys/kernel/realtime'):
            return True
        return False

    def setup(self):
        self.addCopySpec('/etc/rtgroups')
        self.addCopySpec('/proc/sys/kernel/sched_rt_period_us')
        self.addCopySpec('/proc/sys/kernel/sched_rt_runtime_us')
        self.addCopySpec('/sys/kernel/realtime')
        if self.isInstalled('tuna'):
            self.collectExtOutput('/usr/bin/tuna -CP')
