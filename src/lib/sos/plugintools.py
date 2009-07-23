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

# pylint: disable-msg = R0902
# pylint: disable-msg = R0904
# pylint: disable-msg = W0702
# pylint: disable-msg = W0703
# pylint: disable-msg = R0201
# pylint: disable-msg = W0611
# pylint: disable-msg = W0613

"""
This is the base class for sosreport plugins
"""
from sos.helpers import *
from threading import Thread, activeCount
import os, os.path, sys, string, glob, re, traceback
import shutil
from stat import *
from time import time

class PluginException(Exception): pass

class PluginBase:
    """
    Base class for plugins
    """
    def __init__(self, pluginname, commons):
        if not getattr(self, "optionList", False):
            self.optionList = []

        self.copiedFiles = []
        self.copiedDirs = []
        self.executedCommands = []
        self.diagnose_msgs = []
        self.alerts = []
        self.customText = ""
        self.optNames = []
        self.optParms = [] 
        self.piName = pluginname
        self.cInfo = commons
        self.forbiddenPaths = []
        self.copyPaths = []
        self.collectProgs = []
        self.thread = None
        self.pid = None
        self.eta_weight = 1
        self.time_start = None
        self.time_stop  = None

        self.packages = []
        self.files = []

        self.must_exit = False

        self.soslog = logging.getLogger('sos')

        # get the option list into a dictionary
        for opt in self.optionList:
            self.optNames.append(opt[0])
            self.optParms.append({'desc':opt[1], 'speed':opt[2], 'enabled':opt[3]})

    def policy(self):
        return self.cInfo["policy"]

    def isInstalled(self, package_name):
        '''Is the package $package_name installed?
        '''
        return (self.policy().pkgByName(package_name) != {})

    # Method for applying regexp substitutions
    def doRegexSub(self, srcpath, regexp, subst):
        '''Apply a regexp substitution to a file archived by sosreport.
        '''
        if len(self.copiedFiles):
            for afile in self.copiedFiles:
                if afile['srcpath'] == srcpath:
                    abspath = os.path.join(self.cInfo['dstroot'], srcpath.lstrip(os.path.sep))
                    try:
                        fp = open(abspath, 'r')
                        tmpout, occurs = re.subn( regexp, subst, fp.read() )
                        fp.close()
                        if occurs > 0:
                           fp = open(abspath,'w')
                           fp.write(tmpout)
                           fp.close()
                           return occurs
                    except SystemExit:
                      raise SystemExit
                    except KeyboardInterrupt:
                      raise KeyboardInterrupt
                    except Exception, e:
                        self.soslog.log(logging.VERBOSE, "problem at path %s (%s)" % (abspath,e))
                        break
        return False
    
    def doRegexFindAll(self, regex, fname):
        ''' Return a list of all non overlapping matches in the string(s)
        '''
        try:
            return re.findall(regex, open(fname, 'r').read(), re.MULTILINE)
        except:  # IOError, AttributeError, etc.
            return []

    # Methods for copying files and shelling out
    def doCopyFileOrDir(self, srcpath):
        # pylint: disable-msg = R0912
        # pylint: disable-msg = R0915
        ''' Copy file or directory to the destination tree. If a directory, then everything
        below it is recursively copied. A list of copied files are saved for use later
        in preparing a report
        '''
        copyProhibited = 0
        for path in self.forbiddenPaths:
            if ( srcpath.count(path) > 0 ):
                copyProhibited = 1

        if copyProhibited:
            return ''

        if not os.path.exists(srcpath):
            self.soslog.debug("file or directory %s does not exist" % srcpath)
            return

        if os.path.islink(srcpath):
            # This is a symlink - We need to also copy the file that it points to

            # FIXME: ignore directories for now
            if os.path.isdir(srcpath):
                return

            link = os.readlink(srcpath)

            # What's the name of the symlink on the dest tree?
            dstslname = os.path.join(self.cInfo['dstroot'], srcpath.lstrip(os.path.sep))

            if os.path.isabs(link):
                # the link was an absolute path, and will not point to the new
                # tree. We must adjust it.
                rpth = sosRelPath(os.path.dirname(dstslname), os.path.join(self.cInfo['dstroot'], link.lstrip(os.path.sep)))
            else:
                # no adjustment, symlink is the relative path
                rpth = link

            # make sure the link doesn't already exists
            if os.path.exists(dstslname):
                self.soslog.log(logging.DEBUG, "skipping symlink creation: already exists (%s)" % dstslname)
                return

            # make sure the dst dir exists
            if not (os.path.exists(os.path.dirname(dstslname)) and os.path.isdir(os.path.dirname(dstslname))):
                os.makedirs(os.path.dirname(dstslname))

            self.soslog.log(logging.VERBOSE3, "creating symlink %s -> %s" % (dstslname, rpth))
            os.symlink(rpth, dstslname)
            self.copiedFiles.append({'srcpath':srcpath, 'dstpath':rpth, 'symlink':"yes", 'pointsto':link})
            self.doCopyFileOrDir(link)
            return

        else: # not a symlink
            if os.path.isdir(srcpath):
                for afile in os.listdir(srcpath):
                    if afile == '.' or afile == '..':
                        pass
                    else:
                        self.doCopyFileOrDir(srcpath+'/'+afile)
                return

        # if we get here, it's definitely a regular file (not a symlink or dir)

        self.soslog.log(logging.VERBOSE3, "copying file %s" % srcpath)
        try:
            tdstpath, abspath = self.__copyFile(srcpath)
        except PluginException, e:
            self.soslog.log(logging.DEBUG, "%s:  %s" % (srcpath,e))
            return
        except IOError:
            self.soslog.log(logging.VERBOSE2, "error copying file %s (IOError)" % (srcpath))
            return 
        except:
            self.soslog.log(logging.VERBOSE2, "error copying file %s (SOMETHING HAPPENED)" % (srcpath))
            return 

        self.copiedFiles.append({'srcpath':srcpath, 'dstpath':tdstpath, 'symlink':"no"}) # save in our list

        return abspath

    def __copyFile(self, src):
        """ call cp to copy a file, collect return status and output. Returns the
        destination file name.
        """
        rel_dir =  os.path.dirname(src).lstrip(os.path.sep)
