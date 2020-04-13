# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin

# the class name determines the plugin name
# if you want to override it simply provide a @classmethod name()
# that returns the name you want
class example(Plugin, RedHatPlugin):
    """This is the description for the example plugin"""
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
        """ First phase - Collect all the information we need.
        Directories are copied recursively. arbitrary commands may be
        executed using the collectExtOutput() method. Information is
        automatically saved, and links are presented in the report to each
        file or directory which has been copied to the saved tree. Also, links
        are provided to the output from each command.
        """
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
