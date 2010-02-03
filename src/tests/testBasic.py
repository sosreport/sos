import os
from glob import glob
from subprocess import Popen, PIPE
from commons import *
from nose import with_setup

def setup_func():
    for report in glob("/tmp/sosreport*"):
        os.remove(report)
    
def teardown_func():
    for report in glob("/tmp/sosreport*"):
        os.remove(report)

def testSosreportBin():
    """ test existence of sosreport bin """
    if not os.path.isfile(commons['bin']):
        raise AssertionError("Sosreport executable does not exist")

# mostly sanity checks on plugins
@with_setup(setup_func, teardown_func)
def testUnattended():
    """ test batch mode """ 
    (out, err) = Popen([commons['bin'],'-ofilesys','--batch'],
                       stdout=PIPE,stderr=PIPE).communicate()
    output = out
    if not len(glob('/tmp/sosreport-*.bz2')):
        raise AssertionError("No sosreport created.")

@with_setup(setup_func, teardown_func)
def testUnattendedNameTicket():
    """ test for --name/--ticket within sosreport file """
    (out, err) = Popen([commons['bin'],'-ofilesys','--name=%s' % (commons['testName'],),
                       '--ticket-number=%d' % (commons['testID'],),'--batch'],stdout=PIPE,
                       stderr=PIPE).communicate()
    if not len(glob('/tmp/sosreport-%s.%d-*bz2' % (commons['testName'],commons['testID']))):
        raise AssertionError("Can not determine sosreport")

# plugin specific tests