#        if rel_dir[0] == "/": rel_dir = rel_dir[1:]
        new_dir = os.path.join(self.cInfo['dstroot'], rel_dir)
        new_fname = os.path.join(new_dir, os.path.basename(src))

        if not os.path.exists(new_fname):
            if not os.path.isdir(new_dir):
                os.makedirs(new_dir)

            if os.path.islink(src):
                linkto = os.readlink(src)
                os.symlink(linkto, new_fname)
            else:
                shutil.copy2(src, new_dir)
        else:
            raise PluginException('Error copying file: already exists')

        abspath = os.path.join(self.cInfo['dstroot'], src.lstrip(os.path.sep))
        relpath = sosRelPath(self.cInfo['rptdir'], abspath)
        return (relpath, abspath)

    def addForbiddenPath(self, forbiddenPath):
        """Specify a path to not copy, even if it's part of a copyPaths[] entry.
        """
       # Glob case handling is such that a valid non-glob is a reduced glob
        for filespec in glob.glob(forbiddenPath):
            self.forbiddenPaths.append(filespec)
    
    def getAllOptions(self):
        """
        return a list of all options selected
        """
        return (self.optNames, self.optParms)
  
    def setOption(self, optionname, value):
        ''' set the named option to value.
        '''
        for name, parms in zip(self.optNames, self.optParms):
            if name == optionname:
                parms['enabled'] = value
                return True
        else:
            return False

    def isOptionEnabled(self, optionname):
        ''' Deprecated, use getOption() instead
        '''
        return self.getOption(optionname)

    def getOption(self, optionname):
        ''' see whether the named option is enabled.
        '''
        for name, parms in zip(self.optNames, self.optParms):
            if name == optionname:
                return parms['enabled']
        # nonexistent options aren't enabled.
        return 0

    def addCopySpecLimit(self,fname,sizelimit = None):
        """Add a file specification (with limits)
        """
        if not ( fname and len(fname) ):
            self.soslog.warning("invalid file path")
            return False
        files = glob.glob(fname)
        files.sort()
        cursize = 0
        for flog in files:
            cursize += os.stat(flog)[ST_SIZE]
            if sizelimit and (cursize / 1024 / 1024) > sizelimit:
               break
            self.addCopySpec(flog)

    def addCopySpec(self, copyspec):
        """ Add a file specification (can be file, dir,or shell glob) to be
        copied into the sosreport by this module
        """
        if not ( copyspec and len(copyspec) ):
            self.soslog.warning("invalid file path")
            return False
        # Glob case handling is such that a valid non-glob is a reduced glob
        for filespec in glob.glob(copyspec):
            self.copyPaths.append(filespec)

    def callExtProg(self, prog):
        """ Execute a command independantly of the output gathering part of
        sosreport
        """
        # pylint: disable-msg = W0612
        status, shout, runtime = sosGetCommandOutput(prog)
        return status

    def collectExtOutput(self, exe, suggest_filename = None, root_symlink = None, timeout = 300):
        """
        Run a program and collect the output
        """
        self.collectProgs.append( (exe, suggest_filename, root_symlink, timeout) )

    def fileGrep(self, regexp, fname):
        try:
            return [l for l in open(fname).readlines() if re.match(regexp, l)]
        except:  # IOError, AttributeError, etc.
            return []

    def mangleCommand(self, exe):
        # FIXME: this can be improved
        mangledname = re.sub(r"^/(usr/|)(bin|sbin)/", "", exe)
        mangledname = re.sub(r"[^\w\-\.\/]+", "_", mangledname)
        mangledname = re.sub(r"/", ".", mangledname).strip(" ._-")[0:64]
        return mangledname

    def makeCommandFilename(self, exe):
        """ The internal function to build up a filename based on a command """

        outfn = self.cInfo['cmddir'] + "/" + self.piName + "/" + self.mangleCommand(exe)

        # check for collisions
        if os.path.exists(outfn):
            inc = 2
            while True:
               newfn = "%s_%d" % (outfn, inc)
               if not os.path.exists(newfn):
                  outfn = newfn
                  break
               inc +=1

        return outfn

    def collectOutputNow(self, exe, suggest_filename = None, root_symlink = False, timeout = 300):
        """ Execute a command and save the output to a file for inclusion in
        the report
        """

        # pylint: disable-msg = W0612
        status, shout, runtime = sosGetCommandOutput(exe, timeout = timeout)

        if suggest_filename:
            outfn = self.makeCommandFilename(suggest_filename)
        else:
            outfn = self.makeCommandFilename(exe)

        if not os.path.isdir(os.path.dirname(outfn)):
            os.mkdir(os.path.dirname(outfn))

        if not (status == 127 or status == 32512): # if not command_not_found
            outfd = open(outfn, "w")
            if len(shout):    outfd.write(shout+"\n")
            outfd.close()

            if root_symlink:
                curdir = os.getcwd()
                os.chdir(self.cInfo['dstroot'])
                try:    os.symlink(outfn[len(self.cInfo['dstroot'])+1:], root_symlink.strip("/."))
                except: pass
                os.chdir(curdir)

            outfn_strip = outfn[len(self.cInfo['cmddir'])+1:]

        else:
            self.soslog.log(logging.VERBOSE, "could not run command: %s" % exe)
            outfn = None
            outfn_strip = None

        # sosStatus(status)
        # save info for later
        self.executedCommands.append({'exe': exe, 'file':outfn_strip}) # save in our list
        self.cInfo['xmlreport'].add_command(cmdline=exe,exitcode=status,f_stdout=outfn_strip,runtime=runtime)
        return outfn

    def writeTextToCommand(self, exe, text):
        """ A function that allows you to write a random text string to the
        command output location referenced by exe; this is useful if you want
        to conditionally collect information, but still want the output file
        to exist so as not to confuse readers """

        outfn = self.makeCommandFilename(exe)

        if not os.path.isdir(os.path.dirname(outfn)):
            os.mkdir(os.path.dirname(outfn))

        outfd = open(outfn, "w")
        outfd.write(text)
        outfd.close()

        self.executedCommands.append({'exe': exe, 'file': outfn}) # save in our list
        return outfn

    # For adding warning messages regarding configuration sanity
    def addDiagnose(self, alertstring):
        """ Add a configuration sanity warning for this plugin. These
        will be displayed on-screen before collection and in the report as well.
        """
        self.diagnose_msgs.append(alertstring)
        return
        
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

    def doCollect(self):
        """ This function has been replaced with copyStuff(threaded = True).  Please change your
        module calls.  Calling setup() now.
        """
        return self.copyStuff(threaded = True)

    def isRunning(self):
        """
        if threaded, is thread running ?
        """
        if self.thread: return self.thread.isAlive()
        return None
        
    def wait(self,timeout=None):
        """
        wait for a thread to complete - only called for threaded execution
        """
        self.thread.join(timeout)
        return self.thread.isAlive()

    def copyStuff(self, threaded = False, semaphore = None):
        """
        Collect the data for a plugin
        """
        if threaded and self.thread == None:
            self.thread = Thread(target=self.copyStuff, name=self.piName+'-thread', args = [True, semaphore] )
            self.thread.start()
            return self.thread

        if semaphore: semaphore.acquire()

        if self.must_exit:
            semaphore.release()
            return

        self.soslog.log(logging.VERBOSE, "starting threaded plugin %s" % self.piName)

        self.time_start = time()
        self.time_stop  = None

        for path in self.copyPaths:
            self.soslog.debug("copying pathspec %s" % path)
            try:
                self.doCopyFileOrDir(path)
            except SystemExit:
                if semaphore: semaphore.release()
                if threaded: return KeyboardInterrupt
                else:        raise  KeyboardInterrupt
            except KeyboardInterrupt:
                if semaphore: semaphore.release()
                if threaded: return KeyboardInterrupt
                else:        raise  KeyboardInterrupt
            except Exception, e:
                self.soslog.log(logging.VERBOSE2, "error copying from pathspec %s (%s), traceback follows:" % (path,e))
                self.soslog.log(logging.VERBOSE2, traceback.format_exc())
        for (prog, suggest_filename, root_symlink, timeout) in self.collectProgs:
            self.soslog.debug("collecting output of '%s'" % prog)
            try:
                self.collectOutputNow(prog, suggest_filename, root_symlink, timeout)
            except SystemExit:
                if semaphore: semaphore.release()
                if threaded: return SystemExit
                else:        raise  SystemExit
            except KeyboardInterrupt:
                if semaphore: semaphore.release()
                if threaded: return KeyboardInterrupt
                else:        raise  KeyboardInterrupt
            except Exception, e:
                self.soslog.log(logging.VERBOSE2, "error collection output of '%s', traceback follows:" % prog)
                self.soslog.log(logging.VERBOSE2, traceback.format_exc())

        self.time_stop = time()

        if semaphore: semaphore.release()
        self.soslog.log(logging.VERBOSE, "plugin %s returning" % self.piName)

    def exit_please(self):
        """ This function tells the plugin that it should exit ASAP"""
        self.must_exit = True

    def get_description(self):
        """ This function will return the description for the plugin"""
        try:
            return self.__doc__.strip()
        except:
            return "<no description available>"

    def checkenabled(self):
        """ This function can be overidden to let the plugin decide whether
        it should run or not.
        """
        # some files or packages have been specified for this package
        if len(self.files) or len(self.packages):
            for fname in self.files:
                if os.path.exists(fname):
                    return True
            for pkgname in self.packages:
                if self.isInstalled(pkgname):
                    return True
            return False

        return True

    def defaultenabled(self):
        """This devices whether a plugin should be automatically loaded or
        only if manually specified in the command line."""
        return True
    
    def collect(self):
        """ This function has been replaced with setup().  Please change your
        module calls.  Calling setup() now.
        """
        self.setup()

    def diagnose(self):
        """This class must be overridden to check the sanity of the system's
        configuration before the collection begins.
        """
        pass

    def setup(self):
        """This class must be overridden to add the copyPaths, forbiddenPaths,
        and external programs to be collected at a minimum.
        """
        pass

    def analyze(self):
        """
        perform any analysis. To be replaced by a plugin if desired
        """
        pass

    def postproc(self):
        """
        perform any postprocessing. To be replaced by a plugin if desired
        """
        pass
    
    def report(self):
        """ Present all information that was gathered in an html file that allows browsing
        the results.
        """
        # make this prettier
        html = '<hr/><a name="%s"></a>\n' % self.piName

        # Intro
        html = html + "<h2> Plugin <em>" + self.piName + "</em></h2>\n"

        # Files
        if len(self.copiedFiles):
            html = html + "<p>Files copied:<br><ul>\n"
            for afile in self.copiedFiles:
                html = html + '<li><a href="%s">%s</a>' % (afile['dstpath'], afile['srcpath'])
                if (afile['symlink'] == "yes"):
                    html = html + " (symlink to %s)" % afile['pointsto']
                html = html + '</li>\n'
            html = html + "</ul></p>\n"

        # Dirs
        if len(self.copiedDirs):
            html = html + "<p>Directories Copied:<br><ul>\n"
            for adir in self.copiedDirs:
                html = html + '<li><a href="%s">%s</a>\n' % (adir['dstpath'], adir['srcpath'])
                if (adir['symlink'] == "yes"):
                    html = html + " (symlink to %s)" % adir['pointsto']
                html = html + '</li>\n'
            html = html + "</ul></p>\n"

        # Command Output
        if len(self.executedCommands):
            html = html + "<p>Commands Executed:<br><ul>\n"
            # convert file name to relative path from our root
            for cmd in self.executedCommands:
                if cmd["file"] and len(cmd["file"]):
                    cmdOutRelPath = sosRelPath(self.cInfo['rptdir'], self.cInfo['cmddir'] + "/" + cmd['file'])
                    html = html + '<li><a href="%s">%s</a></li>\n' % (cmdOutRelPath, cmd['exe'])
                else:
                    html = html + '<li>%s</li>\n' % (cmd['exe'])
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
