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

    def allPkgsByName(self, name):
        # FIXME: we're relying on rpm to sort the output list
        cmd = "/bin/rpm --qf '%%{N}-%%{V}-%%{R}-%%{ARCH}\n' -q %s" % (name,)
        pkgs = os.popen(cmd).readlines()
        return [pkg[:-1] for pkg in pkgs if pkg.startswith(name)]

    def pkgByName(self, name):
        # TODO: do a full NEVRA compare and return newest version, best arch
        try:
            # lame attempt at locating newest
            pkg = self.allPkgsByName(name)[-1]
        except IndexError:
            pkg = None

        return pkg

    def pkgNVRA(self, pkg):
        fields = pkg.split("-")
        version, release, arch = fields[-3:]
        name = "-".join(fields[:-3])
        return (name, version, release, arch)

    def packageResults(self):
        print "Packaging reults to send to support . . ."

        print "Please enter your first initial and last name (jsmith): ",
        name = sys.stdin.readline()[:-1]

        print "Please enter the case number that you are generating this",
        print "report for: ",
        ticketNumber = sys.stdin.readline()[:-1]

        namestr = name + "." + ticketNumber
        ourtempdir = gettempdir()
        tarballName = os.path.join(ourtempdir,  namestr + ".tar.bz2")

        aliasdir = os.path.join(ourtempdir, namestr)

        tarcmd = "/bin/tar -jcf %s %s" % (tarballName, namestr)

        print "Creating tar file . . ."
        if not os.access(string.split(tarcmd)[0], os.X_OK):
            print "Unable to create tarball"
            return

        # gotta be a better way . . .
        os.system("/bin/mv %s %s" % (self.cInfo['dstroot'], aliasdir))
        curwd = os.getcwd()
        os.chdir(ourtempdir)
        oldmask = os.umask(077)
        # pylint: disable-msg = W0612
        status, shout, sherr = sosGetCommandOutput(tarcmd)
        os.umask(oldmask)
        os.chdir(curwd)
        os.system("/bin/mv %s %s" % (aliasdir, self.cInfo['dstroot']))

	print "Your tarball is located at %s" % tarballName
        return
        
