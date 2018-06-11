# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os


class Sar(Plugin,):
    """System Activity Reporter
    """

    plugin_name = 'sar'
    profiles = ('system', 'performance')

    packages = ('sysstat',)
    sa_path = '/var/log/sa'
    option_list = [("all_sar", "gather all system activity records",
                    "", False)]

    # size-limit SAR data collected by default (MB)
    sa_size = 20

    def setup(self):
        if self.get_option("all_sar"):
            self.sa_size = 0

        # Copy all sa??, sar??, sa??.* and sar??.* files, which will net
        # compressed and uncompressed versions, typically.
        for suffix in ('', '.*'):
            self.add_copy_spec(
                os.path.join(self.sa_path, "sa[0-3][0-9]" + suffix),
                sizelimit=self.sa_size, tailit=False
            )
            self.add_copy_spec(
                os.path.join(self.sa_path, "sar[0-3][0-9]" + suffix),
                sizelimit=self.sa_size, tailit=False
            )

        try:
            dir_list = os.listdir(self.sa_path)
        except OSError:
            self._log_warn("sar: could not list %s" % self.sa_path)
            return
        # find all the sa files that don't have an existing sar file
        for fname in dir_list:
            if fname.startswith('sar'):
                continue
            if not fname.startswith('sa'):
                continue
            if len(fname) != 4:
                # We either have an "sa" or "sa?" file, or more likely, a
                # compressed data file like, "sa??.xz".
                #
                # FIXME: We don't have a detector for the kind of compression
                # use for this file right now, so skip these kinds of files.
                continue
            sa_data_path = os.path.join(self.sa_path, fname)
            sar_filename = 'sar' + fname[2:]
            if sar_filename not in dir_list:
                sar_cmd = 'sh -c "sar -A -f %s"' % sa_data_path
                self.add_cmd_output(sar_cmd, sar_filename)
            sadf_cmd = "sadf -x %s" % sa_data_path
            self.add_cmd_output(sadf_cmd, "%s.xml" % fname)


class RedHatSar(Sar, RedHatPlugin):

    sa_path = '/var/log/sa'


class DebianSar(Sar, DebianPlugin, UbuntuPlugin):

    sa_path = '/var/log/sysstat'

# vim: set et ts=4 sw=4 :
