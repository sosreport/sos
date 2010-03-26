from sos.sosreport import *
from commons import *
from nose.tools import *
import os, sys, shutil

class GlobalVars:
    pass

class TestLDAP:
    def __init__(self):
        GlobalVars.commons = commons
        GlobalVars.dstroot = None

    def setup(self):
        """ prework """
        pass

    def teardown(self):
        """ cleanup dstroot and other miscellaneous files """
        if os.path.isdir(GlobalVars.dstroot) and not None:
            shutil.rmtree(GlobalVars.dstroot)

    def testPostProc(self):
        """ check scraping of bindpw if exists """
        GlobalVars.commons['testOptions'].append("-oldap")
        GlobalVars.dstroot = sosreport(GlobalVars.commons['testOptions'])
        ldapconf = os.path.join(GlobalVars.dstroot,'etc/ldap.conf')
        if os.path.isfile(ldapconf) and os.path.isfile("/etc/ldap.conf"):
            f = open('/etc/ldap.conf','r').readlines()
            for line in f:
                assert_false('bindpw ***' in line)

    def testCapture(self):
        """ check for capture of proper files """
        GlobalVars.commons['testOptions'].append("-oldap")
        GlobalVars.dstroot = sosreport(GlobalVars.commons['testOptions'])
        ldapdir = os.path.join(GlobalVars.dstroot,'etc/openldap')
        if os.path.isdir(ldapdir) and \
        os.path.isfile(os.path.join(GlobalVars.dstroot,'etc/ldap.conf')):
            GlobalVars.commons['testOptions'].pop()
            assert_true
