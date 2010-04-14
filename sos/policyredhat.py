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
import sys
import string
from tempfile import gettempdir
from sos.helpers import *
import random
import re
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import rpm
import time
from subprocess import Popen, PIPE
from collections import deque
from sos import _sos as _

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
        self.report_file_ext = ""
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
        p = Popen("LC_ALL=C /sbin/chkconfig --list %s" % name, shell=True, stdout=PIPE, stderr=PIPE, bufsize=-1)
        out, err = p.communicate() 
        if err:
            return ret
        for tabs in out.split()[1:]:
            try:
                (runlevel, onoff) = tabs.split(":", 1)
            except:
                pass
            else:
                if onoff == "on":
                    ret.append(int(runlevel))
        return ret

    def runlevelDefault(self):
        try:
            reg=self.doRegexFindAll(r"^id:(\d{1}):initdefault:", "/etc/inittab")
            for initlevel in reg:
                return initlevel
        except:
            return 3

    def kernelVersion(self):
        return Popen("/bin/uname -r", shell=True, stdout=PIPE, bufsize=-1).stdout.read().strip("\n")

    def hostName(self):
        return Popen("/bin/hostname", shell=True, stdout=PIPE, bufsize=-1).stdout.read().strip("\n").split(".")[0]

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
        pipe = Popen("/bin/hostname", shell=True, stdout=PIPE, bufsize=-1).read().stdout
        if pipe.split()[1] == "SMP":
            return True
        else:
            return False

    def getArch(self):
        return Popen("/bin/uname -m", shell=True, stdout=PIPE, bufsize=-1).stdout.read().strip()

    def pkgNVRA(self, pkg):
        fields = pkg.split("-")
        version, release, arch = fields[-3:]
        name = "-".join(fields[:-3])
        return (name, version, release, arch)

    def getDstroot(self, tmpdir='/tmp'):
        """Find a temp directory to form the root for our gathered information
           and reports.
        """
        uniqname = "%s-%s" % (self.hostName(), time.strftime("%Y%m%d%H%M%s"))
        dstroot = os.path.join(tmpdir,uniqname)
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
        
        if self.cInfo['cmdlineopts'].customerName:
            self.reportName = self.cInfo['cmdlineopts'].customerName        
            self.reportName = re.sub(r"[^a-zA-Z.0-9]", "", self.reportName)

        if self.cInfo['cmdlineopts'].ticketNumber:
            self.ticketNumber = self.cInfo['cmdlineopts'].ticketNumber
            self.ticketNumber = re.sub(r"[^0-9]", "", self.ticketNumber)

        return

    def renameResults(self, newName):
        newName = os.path.join(gettempdir(), newName)
        if len(self.report_file) and os.path.isfile(self.report_file):
            try:    
                os.rename(self.report_file, newName)
            except:
                return False
        self.report_file = newName

    def packageResults(self):

        if len(self.ticketNumber):
            self.reportName = self.reportName + "." + self.ticketNumber
        else:
            self.reportName = self.reportName

        curwd = os.getcwd()
        os.chdir(os.path.dirname(self.cInfo['dstroot']))
        oldmask = os.umask(077)

        print _("Creating compressed archive...")

        if os.path.isfile("/usr/bin/xz"):
            self.report_file_ext = "tar.xz"
            self.renameResults("sosreport-%s-%s.%s" % (self.reportName, time.strftime("%Y%m%d%H%M%S"), self.report_file_ext))
            cmd = "/bin/tar -c %s | /usr/bin/xz -1 > %s" % (os.path.basename(self.cInfo['dstroot']),self.report_file)
            p = Popen(cmd, shell=True, bufsize=-1)
            sts = os.waitpid(p.pid, 0)[1]
        else:
            self.report_file_ext = "tar.bz2"
            self.renameResults("sosreport-%s-%s.%s" % (self.reportName, time.strftime("%Y%m%d%H%M%S"), self.report_file_ext))
            tarcmd = "/bin/tar -jcf %s %s" % (self.report_file, os.path.basename(self.cInfo['dstroot']))
            p = Popen(tarcmd, shell=True, stdout=PIPE, stderr=PIPE, bufsize=-1)
            output = p.communicate()[0]

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

        p = Popen("""/usr/bin/gpg --trust-model always --batch --keyring "%s" --no-default-keyring --compress-level 0 --encrypt --recipient "%s" --output "%s" "%s" """ % (keyring, recipient, gpgname, self.report_file),
                    shell=True, stdout=PIPE, stderr=PIPE, bufsize=-1)
        stdout, stderr = p.communicate()
        if p.returncode == 0:
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
        self.report_md5 = md5(fp.read()).hexdigest()
        fp.close()

        self.renameResults("sosreport-%s-%s-%s.%s" % (self.reportName, 
                                                          time.strftime("%Y%m%d%H%M%S"),
                                                          self.report_md5[-4:], 
                                                          self.report_file_ext))

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
        if self.cInfo['cmdlineopts'].upload:
            upload_url = self.cInfo['cmdlineopts'].upload
        else:
            try:
               upload_url = self.cInfo['config'].get("general", "ftp_upload_url")
            except:
               print _("No URL defined in config file.")
               return

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
            print _("Your report was successfully uploaded to %s with name:" % (upload_url,))
            print "  " + upload_name
            print
            print _("Please communicate this name to your support representative.")
            print

        fp.close()

# vim: ts=4 sw=4 et
