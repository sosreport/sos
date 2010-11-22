"""
Gather information about a system and report it using plugins
supplied for application-specific information
"""
## sosreport.py
## gather information about a system and report it

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

# pylint: disable-msg = W0611
# pylint: disable-msg = W0702
# pylint: disable-msg = R0912
# pylint: disable-msg = R0914
# pylint: disable-msg = R0915
# pylint: disable-msg = R0913
# pylint: disable-msg = E0611
# pylint: disable-msg = E1101
# pylint: disable-msg = R0904
# pylint: disable-msg = R0903

import sys, traceback
import os
import logging
from optparse import OptionParser, Option
import ConfigParser
import sos.policyredhat
from sos.helpers import importPlugin
import signal
from stat import ST_UID, ST_GID, ST_MODE, ST_CTIME, ST_ATIME, ST_MTIME, S_IMODE
from time import strftime, localtime
from collections import deque
from itertools import izip

from sos import _sos as _
from sos import __version__

if os.path.isfile('/etc/fedora-release'):
    __distro__ = 'Fedora'
else:
    __distro__ = 'Red Hat Enterprise Linux'

class GlobalVars:
    """ Generic container for shared vars """
    def __init__(self):
        pass

## Set up routines to be linked to signals for termination handling
def exittermhandler(signum, frame):
    """ Handle signals cleanly """
    del frame, signum
    doExitCode()

def doExitCode():
    """ Exit with return """

    for plugname, plug in GlobalVars.loadedplugins:
        plug.exit_please()
        del plugname

    print "All processes ended, cleaning up."
    doExit(1)

def doExit(error=0):
    """ Exit with return """
    # We will attempt to clean dstroot; there is only
    # one instance where the policy is not set and that is
    # during the actual creation of dstroot
    try:
        GlobalVars.policy.cleanDstroot()
    except AttributeError:
        sys.exit(error)
    sys.exit(error)

def doException(etype, eval, etrace):
    """ Wrap exception in debugger if not in tty """
    if hasattr(sys, 'ps1') or not sys.stderr.isatty():
        # we are in interactive mode or we don't have a tty-like
        # device, so we call the default hook
        sys.__excepthook__(etype, eval, etrace)
    else:
        import traceback, pdb
        # we are NOT in interactive mode, print the exception...
        traceback.print_exception(etype, eval, etrace, limit=2, file=sys.stdout)
        print
        # ...then start the debugger in post-mortem mode.
        pdb.pm()

# Handle any sort of exit signal cleanly
# Currently, we intercept only sig 15 (TERM)
signal.signal(signal.SIGTERM, exittermhandler)

class OptionParserExtended(OptionParser):
    """ Show examples """
    def print_help(self, out=sys.stdout):
        """ Prints help content including examples """
        OptionParser.print_help(self, out)
        print
        print "Some examples:"
        print
        print " enable cluster plugin only and collect dlm lockdumps:"
        print "   # sosreport -o cluster -k cluster.lockdump"
        print
        print " disable memory and samba plugins, turn off rpm -Va collection:"
        print "   # sosreport -n memory,samba -k rpm.rpmva=off"
        print
        del out

class SosOption (Option):
    """Allow to specify comma delimited list of plugins"""
    ACTIONS = Option.ACTIONS + ("extend",)
    STORE_ACTIONS = Option.STORE_ACTIONS + ("extend",)
    TYPED_ACTIONS = Option.TYPED_ACTIONS + ("extend",)

    def take_action(self, action, dest, opt, value, values, parser):
        """ Performs list extension on plugins """
        if action == "extend":
            try:
                lvalue = value.split(",")
            except:
                pass
            else:
                values.ensure_value(dest, deque()).extend(lvalue)
        else:
            Option.take_action(self, action, dest, opt, value, values, parser)

