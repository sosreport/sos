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

from sos.plugins import Plugin, UbuntuPlugin

class Landscape(Plugin, UbuntuPlugin):
    """
    landscape client related information
    """

    files = ('/etc/landscape/client.conf',
            'broker.log',
            'broker.log.gz',
            'broker.log.1',
            'broker.log.1.gz',
            'broker.log.2',
            'broker.log.2.gz',
            'manager.log',
            'manager.log.gz',
            'manager.log.1',
            'manager.log.1.gz',
            'manager.log.2',
            'manager.log.2.gz',
            'monitor.log',
            'monitor.log.gz',
            'monitor.log.1',
            'monitor.log.1.gz',
            'monitor.log.2',
            'monitor.log.2.gz',
            'package-reporter.log',
            'package-reporter.log.gz',
            'package-reporter.log.1',
            'package-reporter.log.1.gz',
            'package-reporter.log.2',
            'package-reporter.log.2.gz',
            'sysinfo.log',
            'sysinfo.log.gz',
            'sysinfo.log.1',
            'sysinfo.log.1.gz',
            'sysinfo.log.2',
            'sysinfo.log.2.gz',
            'watchdog.log',
            'watchdog.log.gz',
            'watchdog.log.1',
            'watchdog.log.1.gz',
            'watchdog.log.2',
            'watchdog.log.2.gz'
            ,)
    packages = ('landscape-client',)

    def setup(self):
        self.addCopySpec("/etc/landscape/client.conf")
        
    def postproc(self):
        self.doFileSub("/etc/landscape/client.conf", 
        r"registration_password(.*)", 
        r"registration_password[***]"
        )
        
                                                    
