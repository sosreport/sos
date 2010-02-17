import os, sys, shutil
from commons import *
from nose.tools import *
from sos.sosreport import *
from glob import glob

class GlobalVars:
    pass

class TestBasicSos:
    def __init__(self):
        GlobalVars.dstroot = None
        GlobalVars.commons = commons
        # clean pre-existing dummy plugins
        for i in glob(GlobalVars.commons['pluginpath']+'/dummyPlugin*'):
            os.remove(os.path.join(GlobalVars.commons['pluginpath'],i))

    def setup(self):
        """ prework """
        pass

    def teardown(self):
        """ cleanup dstroot and other miscellaneous files """
        if os.path.isdir(GlobalVars.dstroot) and not None:
            shutil.rmtree(GlobalVars.dstroot)

    def testSosreportBin(self):
        """ test existence of sosreport bin """
        if not os.path.isfile(GlobalVars.commons['bin']):
            raise AssertionError("Sosreport executable does not exist")


    def testUnattended(self):
        """ test unattended """
        GlobalVars.commons['testOptions'].append("-ofilesys")
        GlobalVars.dstroot = sosreport(GlobalVars.commons['testOptions'])
        if not os.path.isdir(GlobalVars.dstroot):
            raise AssertionError("No sosreport created")

    def testPluginEnable(self):
        """ test success of plugin enable """
        if os.path.isdir(GlobalVars.commons['pluginpath']):
            shutil.copy('fixture/dummyPluginEnabled.py',GlobalVars.commons['pluginpath'])
        GlobalVars.commons['testOptions'].append('-odummyPluginEnabled')
        GlobalVars.dstroot = sosreport(GlobalVars.commons['testOptions'])
        if os.path.isdir(GlobalVars.dstroot) \
        and os.path.isfile(os.path.join(GlobalVars.dstroot,'tmp/testenabled.file')):
            return True
        raise AssertionError("testenabled.file not found")

    def testPluginDisable(self):
        """ test plugin disable """
        if os.path.isdir(GlobalVars.commons['pluginpath']):
            shutil.copy('fixture/dummyPluginDisabled.py',GlobalVars.commons['pluginpath'])
        GlobalVars.dstroot = sosreport(["-nrpm","-nselinux","--batch","--build"])
        if os.path.isdir(GlobalVars.dstroot) \
        and os.path.isfile(os.path.join(GlobalVars.dstroot,'tmp/testenabled.file')):
            raise AssertionError("plugin not disabled")
        return True