def parse_options(opts):
    """ Parse command line options """

    __cmdParser__ = OptionParserExtended(option_class=SosOption)
    __cmdParser__.add_option("-l", "--list-plugins", action="store_true", \
                         dest="listPlugins", default=False, \
                         help="list plugins and available plugin options")
    __cmdParser__.add_option("-n", "--skip-plugins", action="extend", \
                         dest="noplugins", type="string", \
                         help="skip these plugins", default = deque())
    __cmdParser__.add_option("-e", "--enable-plugins", action="extend", \
                         dest="enableplugins", type="string", \
                         help="enable these plugins", default = deque())
    __cmdParser__.add_option("-o", "--only-plugins", action="extend", \
                         dest="onlyplugins", type="string", \
                         help="enable these plugins only", default = deque())
    __cmdParser__.add_option("-k", action="extend", \
                         dest="plugopts", type="string", \
                         help="plugin options in plugname.option=value format (see -l)")
    __cmdParser__.add_option("-a", "--alloptions", action="store_true", \
                         dest="usealloptions", default=False, \
                         help="enable all options for loaded plugins")
    __cmdParser__.add_option("-u", "--upload", action="store", \
                         dest="upload", default=False, \
                         help="upload the report to an ftp server")
    #__cmdParser__.add_option("--encrypt", action="store_true", \
    #                     dest="encrypt", default=False, \
    #                     help="encrypt with GPG using Red Hat support's public key")
    __cmdParser__.add_option("--batch", action="store_true", \
                         dest="batch", default=False, \
                         help="do not ask any question (batch mode)")
    __cmdParser__.add_option("--build", action="store_true", \
                         dest="build", default=False, \
                         help="keep sos tree available and dont package results")
    __cmdParser__.add_option("--no-colors", action="store_true", \
                         dest="nocolors", default=False, \
                         help="do not use terminal colors for text")
    __cmdParser__.add_option("-v", "--verbose", action="count", \
                         dest="verbosity", \
                         help="increase verbosity")
    __cmdParser__.add_option("--debug", action="count", \
                         dest="debug", \
                         help="enabling debugging through python debugger")
    __cmdParser__.add_option("--ticket-number", action="store", \
                         dest="ticketNumber", \
                         help="set ticket number")
    __cmdParser__.add_option("--name", action="store", \
                         dest="customerName", \
                         help="define customer name")
    __cmdParser__.add_option("--config-file", action="store", \
                         dest="config_file", \
                         help="specify alternate configuration file")
    __cmdParser__.add_option("--tmp-dir", action="store", \
                         dest="tmp_dir", \
                         help="specify alternate temporary directory", default="/tmp")
    __cmdParser__.add_option("--diagnose", action="store_true", \
                         dest="diagnose", \
                         help="enable diagnostics", default=False)
    __cmdParser__.add_option("--analyze", action="store_true", \
                         dest="analyze", \
                         help="enable analyzations", default=False)
    __cmdParser__.add_option("--report", action="store_true", \
                         dest="report", \
                         help="Enable html/xml reporting", default=False)
    __cmdParser__.add_option("--profile", action="store_true", \
                         dest="profiler", \
                         help="turn on profiling", default=False)

    (GlobalVars.__cmdLineOpts__, GlobalVars.__cmdLineArgs__) = __cmdParser__.parse_args(opts)

def textcolor(text, color, raw=0):
    """ Terminal text coloring function """
    if GlobalVars.__cmdLineOpts__.nocolors:
        return text
    colors = {  "black":"30", "red":"31", "green":"32", "brown":"33", "blue":"34",
                "purple":"35", "cyan":"36", "lgray":"37", "gray":"1;30", "lred":"1;31",
                "lgreen":"1;32", "yellow":"1;33", "lblue":"1;34", "pink":"1;35",
                "lcyan":"1;36", "white":"1;37" }
    opencol = "\033["
    closecol = "m"
    clear = opencol + "0" + closecol
    f = opencol + colors[color] + closecol
    del raw
    return "%s%s%s" % (f, text, clear)

