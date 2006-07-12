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

#import os.path
#import copy
#import md5
import os

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

