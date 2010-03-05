import sos.plugintools
import commands
import glob
import os
from os.path import exists


class qpidd(sos.plugintools.PluginBase):
    """Messaging related information
    """
    def checkenabled(self):
         if self.cInfo["policy"].pkgByName("qpidd"):
             return True
         return False

    def setup(self):
        self.addCopySpec("/etc/qpidd.conf")
        self.collectExtOutput("/usr/bin/qpid-stat -q")
        self.collectExtOutput("/usr/bin/qpid-stat -e")
        self.collectExtOutput("/usr/bin/qpid-stat -b")
        self.addCopySpec("/var/lib/qpid/syslog")
