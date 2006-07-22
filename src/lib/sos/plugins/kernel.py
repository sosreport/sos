### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import sos.plugintools
import commands, os

class kernel(sos.plugintools.PluginBase):
    """This plugin gathers kernel related information
    """
    optionList = [("modinfo", 'Gathers module information on all modules', 'fast', 1),
                  ('sysrq', 'Trigger SysRq dumps', 'fast', 1)]
    
    def setup(self):
        self.collectExtOutput("/bin/uname -a")
        self.collectExtOutput("/sbin/lsmod")
        if self.isOptionEnabled('modinfo'):
          for kmod in commands.getoutput('/sbin/lsmod | /bin/cut -f1 -d" " 2>/dev/null | /bin/grep -v Module 2>/dev/null').split('\n'):
            if '' != kmod.strip():
              runcmd = "/sbin/modinfo %s" % (kmod,)
              self.collectExtOutput(runcmd)
        self.collectExtOutput("/sbin/ksyms")
        self.addCopySpec("/proc/filesystems")
        self.addCopySpec("/proc/ksyms")
        self.addCopySpec("/proc/slabinfo")
        kver = commands.getoutput('/bin/uname -r')
        depfile = "/lib/modules/%s/modules.dep" % (kver,)
        self.addCopySpec(depfile)
        self.addCopySpec("/etc/conf.modules")
        self.addCopySpec("/etc/modules.conf")
        self.addCopySpec("/etc/modprobe.conf")
        self.collectExtOutput("/usr/sbin/dmidecode")
        self.collectExtOutput("/usr/sbin/dkms status")
        self.addCopySpec("/proc/cmdline")
        self.addCopySpec("/proc/driver")
        # trigger some sysrq's.  I'm not sure I like doing it this way, but
        # since we end up with the sysrq dumps in syslog whether we run the 
        # syslog report before or after this, I suppose I can live with it.
        if self.isOptionEnabled('sysrq') and os.access("/proc/sysrq-trigger", os.W_OK) and os.access("/proc/sys/kernel/sysrq", os.R_OK):
          sysrq_state = commands.getoutput("/bin/cat /proc/sys/kernel/sysrq")
          commands.getoutput("/bin/echo 1 > /proc/sys/kernel/sysrq")
          for key in ['m', 'p', 't']:
            commands.getoutput("/bin/echo %s > /proc/sysrq-trigger" % (key,))
          commands.getoutput("/bin/echo %s > /proc/sys/kernel/sysrq" % (sysrq_state,))
          # No need to grab syslog here if we can't trigger sysrq, so keep this
          # inside the if
          self.addCopySpec("/var/log/messages*")
        
        
        return

