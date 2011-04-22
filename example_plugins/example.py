## example.py
## An example sos plugin

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

import sos.plugintools

# Class name must be the same as file name and method names must not change
class example(sos.plugintools.PluginBase):
    '''dummy example plugin'''
    # Plugin developers want to override setup() from which they will call
    # addCopySpec() to collect files and collectExtOutPut() to collect programs
    # output.
    # If you want to go fancy you may also want to override diagnose(),
    # analyze() and postproc(). Have a look at the PluginBase definition
    # for details.

    # Add your options here, indicate whether they are slow to run, and set
    # whether they are enabled by default
    # Options are python dictionaries that contain a short name,
    # long description, speed, and whether they are enabled by default
    optionList = [("init.d",  'Gathers the init.d directory', 'slow', 0),
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
        self.addCopySpec("/etc/hosts")
        # this one saves a file path to the copy for later analysis
        # FIXME: Need to figure out how to do this
        # self.fooFilePath = self.copyFileOrDir("/proc/cpuinfo")

        # Here's how to test your options and execute if enabled
        if self.isOptionEnabled("init.d"):
            self.addCopySpec("/etc/init.d") # copies a whole directory tree

        # Here's how to execute a command
        # you can save the path to the copied file for later analysis if desired
        # FIXME: Need to figure out how to do this
        self.psCmdDstFileName = self.collectExtOutput("/bin/ps -ef")
        return

    def analyze(self):
        ''' This is optional and need not be defined.
        If you wish to perform some analysis on either files
        that were gathered or on the output of commands, then save the filenames on the
        destination file system when gathering that information in the setup() method
        and use them here
        '''
        # This is an example of opening and reading the output of a command that
        # was run in the collect() method. Note that the output of the command is
        # included in the report anyway
        fd = open(self.fooFilePath)
        lines = fd.readlines()
        fd.close()
        for line in lines:
            if line.count("vendor_id"):
                self.addCustomText("Vendor ID string is: %s <br>\n" % line)
        #
        # Alerts can optionally be generated, and will be included in the
        # report automatically
        #
        self.addAlert("This is an alert")
        return
