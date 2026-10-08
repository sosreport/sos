# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos_tests import StageTwoReportTest, redhat_only, debian_only


class NamedPluginTest(StageTwoReportTest):
    """Ensure that the named plugin collects runtime status and config
    syntax validation in addition to the static configuration.

    :avocado: tags=stagetwo
    """

    sos_cmd = '-o named'
    packages = {
        'rhel': ['bind'],
        'Ubuntu': ['bind9'],
        'debian': ['bind9'],
    }

    def test_plugin_ran(self):
        self.assertPluginIncluded('named')

    @redhat_only
    def test_keytab_not_collected(self):
        # added as a forbidden path by the plugin
        self.assertFileNotCollected('/etc/named.keytab')

    def test_rndc_status_collected(self):
        # collected whether or not named is running - a failed connection
        # is itself a diagnostic
        self.assertFileCollected('sos_commands/named/rndc_status')

    @redhat_only
    def test_redhat_checkconf_collected(self):
        self.assertFileCollected(
            'sos_commands/named/named-checkconf_.etc.named.conf')

    @debian_only
    def test_debian_checkconf_collected(self):
        self.assertFileCollected(
            'sos_commands/named/named-checkconf_.etc.bind.named.conf')


class NamedChrootPluginTest(StageTwoReportTest):
    """Ensure that chrooted BIND deployments have their config validated
    inside the chroot.

    :avocado: tags=stagetwo
    """

    sos_cmd = '-o named'
    packages = {
        'rhel': ['bind', 'bind-chroot'],
    }
    redhat_only = True

    def test_plugin_ran(self):
        self.assertPluginIncluded('named')

    def test_chroot_checkconf_collected(self):
        self.assertFileGlobInArchive(
            'sos_commands/named/named-checkconf_-t_.var.named.chroot_*')

    def test_chroot_dev_proc_not_collected(self):
        # both are added as forbidden paths by the plugin
        self.assertFileNotCollected('/var/named/chroot/dev')
        self.assertFileNotCollected('/var/named/chroot/proc')


# vim: set et ts=4 sw=4 :
