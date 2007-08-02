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

SOME_PATH = "/tmp/SomePath"

#class SosError(Exception):
#    def __init__(self, code, message):
#        self.code = code
#        self.message = message
#    
#    def __str__(self):
#        return 'Sos Error %s: %s' % (self.code, self.message)


class SosPolicy:
    "This class implements various policies for sos"
    def __init__(self):
        #print "Policy init"
        return

    def setCommons(self, commons):
        self.cInfo = commons
        return

    def validatePlugin(self, pluginpath):
        "Validates the plugin as being acceptable to run"
        # return value
        # TODO implement this
        #print "validating %s" % pluginpath
        return True

    def pkgRequires(self, name):
        # FIXME: we're relying on rpm to sort the output list
        cmd = "/bin/rpm -q --requires %s" % (name)
        return [requires[:-1].split() for requires in os.popen(cmd).readlines()]

    def allPkgsByName(self, name):
        # FIXME: we're relying on rpm to sort the output list
        cmd = "/bin/rpm --qf '%%{N} %%{V} %%{R} %%{ARCH}\n' -q %s" % (name,)
        pkgs = os.popen(cmd).readlines()
        return [pkg[:-1].split() for pkg in pkgs if pkg.startswith(name)]

    def pkgByName(self, name):
        # TODO: do a full NEVRA compare and return newest version, best arch
        try:
            # lame attempt at locating newest
            pkg = self.allPkgsByName(name)[-1]
        except IndexError:
            pkg = None

        return pkg

    def pkgDictByName(self, name):
        pkgName = self.pkgByName(name)
        if pkgName and len(pkgName) > len(name):
           return pkgName[len(name)+1:].split("-")
        else:
           return None

    def runlevelByService(self, name):
        ret = []
        try:
           for tabs in commands.getoutput("/sbin/chkconfig --list %s" % name).split():
              (runlevel, onoff) = tabs.split(":")
              if onoff == "on":
                 ret.append(int(runlevel))
        except:
           pass
        return ret

    def runlevelDefault(self):
        try:
            f=open("/etc/inittab",'r')
            content=f.read()
            f.close()
            reg=re.compile(r"^id:(\d{1}):initdefault:\D",re.MULTILINE)
            for initlevel in reg.findall(content):
                return initlevel
        except:
            return 3

    def kernelVersion(self):
        return commands.getoutput("/bin/uname -r").strip("\n")

    def isKernelSMP(self):
        if self.kernelVersion()[-3:]=="smp": return True
        else: return False

    def pkgNVRA(self, pkg):
        fields = pkg.split("-")
        version, release, arch = fields[-3:]
        name = "-".join(fields[:-3])
        return (name, version, release, arch)

    def preWork(self):
        # this method will be called before the gathering begins

        localname = commands.getoutput("/bin/uname -n").split(".")[0]

        try:
            self.reportName = raw_input("Please enter your first initial and last name [%s]: " % localname)
            self.reportName = re.sub(r"[^a-zA-Z.0-9]", "", self.reportName)
            if len(self.reportName) == 0:
                self.reportName = localname

            self.ticketNumber = raw_input("Please enter the case number that you are generating this report for: ")
            self.ticketNumber = re.sub(r"[^0-9]", "", self.ticketNumber)
            print
        except KeyboardInterrupt:
            print
            sys.exit(0)

    def packageResults(self):

        if len(self.ticketNumber):
            namestr = self.reportName + "." + self.ticketNumber
        else:
            namestr = self.reportName

        ourtempdir = gettempdir()
        tarballName = os.path.join(ourtempdir,  "sosreport-" + namestr + ".tar.bz2")

        namestr = namestr + "-" + str(random.randint(1, 999999))

        aliasdir = os.path.join(ourtempdir, namestr)

        tarcmd = "/bin/tar -jcf %s %s" % (tarballName, namestr)

        print "Creating compressed archive..."
        if not os.access(string.split(tarcmd)[0], os.X_OK):
            print "Unable to create tarball"
            return

        # FIXME: gotta be a better way...
        os.system("/bin/mv %s %s" % (self.cInfo['dstroot'], aliasdir))
        curwd = os.getcwd()
        os.chdir(ourtempdir)
        oldmask = os.umask(077)
        # pylint: disable-msg = W0612
        status, shout, runtime = sosGetCommandOutput(tarcmd)
        os.umask(oldmask)
        os.chdir(curwd)
        # FIXME: use python internal command
        os.system("/bin/mv %s %s" % (aliasdir, self.cInfo['dstroot']))

        # add last 6 chars from md5sum to file name
        fp = open(tarballName, "r")
        md5out = md5.new(fp.read()).hexdigest()
        fp.close()
        oldtarballName = tarballName
        tarballName = os.path.join(ourtempdir, "sosreport-%s-%s.tar.bz2" % (namestr, md5out[-6:]) )
        os.system("/bin/mv %s %s" % (oldtarballName, tarballName) )
        # store md5 to a file
        fp = open(tarballName + ".md5", "w")
        fp.write(md5out + "\n")
        fp.close()

        sys.stdout.write("\n")
        print "Your sosreport has been generated and saved in:\n  %s" % tarballName
        print
        if md5out:
            print "The md5sum is: " + md5out
            print
        print "Please send this file to your support representative."
        sys.stdout.write("\n")

        return
        
