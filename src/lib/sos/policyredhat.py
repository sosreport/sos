## policy-redhat.py
## Implement policies required for the sos system support tool

## Copyright (C) Steve Conklin <sconklin@redhat.com>

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

import os
import commands
import sys
import string
from tempfile import gettempdir
from sos.helpers import *
import random
import re
import md5
import rpm
import time

sys.path.insert(0, "/usr/share/rhn/")
try:
    from up2date_client import up2dateAuth
    from up2date_client import config
    from rhn import rpclib
except:
    # might fail if non-RHEL
    pass

#class SosError(Exception):
#    def __init__(self, code, message):
#        self.code = code
#        self.message = message
#    
#    def __str__(self):
#        return 'Sos Error %s: %s' % (self.code, self.message)

def memoized(function):
    ''' function decorator to allow caching of return values
    '''
    function.cache={}
    def f(*args):
        try:
            return function.cache[args]
        except KeyError:
            result = function.cache[args] = function(*args)
            return result
    return f

class SosPolicy:
    "This class implements various policies for sos"
    def __init__(self):
        self.report_file = ""
        self.report_md5 = ""
        self.reportName = ""
        self.ticketNumber = ""

    def setCommons(self, commons):
        self.cInfo = commons
        return

    def validatePlugin(self, pluginpath):
        "Validates the plugin as being acceptable to run"
        # return value
        # TODO implement this
        #print "validating %s" % pluginpath
        return True

    def pkgProvides(self, name):
        return self.pkgByName(name).get('providename')

    def pkgRequires(self, name):
        return self.pkgByName(name).get('requirename')

    def allPkgsByName(self, name):
        return self.allPkgs("name", name)

    def allPkgsByNameRegex(self, regex_name):
        reg = re.compile(regex_name)
        return [pkg for pkg in self.allPkgs() if reg.match(pkg['name'])]

    def pkgByName(self, name):
        # TODO: do a full NEVRA compare and return newest version, best arch
        try:
            # lame attempt at locating newest
            return self.allPkgsByName(name)[-1]
        except:
            pass
        return {}

    def allPkgs(self, ds = None, value = None):
        # if possible return the cached values
        try:                   return self._cache_rpm[ "%s-%s" % (ds,value) ]
        except AttributeError: self._cache_rpm = {}
        except KeyError:       pass

        ts = rpm.TransactionSet()
        if ds and value:
            mi = ts.dbMatch(ds, value)
        else:
            mi = ts.dbMatch()

        self._cache_rpm[ "%s-%s" % (ds,value) ] = [pkg for pkg in mi]
        del mi, ts
        return self._cache_rpm[ "%s-%s" % (ds,value) ]

    def runlevelByService(self, name):
        ret = []
        try:
           for tabs in commands.getoutput("/sbin/chkconfig --list %s" % name).split():
              try:
                 (runlevel, onoff) = tabs.split(":", 1)
              except:
                 pass
              else:
                 if onoff == "on":
                    ret.append(int(runlevel))
        except:
           pass
        return ret

    def runlevelDefault(self):
        try:
            reg=self.doRegexFindAll(r"^id:(\d{1}):initdefault:", "/etc/inittab")
            for initlevel in reg:
                return initlevel
        except:
            return 3

    def kernelVersion(self):
        return commands.getoutput("/bin/uname -r").strip("\n")

    def hostName(self):
        return commands.getoutput("/bin/hostname").split(".")[0]

    def rhelVersion(self):
        try:
            pkgname = self.pkgByName("redhat-release")["version"]
            if pkgname[0] == "4":
                return 4
            elif pkgname in [ "5Server", "5Client" ]:
                return 5
        except: pass
        return False

    def rhnUsername(self):
        try:
            cfg = config.initUp2dateConfig()

            return rpclib.xmlrpclib.loads(up2dateAuth.getSystemId())[0][0]['username']
        except:
            # ignore any exception and return an empty username
            return ""

    def isKernelSMP(self):
        if commands.getoutput("/bin/uname -v").split()[1] == "SMP":
            return True
        else:
            return False

    def getArch(self):
        return commands.getoutput("/bin/uname -m").strip()

    def pkgNVRA(self, pkg):
        fields = pkg.split("-")
        version, release, arch = fields[-3:]
        name = "-".join(fields[:-3])
        return (name, version, release, arch)

    def getDstroot(self):
        """Find a temp directory to form the root for our gathered information
           and reports.
        """
        dstroot = "/tmp/%s-%s" % (self.hostName(), time.strftime("%Y%m%d%H%M%S"))
        try:
            os.mkdir(dstroot, 0700)
        except:
            return False
        return dstroot

    def preWork(self):
        # this method will be called before the gathering begins

        localname = self.rhnUsername()
        if len(localname) == 0: localname = self.hostName()

        if not self.cInfo['cmdlineopts'].batch:
            try:
                self.reportName = raw_input(_("Please enter your first initial and last name [%s]: ") % localname)
                self.reportName = re.sub(r"[^a-zA-Z.0-9]", "", self.reportName)

                self.ticketNumber = raw_input(_("Please enter the case number that you are generating this report for: "))
                self.ticketNumber = re.sub(r"[^0-9]", "", self.ticketNumber)
                print
            except:
                print
                sys.exit(0)

        if len(self.reportName) == 0:
            self.reportName = localname

        return

    def renameResults(self, newName):
        newName = os.path.join(gettempdir(), newName)
        if len(self.report_file) and os.path.isfile(self.report_file):
            try:    os.rename(self.report_file, newName)
            except: return False
        self.report_file = newName

    def packageResults(self):

        self.renameResults("sosreport-%s-%s.tar.bz2" % (self.reportName, time.strftime("%Y%m%d%H%M%S")))

        tarcmd = "/bin/tar -jcf %s %s" % (self.report_file, os.path.basename(self.cInfo['dstroot']))

        print _("Creating compressed archive...")

        curwd = os.getcwd()
        os.chdir(os.path.dirname(self.cInfo['dstroot']))
        oldmask = os.umask(077)
        status, shout = commands.getstatusoutput(tarcmd)
        os.umask(oldmask)
        os.chdir(curwd)

        return

    def cleanDstroot(self):
        if not os.path.isdir(os.path.join(self.cInfo['dstroot'],"sos_commands")):
            # doesn't look like a dstroot, refusing to clean
            return False
        os.system("/bin/rm -rf %s" % self.cInfo['dstroot'])

    def encryptResults(self):
        # make sure a report exists
        if not self.report_file:
           return False

        print _("Encrypting archive...")
        gpgname = self.report_file + ".gpg"

        try:
           keyring = self.cInfo['config'].get("general", "gpg_keyring")
        except:
           keyring = "/usr/share/sos/rhsupport.pub"

        try:
           recipient = self.cInfo['config'].get("general", "gpg_recipient")
        except:
           recipient = "support@redhat.com"

        status, output = commands.getstatusoutput("""/usr/bin/gpg --trust-model always --batch --keyring "%s" --no-default-keyring --compress-level 0 --encrypt --recipient "%s" --output "%s" "%s" """ % (keyring, recipient, gpgname, self.report_file))
        if status == 0:
            os.unlink(self.report_file)
            self.report_file = gpgname
        else:
           print _("There was a problem encrypting your report.")
           sys.exit(1)

    def displayResults(self):
        # make sure a report exists
        if not self.report_file:
           return False

        # calculate md5
        fp = open(self.report_file, "r")
        self.report_md5 = md5.new(fp.read()).hexdigest()
        fp.close()

        self.renameResults("sosreport-%s-%s-%s.tar.bz2" % (self.reportName, time.strftime("%Y%m%d%H%M%S"), self.report_md5[-4:]))

        # store md5 into file
        fp = open(self.report_file + ".md5", "w")
        fp.write(self.report_md5 + "\n")
        fp.close()

        print
        print _("Your sosreport has been generated and saved in:\n  %s") % self.report_file
        print
        if len(self.report_md5):
            print _("The md5sum is: ") + self.report_md5
            print
        print _("Please send this file to your support representative.")
        print

    def uploadResults(self):
        # make sure a report exists
        if not self.report_file:
           return False

        print

        # make sure it's readable
        try:
           fp = open(self.report_file, "r")
        except:
           return False

        # read ftp URL from configuration
        try:
           upload_url = self.cInfo['config'].get("general", "upload_url")
        except:
           upload_url = "ftp://dropbox.redhat.com/incoming"

        from urlparse import urlparse
        url = urlparse(upload_url)

        if url[0] != "ftp":
           print _("Cannot upload to specified URL.")
           return

        # extract username and password from URL, if present
        if url[1].find("@") > 0:
           username, host = url[1].split("@", 1)
           if username.find(":") > 0:
              username, passwd = username.split(":", 1)
           else:
              passwd = None
        else:
           username, passwd, host = None, None, url[1]

        # extract port, if present
        if host.find(":") > 0:
           host, port = host.split(":", 1)
           port = int(port)
        else:
           port = 21

        path = url[2]

        try:
           from ftplib import FTP
           upload_name = os.path.basename(self.report_file)

           ftp = FTP()
           ftp.connect(host, port)
           if username and passwd:
              ftp.login(username, passwd)
           else:
              ftp.login()
           ftp.cwd(path)
           ftp.set_pasv(True)
           ftp.storbinary('STOR %s' % upload_name, fp)
           ftp.quit()
        except:
           print _("There was a problem uploading your report to Red Hat support.")
        else:
           print _("Your report was successfully uploaded to Red Hat's ftp server with name:")
           print "  " + upload_name
           print
           print _("Please communicate this name to your support representative.")
           print

        fp.close()