class XmlReport:
    """ Report build class """
    def __init__(self):
        try:
            import libxml2
        except ImportError:
            self.enabled = False
            return
        else:
            self.enabled = False
            return
        self.doc = libxml2.newDoc("1.0")
        self.root = self.doc.newChild(None, "sos", None)
        self.commands = self.root.newChild(None, "commands", None)
        self.files = self.root.newChild(None, "files", None)

    def add_command(self, cmdline, exitcode, stdout = None, stderr = None,
                    f_stdout=None, f_stderr=None, runtime=None):
        """ Appends command run into report """
        if not self.enabled:
            return

        cmd = self.commands.newChild(None, "cmd", None)

        cmd.setNsProp(None, "cmdline", cmdline)

        cmdchild = cmd.newChild(None, "exitcode", str(exitcode))

        if runtime:
            cmd.newChild(None, "runtime", str(runtime))

        if stdout or f_stdout:
            cmdchild = cmd.newChild(None, "stdout", stdout)
            if f_stdout:
                cmdchild.setNsProp(None, "file", f_stdout)

        if stderr or f_stderr:
            cmdchild = cmd.newChild(None, "stderr", stderr)
            if f_stderr:
                cmdchild.setNsProp(None, "file", f_stderr)

    def add_file(self, fname, stats):
        """ Appends file(s) added to report """
        if not self.enabled:
            return

        cfile = self.files.newChild(None, "file", None)

        cfile.setNsProp(None, "fname", fname)

        cchild = cfile.newChild(None, "uid", str(stats[ST_UID]))
        cchild = cfile.newChild(None, "gid", str(stats[ST_GID]))
        cfile.newChild(None, "mode", str(oct(S_IMODE(stats[ST_MODE]))))
        cchild = cfile.newChild(None, "ctime", strftime('%a %b %d %H:%M:%S %Y',
                                                        localtime(stats[ST_CTIME])))
        cchild.setNsProp(None, "tstamp", str(stats[ST_CTIME]))
        cchild = cfile.newChild(None, "atime", strftime('%a %b %d %H:%M:%S %Y',
                                                        localtime(stats[ST_ATIME])))
        cchild.setNsProp(None, "tstamp", str(stats[ST_ATIME]))
        cchild = cfile.newChild(None, "mtime", strftime('%a %b %d %H:%M:%S %Y',
                                                        localtime(stats[ST_MTIME])))
        cchild.setNsProp(None, "tstamp", str(stats[ST_MTIME]))

    def serialize(self):
        """ Serializes xml """
        if not self.enabled:
            return

        print self.doc.serialize(None,  1)

    def serialize_to_file(self, fname):
        """ Serializes to file """
        if not self.enabled:
            return

        outfn = open(fname,"w")
        outfn.write(self.doc.serialize(None, 1))
        outfn.close()

# if debugging is enabled, allow plugins to raise exceptions
def isDebug():
    """ Enable plugin to raise exception """
    if GlobalVars.__cmdLineOpts__.debug:
        sys.excepthook = doException
        GlobalVars.__raisePlugins__ = 1
    else:
        GlobalVars.__raisePlugins__ = 0

