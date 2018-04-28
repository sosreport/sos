# Copyright (C) 2018 Brian Gribble <bgribble@redhat.com>, Red Hat.
# All rights reserved.
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions
# of the version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further
# information.

from sos.plugins import Plugin, RedHatPlugin
from os.path import exists
from glob import glob
import os


class CertificateSystem(Plugin, RedHatPlugin):
    """ Certificate System and Dogtag
    """

    plugin_name = 'cs'
    profiles = ('identity', 'security')

    packages = (
        'redhat-cs',
        'rhpki-common',
        'pki-common',
        'pki-base'
    )

    files = (
        '/opt/redhat-cs',
        '/usr/share/java/rhpki',
        '/usr/share/java/pki'
    )

    def checkversion(self):
        """ Check if Certificate System 7, 8, or 9 is installed.
        """

        if self.is_installed('redhat-cs') or exists('/opt/redhat-cs'):
            return 71
        elif self.is_installed('rhpki-common') or \
                len(glob('/var/lib/rhpki-*')):
            return 73
        # 8 should cover Dogtag.
        elif self.is_installed('pki-common'):
            return 8
        # pki-base is the common package for 9.
        elif self.is_installed('pki-base'):
            return 9
        return False

    def setup(self):
        csversion = self.checkversion()

        if not csversion:
            self.add_alert('Red Hat Certificate System not found.')
            return
        if csversion == 71:
            self.add_copy_spec([
                '/opt/redhat-cs/slapd-*/logs/access',
                '/opt/redhat-cs/slapd-*/logs/errors',
                '/opt/redhat-cs/slapd-*/config/dse.ldif',
                '/opt/redhat-cs/cert-*/errors',
                '/opt/redhat-cs/cert-*/config/CS.cfg',
                '/opt/redhat-cs/cert-*/access',
                '/opt/redhat-cs/cert-*/errors',
                '/opt/redhat-cs/cert-*/system',
                '/opt/redhat-cs/cert-*/transactions',
                '/opt/redhat-cs/cert-*/debug',
                '/opt/redhat-cs/cert-*/tps-debug.log'
            ])
        if csversion == 73:
            self.add_copy_spec([
                '/var/lib/rhpki-*/conf/*cfg*',
                '/var/lib/rhpki-*/conf/*.ldif',
                '/var/lib/rhpki-*/logs/debug',
                '/var/lib/rhpki-*/logs/catalina.*',
                '/var/lib/rhpki-*/logs/ra-debug.log',
                '/var/lib/rhpki-*/logs/transactions',
                '/var/lib/rhpki-*/logs/system'
            ])
        if csversion == 8:
            self.add_copy_spec([
                '/var/lib/pki-*/conf/*cfg*',
                '/var/log/pki-*/debug',
                '/var/log/pki-*/catalina.*',
                '/var/log/pki-*/localhost.*',
                '/var/log/pki-*/manager.*',
                '/var/log/pki-*/ra-debug.log',
                '/var/log/pki-*/transactions',
                '/var/log/pki-*/selftests.log',
                '/var/log/pki-*/system'
            ])
        if csversion == 9:
            for dirs in os.listdir('/var/lib/pki'):

                # Files containing sensitive information.
                self.add_forbidden_path('/etc/pki/%s/password.conf'
                                        % dirs)
                self.add_forbidden_path('/etc/pki/%s/alias/key3.db'
                                        % dirs)

                # Get certificates from CA.
                try:
                    certpath = os.path.join('/var/lib/pki', dirs)
                    self.add_cmd_output('certutil -L -d %s/alias'
                                        % certpath)
                except:
                    self._log_warn('Could not list /var/lib/pki')

                # Grab logs and configs for each subsystem.
                self.add_copy_spec([
                    '/var/lib/pki/' + dirs,
                    '/etc/pki/' + dirs,
                    '/var/log/pki/' + dirs,
                    '/var/log/pki/pki-*-spawn.*'
                ])

    # Obfuscate passwords in CS 9 tomcat files.
    def postproc(self):
        for dirs in os.listdir('/var/lib/pki'):
            serverXmlPasswordAttributes = ['keyPass', 'keystorePass',
                                           'truststorePass', 'SSLPassword']
            for attr in serverXmlPasswordAttributes:
                self.do_path_regex_sub(
                    r'\/etc\/pki\/' + dirs + '\/server.xml',
                    r'%s=(\S*)' % attr,
                    r'%s="********"' % attr
                )
            self.do_path_regex_sub(
                r'\/etc\/pki\/' + dirs + '\/tomcat-users.xml',
                r'password=(\S*)',
                r'password="********"'
            )

# vim: set et ts=4 sw=4 :
