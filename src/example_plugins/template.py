#!/usr/bin/env python

## template.py
## A template for sos plugins

## Copyright (C) 2006 Steve Conklin <sconklin@redhat.com>

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
class template(sos.plugintools.PluginBase):
    """This is a template plugin for sos. Plugins gather, analyze, and report on various aspects
    of system operation that are of interest. plugins are based on the PluginBase class, which
    you should inspect if you wish to override any methods in your plugin. The methods of use
    to plugin developers are:
    collect() - use the functions sosCp and sosRunExe to gether information
    analyze() - perform any special analysis you require beyond just saving the
                information gathered by collect(). Use sosAlert() and sosAddCustomText()
                to add information to the report.
    report() - override this method if you wish to replace the default reporting

    All plugins will use collect(), some will use analyze(), few will override report()
    """

    # Add your options here, indicate whether they are slow to run, and set whether they are enabled by default
    # Options are dictionaries that conatin a short name, long desc, speed, and whether they are enabled by default
    optionList = [("init.d",  'Gathers the init.d directory', 'slow', 0),
                  ('Option 2', 'Gathers information about each follicle on every toe', 'slow', 0),
                  ('Option 3', 'Gathers toenail polish color', 'fast', 0)]

    def collect(self):
        ''' First phase - Collect all the information we need.
        Directories are copied recursively. arbitrary commands may be
        executed using the susRunExe method. Information is automatically saved, and
        links are presented in the report to each file or directory which has been
        copied to the saved tree. Also, links are provided to the output from each command.
        '''
        # For this example, we use files created in our build test directory. Edit the
        # following line after running the maketesttree.sh script
        testdir = "/home/sconklin/src/sos/tests/tree/"
        self.copyFileOrDir(testdir + "absdirlink")
        self.copyFileOrDir(testdir + "bar")

        # Here's how to test your options and execute if enabled
        if self.isOptionEnabled("init.d"):
            self.copyFileOrDir("/etc/init.d")
        self.copyFileOrDir(testdir + "abslink")
        # you can save the path to the copied file for later analysis if desired
        self.fooFilePath = self.copyFileOrDir(testdir + "abslink2")
        self.copyFileOrDir(testdir + "abslink3")
        self.psCmdDstFileName = self.runExe("/bin/ps -ef")
        return

    def analyze(self):
        ''' This is optional and need not be defined.
        If you wish to perform some analysis on either files
        that were gathered or on the output of commands, then save the filenames on the
        destination file system when gathering that information in the collect() method
        and use them here
        '''
        # This is an example of opening and reading the output of a command that
        # was run in the collect() method. Note that the output of the command is
        # included in the report anyway
        fd = open(self.psCmdDstFileName)
        lines = fd.readlines()
        fd.close()
        procs = 0
        for line in lines:
            # can perform analysis here - This is a dumb example, but
            # shows how to add customized text to output
            if line.count("sconkli"):
                procs = procs + 1
        self.addCustomText("sconklin has %d processes running <br>\n" % procs)
        #
        # Alerts can optionally be generated, and will be included in the
        # report automatically
        #
        self.addAlert("This is an alert")
        return

#    def report(self):
#        """ Usually, this doesn't even need to be defined, and you can inherit the
#        base class, unless you want to replace what sosGetResults()
#        does with your own custom report generator. If you are going to do that, have a good
#        look at that method to see what it does. Custom text and alerts can still be added
#        here using sosAddCustomText() and sosAddAlert()
#        This method returns html that will be included inline in the report
#        """


