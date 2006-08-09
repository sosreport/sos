## plugintools.py
## This exports methods available for use by plugins for sos

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

from sos.helpers import *
from threading import Thread
import os, os.path, sys, string, itertools, glob

class PluginBase:
    """
    Base class for plugins
    """
    def __init__(self, pluginname, commons):
        try:
            foo = len(self.optionList)
        except:
            self.optionList = []
        self.copiedFiles = []
        self.copiedDirs = []
        self.executedCommands = []
        self.alerts = []
        self.customText = ""
        self.optNames = []
        self.optParms = [] 
        self.piName = pluginname
        self.cInfo = commons
        self.forbiddenPaths = []
        self.copyPaths = []
        self.collectProgs = []

        # get the option list into a dictionary
        for opt in self.optionList:
            self.optNames.append(opt[0])
            self.optParms.append({'desc':opt[1], 'speed':opt[2], 'enabled':opt[3]})
        return

    # Methods for copying files and shelling out
    def doCopyFileOrDir(self, srcpath):
        ''' Copy file or directory to the destination tree. If a directory, then everything
        below it is recursively copied. A list of copied files are saved for use later
        in preparing a report
        '''
        copyProhibited = 0
        for path in self.forbiddenPaths:
            if ( srcpath.count(path) > 0 ):
                copyProhibited = 1
                
        if copyProhibited:
            return

        if os.path.islink(srcpath):
            # This is a symlink - We need to also copy the file that it points to
            # file and dir symlinks ar ehandled the same
            link = os.readlink(srcpath)
            if os.path.isabs(link):
                # the link was an absolute path, and will not point to the new
                # tree. We must adjust it.

                # What's the name of the symlink on the dest tree?
                dstslname = os.path.join(self.cInfo['dstroot'], srcpath.lstrip(os.path.sep))

                # make sure the dst dir exists
                if not (os.path.exists(os.path.dirname(dstslname)) and os.path.isdir(os.path.dirname(dstslname))):
                    # create the directory
                    os.makedirs(os.path.dirname(dstslname))

                dstsldir = os.path.join(self.cInfo['dstroot'], link.lstrip(os.path.sep))
                # Create the symlink on the dst tree
                rpth = sosRelPath(os.path.dirname(dstslname), dstsldir)
                os.symlink(rpth, dstslname)

            if os.path.isdir(srcpath):
                for file in os.listdir(srcpath):
                    if file == '.' or file == '..':
                        pass
                    else:
                        try:
                          self.doCopyFileOrDir(srcpath+'/'+file)
                        except:
                          sys.stderr.write("Problem at path %s\n" %  srcpath+'/'+file,)
                          sys.stderr.flush()
            else:
                try:
                  dstslname, abspath = self.__copyFile(srcpath)
                except:
                  sys.stderr.write("Problem at path %s\n" % srcpath)
                  sys.stderr.flush()
                self.copiedFiles.append({'srcpath':srcpath, 'dstpath':dstslname, 'symlink':"yes", 'pointsto':link})

            # Recurse to copy whatever it points to
            newpath = os.path.normpath(os.path.join(os.path.dirname(srcpath), link))
            try:
              self.doCopyFileOrDir(newpath)
            except:
              sys.stderr.write("Problem at path %s" % newpath,)
              sys.stderr.flush
            return abspath

        else:
            if not os.path.exists(srcpath):
                self.cInfo['logfd'].write("File or directory %s does not exist\n" % srcpath)
            elif  os.path.isdir(srcpath):
                for file in os.listdir(srcpath):
                    if file == '.' or file == '..':
                        pass
                    else:
                        self.doCopyFileOrDir(srcpath+'/'+file)
            else:
                # This is not a directory or a symlink
                tdstpath, abspath = self.__copyFile(srcpath)
                self.copiedFiles.append({'srcpath':srcpath, 'dstpath':tdstpath,'symlink':"no"}) # save in our list
                return abspath

    def __copyFile(self, src):
        """ call cp to copy a file, collect return status and output. Returns the
        destination file name.
        """
        try:
          status, shout, sherr = sosGetCommandOutput("/bin/cp --parents " + src +" " + self.cInfo['dstroot'])
          self.cInfo['logfd'].write(shout)
          self.cInfo['logfd'].write(sherr)
          #sosStatus(status)
          abspath = os.path.join(self.cInfo['dstroot'], src.lstrip(os.path.sep))
          relpath = sosRelPath(self.cInfo['rptdir'], abspath)
          return relpath, abspath
        except Exception,e:
          sys.stderr.write("Problem copying file %s\n" % src,)
          print e

    def addForbiddenPath(self, forbiddenPath):
        """Specify a path to not copy, even if it's part of a copyPaths[] entry.
        Note:  do NOT use globs here.
        """
        self.forbiddenPaths.append(forbiddenPath)
    
    def getAllOptions(self):
        return (self.optNames, self.optParms)
  
    def setOption(self, optionname, enable):
        ''' enable or disable the named option.
        '''
        for name, parms in zip(self.optNames, self.optParms):
            if name == optionname:
                parms['enabled'] = enable

    def isOptionEnabled(self, optionname):
        ''' see whether the named option is enabled.
        '''
        for name, parms in zip(self.optNames, self.optParms):
            if name == optionname:
                return parms['enabled']
        # nonexistent options aren't enabled.
        return 0

    def addCopySpec(self, copyspec):
        """ Add a file specification (can be file, dir,or shell glob) to be
        copied into the sosreport by this module
        """
        # Glob case handling is such that a valid non-glob is a reduced glob
        for filespec in glob.glob(copyspec):
          self.copyPaths.append(filespec)

    def copyFileGlob(self, srcglob):
        """ Deprecated - please modify modules to use addCopySpec()
        """
        sys.stderr.write("Warning: thecopyFileGlob() function has been deprecated.  Please")
        sys.stderr.write("use addCopySpec() instead.  Calling addCopySpec() now.")
        self.addCopySpec(srcglob)
        
    def copyFileOrDir(self, srcpath):
        """ Deprecated - please modify modules to use addCopySpec()
        """
        sys.stderr.write("Warning: the copyFileOrDir() function has been deprecated.  Please\n")
        sys.stderr.write("use addCopySpec() instead.  Calling addCopySpec() now.\n")
        raise ValueError
        self.addCopySpec(srcpath)
        
    def runExeInd(self, exe):
        """ Deprecated - use callExtProg()
        """
        sys.stderr.write("Warning: the runExeInd() function has been deprecated.  Please use\n")
        sys.stderr.write("the callExtProg() function.  This should only be called\n")
        sys.stderr.write("if collect() is overridden.")
        pass
        
    def callExtProg(self, prog):
        """ Execute a command independantly of the output gathering part of
        sosreport
        """                        
        # First check to make sure the binary exists and is runnable.
        if not os.access(prog.split()[0], os.X_OK):
            return
                                                    
        status, shout, sherr = sosGetCommandOutput(prog)                                                            
        return status
                                                                        
    def runExe(self, exe):
        """ Deprecated - use collectExtOutput()
        """
        sys.stderr.write("Warning: the runExe() function has been deprecated.  Please use\n")
        sys.stderr.write("the collectExtOutput() function.\n")
        pass

    def collectExtOutput(self, exe):
        self.collectProgs.append(exe)

    def collectOutputNow(self, exe):
        """ Execute a command and save the output to a file for inclusion in
        the report
        """
        # First check to make sure the binary exists and is runnable.
        if not os.access(exe.split()[0], os.X_OK):
            return

        status, shout, sherr = sosGetCommandOutput(exe)

        # build file name for output
        rawcmd = os.path.basename(exe).strip()[:28]

        # Mangle command to make it suitable for a file name
        tabl = string.maketrans(" /\t;#$|%\"'`}{\n", "_._-----------")
        mangledname = rawcmd.translate(tabl)

        outfn = self.cInfo['cmddir'] + "/" + self.piName + "." + mangledname

        # check for collisions
        while os.path.exists(outfn):
            outfn = outfn + "z"

        outfd = open(outfn, "w")
        outfd.write(shout)
        outfd.close()
        self.cInfo['logfd'].write(sherr)
        # sosStatus(status)
        # save info for later
        self.executedCommands.append({'exe': exe, 'file':outfn}) # save in our list
        return outfn
        
    # For adding output
    def addAlert(self, alertstring):
        """ Add an alert to the collection of alerts for this plugin. These
        will be displayed in the report
        """
        self.alerts.append(alertstring)
        return


    def addCustomText(self, text):
        """ Append text to the custom text that is included in the report. This
        is freeform and can include html.
        """
        self.customText = self.customText + text
        return

    def doCollect(self, verbosity):
        self.thread = Thread(target=self.copyStuff,name=self.piName+'-thread',args=(verbosity,))
        self.thread.start()
        
    def wait(self):
        self.thread.join()

    def copyStuff(self, verbosity):
        for path in self.copyPaths:
            try:
                self.doCopyFileOrDir(path)
            except Exception, e:
                sys.stderr.write("Error copying from pathspec %s\n" % path,)
                print e
                sys.stderr.flush()
        for prog in self.collectProgs:
            try:
                self.collectOutputNow(prog)
            except:
                sys.stderr.write("Error collecting output of '%s'\n" % prog,)
                sys.stderr.flush()
    
    def collect(self):
        """ This function has been replaced with setup().  Please change your
        module calls.  Calling setup() now.
        """
        self.setup()

    def setup(self):
        """This class must be overridden to add the copyPaths, forbiddenPaths,
        and external programs to be collected at a minimum.
        """
        pass

    def analyze(self, verbosity):
        pass

    def postproc(self, dstroot):
        pass
    
    def report(self):
        """ Present all information that was gathered in an html file that allows browsing
        the results.
        """
        # TODO make this prettier, this is a first pass
        html = '<hr/><a name="%s"></a>\n' % self.piName

        # Intro
        html = html + "<h2> Plugin <em>" + self.piName + "</em></h2>\n"

        # Files
        if len(self.copiedFiles):
            html = html + "<p>Files copied:<br><ul>\n"
            for file in self.copiedFiles:
                html = html + '<li><a href="%s">%s</a>' % (file['dstpath'], file['srcpath'])
                if (file['symlink'] == "yes"):
                    html = html + " (symlink to %s)" % file['pointsto']
                html = html + '</li>\n'
            html = html + "</ul></p>\n"

        # Dirs
        if len(self.copiedDirs):
            html = html + "<p>Directories Copied:<br><ul>\n"
            for dir in self.copiedDirs:
                html = html + '<li><a href="%s">%s</a>\n' % (dir['dstpath'], dir['srcpath'])
                if (dir['symlink'] == "yes"):
                    html = html + " (symlink to %s)" % dir['pointsto']
                html = html + '</li>\n'
            html = html + "</ul></p>\n"

        # Command Output
        if len(self.executedCommands):
            html = html + "<p>Commands Executed:<br><ul>\n"
            # convert file name to relative path from our root
            for cmd in self.executedCommands:
                cmdOutRelPath = sosRelPath(self.cInfo['rptdir'], cmd['file'])
                html = html + '<li><a href="%s">%s</a></li>\n' % (cmdOutRelPath, cmd['exe'])
            html = html + "</ul></p>\n"

        # Alerts
        if len(self.alerts):
            html = html + "<p>Alerts:<br><ul>\n"
            for alert in self.alerts:
                html = html + '<li>%s</li>\n' % alert
            html = html + "</ul></p>\n"

        # Custom Text
        if (self.customText != ""):
            html = html + "<p>Additional Information:<br>\n"
            html = html + self.customText + "</p>\n"

        return html


