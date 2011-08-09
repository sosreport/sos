'''
Created on Aug 2, 2011
@author: Keith Robertson
'''

import pprint
import os
import re

class OSTypes:
    """
    Utility class with enumerations for the various OSes to facilitate 
    OS detection.    
    """
    JAVA_OS_NAME_KEY='os.name'
    
    OS_TYPE_LINUX='Linux'
    OS_TYPE_LINUX_PAT=re.compile('^%s$' % OS_TYPE_LINUX, re.I)
    OS_TYPE_WIN='Windows'
    OS_TYPE_WIN_PAT=re.compile('^%s$' % OS_TYPE_WIN, re.I)
    OS_TYPE_AIX='AIX'
    OS_TYPE_AIX_PAT=re.compile('^%s$' % OS_TYPE_AIX, re.I)
    OS_TYPE_MAC='Mac OS'
    OS_TYPE_MAC_PAT=re.compile('^%s$' % OS_TYPE_MAC, re.I)
    OS_TYPE_390='OS/390'
    OS_TYPE_390_PAT=re.compile('^%s$' % OS_TYPE_390, re.I)
    OS_TYPE_HPUX='HP-UX'
    OS_TYPE_HPUX_PAT=re.compile('^%s$' % OS_TYPE_HPUX, re.I)

def printProps():
    try:
        from java.lang import System
        from java.util import Set
        from java.util import Iterator
        
        set = System.getProperties().entrySet()
        it = set.iterator()
        while it.hasNext():
            me = it.next();        
            print "Key (%s) Value(%s)" % (me.getKey(), me.getValue())
    except Exception, e:
        print "ERROR: unable to print Java properties %s" % e

    

def java_detect_os():
    """
    Try to load Java packages.  If successful then we know we are running
    in JYthon.  Use the JRE to determine what type of OS and return the proper 
    policy.
    """
    try:
        from java.lang import System
        
        ostype = System.getProperty(OSTypes.JAVA_OS_NAME_KEY)
        if ostype:
            if OSTypes.OS_TYPE_LINUX_PAT.match(ostype):
                print "Matched %s" % OSTypes.OS_TYPE_LINUX
                # Lots of checks here to determine linux version.
                #return proper policy here
            elif OSTypes.OS_TYPE_WIN_PAT.match(ostype):
                print "Matched %s" % OSTypes.OS_TYPE_WIN
            elif OS_TYPE_AIX_PAT.match(ostype):
                print "Matched %s" % OSTypes.OS_TYPE_AIX
            elif OS_TYPE_MAC_PAT.match(ostype):
                print "Matched %s" % OSTypes.OS_TYPE_MAC
            elif OS_TYPE_390_PAT.match(ostype):
                print "Matched %s" % OSTypes.OS_TYPE_390
            elif OS_TYPE_HPUX_PAT.match(ostype):
                print "Matched %s" % OSTypes.OS_TYPE_HPUX
            else:
                raise Exception("Unsupported OS type of %s." % ostype)                                  
        else:
            raise Exception("Unable to get %s from JRE's system properties." % OSTypes.JAVA_OS_NAME_KEY)            
    except Exception, e:
        print "WARN: unable to print Java properties %s" % e
        
def native_detect_os():
    print "here" 
        
    

if __name__ == '__main__':
    #printProps()
    detectOS()
    
    pass