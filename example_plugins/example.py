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

from sos.plugins import Plugin, RedHatPlugin

# the class name determines the plugin name
# if you want to override it simply provide a @classmethod name()
# that returns the name you want
class example(Plugin, RedHatPlugin):
    '''This is the description for the example plugin'''
    # Plugin developers want to override setup() from which they will call
    # add_copy_spec() to collect files and collectExtOutput() to collect programs
    # output.

    # Add your options here, indicate whether they are slow to run, and set
    # whether they are enabled by default
    # each option is a tuple of the following format:
    # (name, description, fast or slow, default value)
    # each option will be addressable like -k name=value
    option_list = [("init.d",  'Gathers the init.d directory', 'slow', 0),
                  ('follicles', 'Gathers information about each follicle on every toe', 'slow', 0),
                  ('color', 'Gathers toenail polish color', 'fast', 0)]

    def setup(self):
        ''' First phase - Collect all the information we need.
        Directories are copied recursively. arbitrary commands may be
        executed using the collectExtOutput() method. Information is
        automatically saved, and links are presented in the report to each
        file or directory which has been copied to the saved tree. Also, links
        are provided to the output from each command.
        '''
        # Here's how to copy files and directory trees
        self.add_copy_spec("/etc/hosts")

        with open("/proc/cpuinfo") as f:
            for line in f:
                if "vendor_id" in line:
                    self.add_alert("Vendor ID string is: %s <br>\n" % line)

        # Here's how to test your options and execute if enabled
        if self.option_enabled("init.d"):
            self.add_copy_spec("/etc/init.d") # copies a whole directory tree

        # Here's how to execute a command
        self.collectExtOutput("/bin/ps -ef")


# vim: set et ts=4 sw=4 :
