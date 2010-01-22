import unittest
import sys
import os
import sos.policyredhat
from sos.helpers import *

class testPluginSanity(unittest.TestCase):
    """ tests plugins don't fail due to indentation errors
        etc.
    """
    def setUp(self):
        self.policy = sos.policyredhat.SosPolicy()
        # build plugins list
        paths = sys.path
        for path in paths:
            if path.strip()[-len("site-packages"):] == "site-packages" \
            and os.path.isdir(path + "/sos/plugins"):
                pluginpath = path + "/sos/plugins"
        self.plugins = os.listdir(pluginpath)
        self.plugins.sort()

    def testPluginLoad(self):
        for plug in self.plugins:
            plugbase = plug[:-3]
            if not plug[-3:] == '.py' or plugbase == "__init__":
                continue
            try:
                loadPlugin = importPlugin("sos.plugins." + plugbase, plugbase)
            except:
                self.fail("Plugin exception on %s" % (plugbase,))

if __name__=="__main__":
    unittest.main()