def sosreport(opts):
    """
    This is the top-level function that gathers
    and processes all sosreport information
    """
    parse_options(opts)
    # check debug
    isDebug()

    config = ConfigParser.ConfigParser()
    if GlobalVars.__cmdLineOpts__.config_file:
        config_file = GlobalVars.__cmdLineOpts__.config_file
    else:
        config_file = '/etc/sos.conf'
    try:
        config.readfp(open(config_file))
    except IOError:
        pass

    GlobalVars.loadedplugins = deque() 
    skippedplugins = deque() 
    alloptions = deque() 

    # perhaps we should automatically locate the policy module??
    GlobalVars.policy = sos.policyredhat.SosPolicy()

    # find the plugins path
    paths = sys.path
    for path in paths:
        if path.strip()[-len("site-packages"):] == "site-packages" \
        and os.path.isdir(path + "/sos/plugins"):
            pluginpath = path + "/sos/plugins"

    # Set up common info and create destinations

    GlobalVars.dstroot = GlobalVars.policy.getDstroot(GlobalVars.__cmdLineOpts__.tmp_dir)
    if not GlobalVars.dstroot:
        print _("Could not create temporary directory.")
        doExit()

    cmddir = os.path.join(GlobalVars.dstroot, "sos_commands")
    logdir = os.path.join(GlobalVars.dstroot, "sos_logs")
    rptdir = os.path.join(GlobalVars.dstroot, "sos_reports")
    os.mkdir(cmddir, 0755)
    os.mkdir(logdir, 0755)
    os.mkdir(rptdir, 0755)

    # initialize logging
    soslog = logging.getLogger('sos')
    soslog.setLevel(logging.DEBUG)

    logging.VERBOSE  = logging.INFO - 1
    logging.VERBOSE2 = logging.INFO - 2
    logging.VERBOSE3 = logging.INFO - 3
    logging.addLevelName(logging.VERBOSE, "verbose")
    logging.addLevelName(logging.VERBOSE2,"verbose2")
    logging.addLevelName(logging.VERBOSE3,"verbose3")

    if GlobalVars.__cmdLineOpts__.profiler:
        proflog = logging.getLogger('sosprofile')
        proflog.setLevel(logging.DEBUG)
        
    # if stdin is not a tty, disable colors and don't ask questions
    if not sys.stdin.isatty():
        GlobalVars.__cmdLineOpts__.nocolors = True
        GlobalVars.__cmdLineOpts__.batch = True

    # log to a file
    flog = logging.FileHandler(logdir + "/sos.log")
    flog.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    flog.setLevel(logging.VERBOSE3)
    soslog.addHandler(flog)

    if GlobalVars.__cmdLineOpts__.profiler:
        # setup profile log
        plog = logging.FileHandler(logdir + "/sosprofile.log")
        plog.setFormatter(logging.Formatter('%(message)s'))
        plog.setLevel(logging.DEBUG)
        proflog.addHandler(plog)

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler(sys.stderr)
    if GlobalVars.__cmdLineOpts__.verbosity > 0:
        console.setLevel(20 - GlobalVars.__cmdLineOpts__.verbosity)
    else:
        console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(message)s'))
    soslog.addHandler(console)

    xmlrep = XmlReport()

    # set up dict so everyone can share the following
    commons = {'dstroot': GlobalVars.dstroot, 'cmddir': cmddir, 'logdir': logdir, 'rptdir': rptdir,
               'soslog': soslog, 'policy': GlobalVars.policy, 'verbosity' : GlobalVars.__cmdLineOpts__.verbosity,
               'xmlreport' : xmlrep, 'cmdlineopts':GlobalVars.__cmdLineOpts__, 'config':config }

    # Make policy aware of the commons
    GlobalVars.policy.setCommons(commons)

    print
    print _("sosreport (version %s)" % (__version__,))
    print

    # disable plugins that we read from conf files
    conf_disable_plugins_list = deque() 
    conf_disable_plugins = None
    if config.has_option("plugins", "disable"):
        conf_disable_plugins = config.get("plugins", "disable").split(',')
        for item in conf_disable_plugins:
            conf_disable_plugins_list.append(item.strip())

    # generate list of available plugins
    plugins = os.listdir(pluginpath)
    plugins.sort()
    plugin_names = deque()

    # validate and load plugins
    for plug in plugins:
        plugbase =  plug[:-3]
        if not plug[-3:] == '.py' or plugbase == "__init__":
            continue
        try:
            if GlobalVars.policy.validatePlugin(pluginpath + plug):
                pluginClass = importPlugin("sos.plugins." + plugbase, plugbase)
            else:
                soslog.warning(_("plugin %s does not validate, skipping") % plug)
                skippedplugins.append((plugbase, pluginClass(plugbase, commons)))
                continue
            # plug-in is valid, let's decide whether run it or not
            plugin_names.append(plugbase)
            if plugbase in GlobalVars.__cmdLineOpts__.noplugins or \
            plugbase in conf_disable_plugins_list:
                # skipped
                skippedplugins.append((plugbase, pluginClass(plugbase, commons)))
                continue
            if not pluginClass(plugbase, commons).checkenabled() and \
            not plugbase in GlobalVars.__cmdLineOpts__.enableplugins  and \
            not plugbase in GlobalVars.__cmdLineOpts__.onlyplugins:
                # inactive
                skippedplugins.append((plugbase, pluginClass(plugbase, commons)))
                continue
            if not pluginClass(plugbase, commons).defaultenabled() and \
            not plugbase in GlobalVars.__cmdLineOpts__.enableplugins and \
            not plugbase in GlobalVars.__cmdLineOpts__.onlyplugins:
                # not loaded by default
                skippedplugins.append((plugbase, pluginClass(plugbase, commons)))
                continue
            if GlobalVars.__cmdLineOpts__.onlyplugins and \
            not plugbase in GlobalVars.__cmdLineOpts__.onlyplugins:
                # not specified
                skippedplugins.append((plugbase, pluginClass(plugbase, commons)))
                continue
            GlobalVars.loadedplugins.append((plugbase, pluginClass(plugbase, commons)))
        except:
            soslog.warning(_("plugin %s does not install, skipping") % plug)
            if GlobalVars.__raisePlugins__:
                raise

    # First, gather and process options
    # using the options specified in the command line (if any)
    if GlobalVars.__cmdLineOpts__.usealloptions:
        for plugname, plug in GlobalVars.loadedplugins:
            for name, parms in zip(plug.optNames, plug.optParms):
                if type(parms["enabled"])==bool:
                    parms["enabled"] = True
                del name

    # read plugin tunables from configuration file
    if config.has_section("tunables"):
        if not GlobalVars.__cmdLineOpts__.plugopts:
            GlobalVars.__cmdLineOpts__.plugopts = deque() 

        for opt, val in config.items("tunables"):
            if not opt.split('.')[0] in conf_disable_plugins_list:
                GlobalVars.__cmdLineOpts__.plugopts.append(opt + "=" + val)

    if GlobalVars.__cmdLineOpts__.plugopts:
        opts = {}
        for opt in GlobalVars.__cmdLineOpts__.plugopts:
            # split up "general.syslogsize=5"
            try:
                opt, val = opt.split("=")
            except:
                val = True
            else:
                if val.lower() in ["off", "disable", "disabled", "false"]:
                    val = False
                else:
                    # try to convert string "val" to int()
                    try:
                        val = int(val)
                    except:
                        pass

            # split up "general.syslogsize"
            try:
                plug, opt = opt.split(".")
            except:
                plug = opt
                opt = True

            try:
                opts[plug]
            except KeyError: 
                opts[plug] = deque() 
            opts[plug].append( (opt, val) )

        for plugname, plug in GlobalVars.loadedplugins:
            if plugname in opts:
                for opt, val in opts[plugname]:
                    if not plug.setOption(opt, val):
                        soslog.error('no such option "%s" for plugin ' \
                                     '(%s)' % (opt,plugname))
                        doExit(1)
                del opts[plugname]
        for plugname in opts.keys():
            soslog.error('unable to set option for disabled or non-existing ' \
                         'plugin (%s)' % (plugname))
            # Do not want to exit on invalid opts due to a misconfiguration in sos.conf
            # doExit(1)
        del opt, opts, val

    # error if the user references a plugin which does not exist
    unk_plugs =  [plugname.split(".")[0] for plugname in \
                 GlobalVars.__cmdLineOpts__.onlyplugins \
                 if not plugname.split(".")[0] in plugin_names]
    unk_plugs += [plugname.split(".")[0] for plugname in \
                 GlobalVars.__cmdLineOpts__.noplugins \
                 if not plugname.split(".")[0] in plugin_names]
    unk_plugs += [plugname.split(".")[0] for plugname in \
                 GlobalVars.__cmdLineOpts__.enableplugins \
                 if not plugname.split(".")[0] in plugin_names]
    if len(unk_plugs):
        for plugname in unk_plugs:
            soslog.error('a non-existing plugin (%s) was specified in the ' \
                         'command line' % (plugname))
        doExit(1)
    del unk_plugs

    for plugname, plug in GlobalVars.loadedplugins:
        names, parms = plug.getAllOptions()
        for optname, optparm  in zip(names, parms):
            alloptions.append((plug, plugname, optname, optparm))

    # when --listplugins is specified we do a dry-run
    # which tells the user which plugins are going to be enabled
    # and with what options.

    if GlobalVars.__cmdLineOpts__.listPlugins:
        if not len(GlobalVars.loadedplugins) and not len(skippedplugins):
            soslog.error(_("no valid plugins found"))
            doExit(1)

        if len(GlobalVars.loadedplugins):
            print _("The following plugins are currently enabled:")
            print
            for (plugname, plug) in GlobalVars.loadedplugins:
                print " %-25s  %s" % (textcolor(plugname,"lblue"),
                                     plug.get_description())
        else:
            print _("No plugin enabled.")
        print

        if len(skippedplugins):
            print _("The following plugins are currently disabled:")
            print
            for (plugname, plugclass) in skippedplugins:
                print " %-25s  %s" % (textcolor(plugname,"cyan"),
                                     plugclass.get_description())
        print

        if len(alloptions):
            print _("The following plugin options are available:")
            print
            for (plug, plugname, optname, optparm)  in alloptions:
                # format and colorize option value based on its type (int or bool)
                if type(optparm["enabled"]) == bool:
                    if optparm["enabled"] == True:
                        tmpopt = textcolor("on","lred")
                    else:
                        tmpopt = textcolor("off","red")
                elif type(optparm["enabled"]) == int:
                    if optparm["enabled"] > 0:
                        tmpopt = textcolor(optparm["enabled"],"lred")
                    else:
                        tmpopt = textcolor(optparm["enabled"],"red")
                else:
                    tmpopt = optparm["enabled"]

                print " %-21s %-5s %s" % (plugname + "." + optname,
                                          tmpopt, optparm["desc"])
                del tmpopt
        else:
            print _("No plugin options available.")

        print
        doExit()

    # to go anywhere further than listing the
    # plugins we will need root permissions.
    if os.getuid() != 0:
        print _('sosreport requires root permissions to run.')
        doExit(1)

    # we don't need to keep in memory plugins we are not going to use
    del skippedplugins

    if not len(GlobalVars.loadedplugins):
        soslog.error(_("no valid plugins were enabled"))
        doExit(1)

    msg = _("""This utility will collect some detailed  information about the
hardware and setup of your %(distroa)s system.
The information is collected and an archive is  packaged under
/tmp, which you can send to a support representative.
%(distrob)s will use this information for diagnostic purposes ONLY
and it will be considered confidential information.

This process may take a while to complete.
No changes will be made to your system.

""" % {'distroa':__distro__, 'distrob':__distro__})

    if GlobalVars.__cmdLineOpts__.batch:
        print msg
    else:
        msg += _("""Press ENTER to continue, or CTRL-C to quit.\n""")
        try:
            raw_input(msg)
        except: 
            print
            doExit()
    del msg

    if GlobalVars.__cmdLineOpts__.diagnose:
        # Call the diagnose() method for each plugin
        tmpcount = 0
        for plugname, plug in GlobalVars.loadedplugins:
            try:
                plug.diagnose()
            except:
                if GlobalVars.__raisePlugins__:
                    raise
                else:
                    error_log = open(logdir + "/sosreport-plugin-errors.txt", "a")
                    etype, eval, etrace = sys.exc_info()
                    traceback.print_exception(etype, eval, etrace, limit=2, file=sys.stdout)
                    error_log.write(traceback.format_exc())
                    error_log.close()

            tmpcount += len(plug.diagnose_msgs)
        if tmpcount > 0:
            print _("One or more plugins have detected a problem in your " \
                    "configuration.")
            print _("Please review the following messages:")
            print

            fp = open(rptdir + "/diagnose.txt", "w")
            for plugname, plug in GlobalVars.loadedplugins:
                for tmpcount2 in range(0, len(plug.diagnose_msgs)):
                    if tmpcount2 == 0:
                        soslog.warning( textcolor("%s:" % plugname, "red") )
                    soslog.warning("    * %s" % plug.diagnose_msgs[tmpcount2])
                    fp.write("%s: %s\n" % (plugname, plug.diagnose_msgs[tmpcount2]))
            fp.close()

            print
            if not GlobalVars.__cmdLineOpts__.batch:
                try:
                    while True:
                        yorno = raw_input( _("Are you sure you would like to " \
                                             "continue (y/n) ? ") )
                        if yorno == _("y") or yorno == _("Y"):
                            print
                            break
                        elif yorno == _("n") or yorno == _("N"):
                            doExit(0)
                    del yorno
                except KeyboardInterrupt:
                    print
                    doExit(0)

    GlobalVars.policy.preWork()

    # Call the setup() method for each plugin
    for plugname, plug in GlobalVars.loadedplugins:
        try:
            plug.setup()
        except KeyboardInterrupt:
            raise
        except:
            if GlobalVars.__raisePlugins__:
                raise
            else:
                error_log = open(logdir + "/sosreport-plugin-errors.txt", "a")
                etype, eval, etrace = sys.exc_info()
                traceback.print_exception(etype, eval, etrace, limit=2, file=sys.stdout)
                error_log.write(traceback.format_exc())
                error_log.close()

    print _(" Running plugins. Please wait ...")
    print
    plugruncount = 0
    for i in izip(GlobalVars.loadedplugins):
        plugruncount += 1
        plugname, plug = i[0]
        sys.stdout.write("\r  Running %d/%d: %s...        " % (plugruncount, 
                                                              len(GlobalVars.loadedplugins),
                                                              plugname))
        sys.stdout.flush()
        try:
            plug.copyStuff()
        except KeyboardInterrupt:
            raise
        except:
            if GlobalVars.__raisePlugins__:
                raise
            else:
                error_log = open(logdir + "/sosreport-plugin-errors.txt", "a")
                etype, eval, etrace = sys.exc_info()
                traceback.print_exception(etype, eval, etrace, limit=2, file=sys.stdout)
                error_log.write(traceback.format_exc())
                error_log.close()

    print

    if GlobalVars.__cmdLineOpts__.report:
        for plugname, plug in GlobalVars.loadedplugins:
            for oneFile in plug.copiedFiles:
                try:
                    xmlrep.add_file(oneFile["srcpath"], os.stat(oneFile["srcpath"]))
                except:
                    pass

        xmlrep.serialize_to_file(rptdir + "/sosreport.xml")

    if GlobalVars.__cmdLineOpts__.analyze:
        # Call the analyze method for each plugin
        for plugname, plug in GlobalVars.loadedplugins:
            try:
                plug.analyze()
            except:
                # catch exceptions in analyze() and keep working
                pass

    if GlobalVars.__cmdLineOpts__.report:
        # Generate the header for the html output file
        rfd = open(rptdir + "/" + "sosreport.html", "w")
        rfd.write("""
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
            <head>
        <link rel="stylesheet" type="text/css" media="screen" href="donot.css" />
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <title>Sos System Report</title>
            </head>

            <body>
        """)


        # Make a pass to gather Alerts and a list of module names
        allAlerts = deque() 
        plugNames = deque() 
        for plugname, plug in GlobalVars.loadedplugins:
            for alert in plug.alerts:
                allAlerts.append('<a href="#%s">%s</a>: %s' % (plugname, plugname,
                                                               alert))
            plugNames.append(plugname)

        # Create a table of links to the module info
        rfd.write("<hr/><h3>Loaded Plugins:</h3>")
        rfd.write("<table><tr>\n")
        rr = 0
        for i in range(len(plugNames)):
            rfd.write('<td><a href="#%s">%s</a></td>\n' % (plugNames[i],
                                                           plugNames[i]))
            rr = divmod(i, 4)[1]
            if (rr == 3):
                rfd.write('</tr>')
        if not (rr == 3):
            rfd.write('</tr>')
        rfd.write('</table>\n')

        rfd.write('<hr/><h3>Alerts:</h3>')
        rfd.write('<ul>')
        for alert in allAlerts:
            rfd.write('<li>%s</li>' % alert)
        rfd.write('</ul>')


        # Call the report method for each plugin
        for plugname, plug in GlobalVars.loadedplugins:
            try:
                html = plug.report()
            except:
                if GlobalVars.__raisePlugins__:
                    raise
            else:
                rfd.write(html)

        rfd.write("</body></html>")

        rfd.close()

    # Call the postproc method for each plugin
    for plugname, plug in GlobalVars.loadedplugins:
        try:
            plug.postproc()
        except:
            if GlobalVars.__raisePlugins__:
                raise

    if GlobalVars.__cmdLineOpts__.build:
        print
        print _("  sosreport build tree is located at : %s" % (GlobalVars.dstroot,))
        print
        return GlobalVars.dstroot

    # package up the results for the support organization
    GlobalVars.policy.packageResults()

    # delete gathered files
    GlobalVars.policy.cleanDstroot()

    # let's encrypt the tar-ball
    #if GlobalVars.__cmdLineOpts__.encrypt:
    #   policy.encryptResults()

    # automated submission will go here
    if not GlobalVars.__cmdLineOpts__.upload:
        GlobalVars.policy.displayResults()
    else:
        GlobalVars.policy.uploadResults()

    # Close all log files and perform any cleanup
    logging.shutdown()

