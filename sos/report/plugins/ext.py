# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Ext(Plugin, IndependentPlugin):
    """This plugin collects information on mounted Ext2/3/4 filessystems on
    the local system.

    Users should expect `dumpe2fs -h` or `dumpe2fs` collections by this
    plugin for each Ext2/3/4 filesystem that is recognized by lsblk.
    """

    short_desc = 'Ext2/3/4 filesystem'

    plugin_name = 'ext'
    profiles = ('storage',)
    files = ('/sys/fs/ext4/', '/proc/fs/ext4/', '/proc/fs/jbd2/')

    option_list = [
        PluginOpt('dumpe2fs', default=False, desc='dump filesystem info'),
        PluginOpt('frag', default=False,
                  desc='collect filesystem fragmentation status')
    ]

    def setup(self):
        dumpe2fs_opts = '-h'
        if self.get_option('dumpe2fs'):
            dumpe2fs_opts = ''
        allfs = self.get_devices_by_fstype('ext')
        if allfs:
            for fs in allfs:
                self.add_cmd_output(f"dumpe2fs {dumpe2fs_opts} {fs}",
                                    tags="dumpe2fs_h")

                if self.get_option('frag'):
                    self.add_cmd_output(f"e2freefrag {fs}", priority=100)

        else:
            mounts = '/proc/mounts'
            ext_fs_regex = r"^(/dev/\S+).+ext[234]\s+"
            for dev in self.do_regex_find_all(ext_fs_regex, mounts):
                self.add_cmd_output(f"dumpe2fs {dumpe2fs_opts} {fs}",
                                    tags="dumpe2fs_h")

            if self.get_option('frag'):
                self.add_cmd_output(f"e2freefrag {fs}", priority=100)

        self.add_copy_spec(self.files)

# vim: set et ts=4 sw=4 :
