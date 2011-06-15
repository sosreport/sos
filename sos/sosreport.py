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

import sys
import traceback
import os
import logging
from optparse import OptionParser, Option
import ConfigParser
import sos.policydummy
from sos.helpers import importPlugin
import signal
from stat import ST_UID, ST_GID, ST_MODE, ST_CTIME, ST_ATIME, ST_MTIME, S_IMODE
from time import strftime, localtime
from collections import deque
from itertools import izip
import distutils.sysconfig

from sos import _sos as _
from sos import __version__

if os.path.isfile('/etc/fedora-release'):
    __distro__ = 'Fedora'
else:
    __distro__ = 'Red Hat Enterprise Linux'

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

class SosOption(Option):
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

    parser = OptionParserExtended(option_class=SosOption)
    parser.add_option("-l", "--list-plugins", action="store_true",
                         dest="listPlugins", default=False,
                         help="list plugins and available plugin options")
    parser.add_option("-n", "--skip-plugins", action="extend",
                         dest="noplugins", type="string",
                         help="skip these plugins", default = deque())
    parser.add_option("-e", "--enable-plugins", action="extend",
                         dest="enableplugins", type="string",
                         help="enable these plugins", default = deque())
    parser.add_option("-o", "--only-plugins", action="extend",
                         dest="onlyplugins", type="string",
                         help="enable these plugins only", default = deque())
    parser.add_option("-k", action="extend",
                         dest="plugopts", type="string",
                         help="plugin options in plugname.option=value format (see -l)")
    parser.add_option("-a", "--alloptions", action="store_true",
                         dest="usealloptions", default=False,
                         help="enable all options for loaded plugins")
    parser.add_option("-u", "--upload", action="store",
                         dest="upload", default=False,
                         help="upload the report to an ftp server")
    #parser.add_option("--encrypt", action="store_true",
    #                     dest="encrypt", default=False,
    #                     help="encrypt with GPG using Red Hat support's public key")
    parser.add_option("--batch", action="store_true",
                         dest="batch", default=False,
                         help="do not ask any question (batch mode)")
    parser.add_option("--build", action="store_true",
                         dest="build", default=False,
                         help="keep sos tree available and dont package results")
    parser.add_option("--no-colors", action="store_true",
                         dest="nocolors", default=False,
                         help="do not use terminal colors for text")
    parser.add_option("-v", "--verbose", action="count",
                         dest="verbosity",
                         help="increase verbosity")
    parser.add_option("--debug", action="count",
                         dest="debug",
                         help="enabling debugging through python debugger")
    parser.add_option("--ticket-number", action="store",
                         dest="ticketNumber",
                         help="set ticket number")
    parser.add_option("--name", action="store",
                         dest="customerName",
                         help="define customer name")
    parser.add_option("--config-file", action="store",
                         dest="config_file",
                         help="specify alternate configuration file")
    parser.add_option("--tmp-dir", action="store",
                         dest="tmp_dir",
                         help="specify alternate temporary directory", default="/tmp")
    parser.add_option("--diagnose", action="store_true",
                         dest="diagnose",
                         help="enable diagnostics", default=False)
    parser.add_option("--analyze", action="store_true",
                         dest="analyze",
                         help="enable analyzations", default=False)
    parser.add_option("--report", action="store_true",
                         dest="report",
                         help="Enable html/xml reporting", default=False)
    parser.add_option("--profile", action="store_true",
                         dest="profiler",
                         help="turn on profiling", default=False)

    return parser.parse_args(opts)


class XmlReport(object):
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


class SoSReport(object):

    msg = _("""This utility will collect some detailed  information about the
hardware and setup of your %(distroa)s system.
The information is collected and an archive is  packaged under
/tmp, which you can send to a support representative.
%(distrob)s will use this information for diagnostic purposes ONLY
and it will be considered confidential information.

This process may take a while to complete.
No changes will be made to your system.

""" % {'distroa':__distro__, 'distrob':__distro__})

    def __init__(self, opts):
        self.loaded_plugins = deque()
        self.skipped_plugins = deque()
        self.all_options = deque()
        self.xml_report = XmlReport()

        signal.signal(signal.SIGTERM, self.get_exit_handler())

        self.opts, self.args = parse_options(opts)
        self._set_debug()
        self._read_config()
        self.policy = self.load_policy()
        self._set_directories()
        self._setup_logging()
        self.policy.setCommons(self.get_commons())
        self.print_header()
        self.load_plugins()
        self._set_tunables()
        self._check_for_unknown_plugins()
        self._set_plugin_options()

    def print_header(self):
        print "\n%s\n" % _("sosreport (version %s)" % (__version__,))

    def textcolor(self, text, color, raw=0):
        """ Terminal text coloring function """
        if self.opts.nocolors or not sys.stdout.isatty():
            return text
        colors = {  "black":"30", "red":"31", "green":"32", "brown":"33", "blue":"34",
                    "purple":"35", "cyan":"36", "lgray":"37", "gray":"1;30", "lred":"1;31",
                    "lgreen":"1;32", "yellow":"1;33", "lblue":"1;34", "pink":"1;35",
                    "lcyan":"1;36", "white":"1;37" }
        opencol = "\033["
        closecol = "m"
        clear = opencol + "0" + closecol
        f = opencol + colors[color] + closecol
        return "%s%s%s" % (f, text, clear)

    def get_commons(self):
        return {'dstroot': self.dstroot,
                'cmddir': self.cmddir,
                'logdir': self.logdir,
                'rptdir': self.rptdir,
                'soslog': self.soslog,
                'policy': self.policy,
                'verbosity': self.opts.verbosity,
                'xmlreport': self.xml_report,
                'cmdlineopts': self.opts,
                'config': self.config }

    def _set_directories(self):
        self.dstroot = self.policy.getDstroot(self.opts.tmp_dir)
        if not self.dstroot:
            print _("Could not create temporary directory.")
            self._exit()

        self.cmddir = os.path.join(self.dstroot,
                                   'sos_commands')
        self.logdir = os.path.join(self.dstroot,
                                   'sos_logs')
        self.rptdir = os.path.join(self.dstroot,
                                   'sos_reports')
        os.mkdir(self.cmddir, 0755)
        os.mkdir(self.logdir, 0755)
        os.mkdir(self.rptdir, 0755)

    def _set_debug(self):
        if self.opts.debug:
            sys.excepthook = self._exception
            self.raise_plugins = True
        else:
            self.raise_plugins = False

    @staticmethod
    def _exception(etype, eval_, etrace):
        """ Wrap exception in debugger if not in tty """
        if hasattr(sys, 'ps1') or not sys.stderr.isatty():
            # we are in interactive mode or we don't have a tty-like
            # device, so we call the default hook
            sys.__excepthook__(etype, eval_, etrace)
        else:
            import traceback, pdb
            # we are NOT in interactive mode, print the exception...
            traceback.print_exception(etype, eval_, etrace, limit=2, file=sys.stdout)
            print
            # ...then start the debugger in post-mortem mode.
            pdb.pm()

    def _exit(self, error=0):
        try:
            self.policy.cleanDstroot()
        finally:
            sys.exit(error)

    def _exit_nice(self):
        for plugname, plugin in self.loaded_plugins:
            plugin.exit_please()
        print "All processes ended, cleaning up."
        self._exit(1)

    def get_exit_handler(self):
        def exit_handler(signum, frame):
            self._exit_nice()
        return exit_handler

    def _read_config(self):
        self.config = ConfigParser.ConfigParser()
        if self.opts.config_file:
            config_file = self.opts.config_file
        else:
            config_file = '/etc/sos.conf'
        try:
            self.config.readfp(open(config_file))
        except IOError:
            pass

    def load_policy(self):
        return sos.policydummy.SosPolicy()

    def _setup_logging(self):
        self.soslog = logging.getLogger('sos')
        self.soslog.setLevel(logging.DEBUG)

        logging.VERBOSE  = logging.INFO - 1
        logging.VERBOSE2 = logging.INFO - 2
        logging.VERBOSE3 = logging.INFO - 3
        logging.addLevelName(logging.VERBOSE, "verbose")
        logging.addLevelName(logging.VERBOSE2,"verbose2")
        logging.addLevelName(logging.VERBOSE3,"verbose3")

        if self.opts.profiler:
            self.proflog = logging.getLogger('sosprofile')
            self.proflog.setLevel(logging.DEBUG)

        # if stdin is not a tty, disable colors and don't ask questions
        if not sys.stdin.isatty():
            self.opts.nocolors = True
            self.opts.batch = True

        # log to a file
        flog = logging.FileHandler(os.path.join(self.logdir, "sos.log"))
        flog.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        flog.setLevel(logging.VERBOSE3)
        self.soslog.addHandler(flog)

        if self.opts.profiler:
            # setup profile log
            plog = logging.FileHandler(os.path.join(logdir, "sosprofile.log"))
            plog.setFormatter(logging.Formatter('%(message)s'))
            plog.setLevel(logging.DEBUG)
            self.proflog.addHandler(plog)

        # define a Handler which writes INFO messages or higher to the sys.stderr
        console = logging.StreamHandler(sys.stderr)
        if self.opts.verbosity > 0:
            console.setLevel(20 - self.opts.verbosity)
        else:
            console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter('%(message)s'))
        self.soslog.addHandler(console)


    def _get_disabled_plugins(self):
        disabled = []
        if self.config.has_option("plugins", "disable"):
            disabled = [plugin.strip() for plugin in
                        self.config.get("plugins", "disable").split(',')]
        return disabled


    def _is_skipped(self, plugin_name):
        return (plugin_name in self.opts.noplugins or
                plugin_name in self._get_disabled_plugins())

    def _is_inactive(self, plugin_name, pluginClass):
        return (not pluginClass(self.get_commons()).checkenabled() and
                not plugin_name in self.opts.enableplugins  and
                not plugin_name in self.opts.onlyplugins)

    def _is_not_default(self, plugin_name, pluginClass):
        return (not pluginClass(self.get_commons()).defaultenabled() and
                not plugin_name in self.opts.enableplugins and
                not plugin_name in self.opts.onlyplugins)

    def _is_not_specified(self, plugin_name):
        return (self.opts.onlyplugins and
                not plugin_name in self.opts.onlyplugins)

    def _skip(self, plugin_class):
        self.skipped_plugins.append((
            plugin_class.name(),
            plugin_class(self.get_commons())
        ))

    def _load(self, plugin_class):
        self.loaded_plugins.append((
            plugin_class.name(),
            plugin_class(self.get_commons())
        ))

    def _find_pluginpath(self):
        for path in sys.path:
            candidate = os.path.join(path, 'sos', 'plugins')
            if os.path.exists(candidate):
                return candidate

    def load_plugins(self):
        pluginpath = self._find_pluginpath()

        if not pluginpath:
            print _("Could not find a valid plugin path.")
            self._exit()

        self.soslog.info(_("Plugin path is %s") % pluginpath)

        plugins = [plugin for plugin in os.listdir(pluginpath) if plugin.endswith(".py")]
        plugins.sort()
        self.plugin_names = deque()

        # validate and load plugins
        for plug in plugins:
            plugbase, ext = os.path.splitext(plug)
            if plugbase == "__init__":
                continue
            try:
                if self.policy.validatePlugin(pluginpath + plug):
                    pluginClass = importPlugin(plugbase)
                else:
                    self.soslog.warning(_("plugin %s does not validate, skipping") % plug)
                    self._skip(pluginClass)
                    continue

                # plug-in is valid, let's decide whether run it or not
                self.plugin_names.append(plugbase)

                if any((self._is_skipped(plugbase),
                        self._is_inactive(plugbase, pluginClass),
                        self._is_not_default(plugbase, pluginClass),
                        self._is_not_specified(plugbase),
                        )):
                    self._skip(pluginClass)
                    continue

                self._load(pluginClass)
            except Exception, e:
                self.soslog.warning(_("plugin %s does not install, skipping: %s") % (plug, e))
                if self.raise_plugins:
                    raise

    def _set_all_options(self):
        if self.opts.usealloptions:
            for plugname, plug in self.loaded_plugins:
                for name, parms in zip(plug.optNames, plug.optParms):
                    if type(parms["enabled"])==bool:
                        parms["enabled"] = True

    def _set_tunables(self):
        if self.config.has_section("tunables"):
            if not self.opts.plugopts:
                self.opts.plugopts = deque()

            for opt, val in self.config.items("tunables"):
                if not opt.split('.')[0] in self.disabled:
                    self.opts.plugopts.append(opt + "=" + val)
        if self.opts.plugopts:
            opts = {}
            for opt in self.opts.plugopts:
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

            for plugname, plug in self.loaded_plugins:
                if plugname in opts:
                    for opt, val in opts[plugname]:
                        if not plug.setOption(opt, val):
                            self.soslog.error('no such option "%s" for plugin '
                                         '(%s)' % (opt,plugname))
                            self._exit(1)
                    del opts[plugname]
            for plugname in opts.keys():
                self.soslog.error('unable to set option for disabled or non-existing '
                             'plugin (%s)' % (plugname))

    def _check_for_unknown_plugins(self):
        import itertools
        for plugin in itertools.chain(self.opts.onlyplugins,
                                      self.opts.noplugins,
                                      self.opts.enableplugins):
            plugin_name = plugin.split(".")[0]
            if not plugin_name in self.plugin_names:
                soslog.error('a non-existing plugin (%s) was specified in the '
                             'command line' % (plugin_name))
                self._exit(1)

    def _set_plugin_options(self):
        for plugin_name, plugin in self.loaded_plugins:
            names, parms = plugin.getAllOptions()
            for optname, optparm in zip(names, parms):
                self.all_options.append((plugin, plugin_name, optname, optparm))

    def list_plugins(self):
        if not self.loaded_plugins and not self.skipped_plugins:
            self.soslog.error(_("no valid plugins found"))
            self._exit(1)

        if self.loaded_plugins:
            print _("The following plugins are currently enabled:")
            print
            for (plugname, plug) in self.loaded_plugins:
                print " %-25s  %s" % (self.textcolor(plugname,"lblue"),
                                     plug.get_description())
        else:
            print _("No plugin enabled.")
        print

        if self.skipped_plugins:
            print _("The following plugins are currently disabled:")
            print
            for (plugname, plugclass) in self.skipped_plugins:
                print " %-25s  %s" % (self.textcolor(plugname,"cyan"),
                                     plugclass.get_description())
        print

        if self.all_options:
            print _("The following plugin options are available:")
            print
            for (plug, plugname, optname, optparm)  in self.all_options:
                # format and colorize option value based on its type (int or bool)
                if type(optparm["enabled"]) == bool:
                    if optparm["enabled"] == True:
                        tmpopt = self.textcolor("on","lred")
                    else:
                        tmpopt = self.textcolor("off","red")
                elif type(optparm["enabled"]) == int:
                    if optparm["enabled"] > 0:
                        tmpopt = self.textcolor(optparm["enabled"],"lred")
                    else:
                        tmpopt = self.textcolor(optparm["enabled"],"red")
                else:
                    tmpopt = optparm["enabled"]

                print " %-21s %-5s %s" % (plugname + "." + optname,
                                          tmpopt, optparm["desc"])
        else:
            print _("No plugin options available.")

        print
        self._exit()

    def batch(self):
        if self.opts.batch:
            print self.msg
        else:
            self.msg += _("Press ENTER to continue, or CTRL-C to quit.\n")
            try:
                raw_input(self.msg)
            except:
                print
                self._exit()

    def _exception_to_logfile(self, logfile_name):
        error_log = open(logfile_name, 'a')
        etype, eval, etrace = sys.exc_info()
        traceback.print_exception(etype, eval, etrace, limit=2, file=sys.stdout)
        error_log.write(traceback.format_exc())
        error_log.close()

    def _log_plugin_exception(self):
        self._exception_to_logfile(
            os.path.join(self.logdir, "sosreport-plugin-errors.txt"))

    def diagnose(self):
        tmpcount = 0
        for plugname, plug in GlobalVars.loadedplugins:
            try:
                plug.diagnose()
            except:
                if self.raise_plugins:
                    raise
                else:
                    self._log_plugin_exception()

            tmpcount += len(plug.diagnose_msgs)
        if tmpcount > 0:
            print _("One or more plugins have detected a problem in your "
                    "configuration.")
            print _("Please review the following messages:")
            print

            fp = open(os.path.join(rptdir, "diagnose.txt"), "w")
            for plugname, plug in self.loaded_plugins:
                for tmpcount2 in range(0, len(plug.diagnose_msgs)):
                    if tmpcount2 == 0:
                        soslog.warning( self.textcolor("%s:" % plugname, "red") )
                    soslog.warning("    * %s" % plug.diagnose_msgs[tmpcount2])
                    fp.write("%s: %s\n" % (plugname, plug.diagnose_msgs[tmpcount2]))
            fp.close()

            print
            if not self.opts.batch:
                try:
                    while True:
                        yorno = raw_input( _("Are you sure you would like to "
                                             "continue (y/n) ? ") )
                        if yorno == _("y") or yorno == _("Y"):
                            print
                            break
                        elif yorno == _("n") or yorno == _("N"):
                            self._exit(0)
                    del yorno
                except KeyboardInterrupt:
                    print
                    self._exit(0)

    def prework(self):
        self.policy.preWork()


    def setup(self):
        for plugname, plug in self.loaded_plugins:
            try:
                plug.setup()
            except KeyboardInterrupt:
                raise
            except:
                if self.raise_plugins:
                    raise
                else:
                    self._log_plugin_exception()

    def copy_stuff(self):
        plugruncount = 0
        for i in izip(self.loaded_plugins):
            plugruncount += 1
            plugname, plug = i[0]
            sys.stdout.write("\r  Running %d/%d: %s...        " % (plugruncount,
                                                                  len(self.loaded_plugins),
                                                                  plugname))
            sys.stdout.flush()
            try:
                plug.copyStuff()
            except KeyboardInterrupt:
                raise
            except:
                if self.raise_plugins:
                    raise
                else:
                    self._log_plugin_exception()

    def report(self):
        for plugname, plug in self.loaded_plugins:
            for oneFile in plug.copiedFiles:
                try:
                    xmlrep.add_file(oneFile["srcpath"], os.stat(oneFile["srcpath"]))
                except:
                    pass

        self.xml_report.serialize_to_file(
            os.path.join(self.rptdir, "sosreport.xml"))

    def html_report(self):
        # Generate the header for the html output file
        rfd = open(os.path.join(self.rptdir, "sosreport.html"), "w")
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
        for plugname, plug in self.loaded_plugins:
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
        for plugname, plug in self.loaded_plugins:
            try:
                html = plug.report()
            except:
                if self.raise_plugins:
                    raise
            else:
                rfd.write(html)

        rfd.write("</body></html>")

        rfd.close()

    def postproc(self):
        for plugname, plug in self.loaded_plugins:
            try:
                plug.postproc()
            except:
                if self.raise_plugins:
                    raise

    def final_work(self):

        if self.opts.build:
            print
            print _("  sosreport build tree is located at : %s" % (self.dstroot,))
            print
            sys.exit(0)

        # package up the results for the support organization
        self.policy.packageResults()

        # delete gathered files
        self.policy.cleanDstroot()

        # let's encrypt the tar-ball
        #if self.__cmdLineOpts__.encrypt:
        #   policy.encryptResults()

        # automated submission will go here
        if not self.opts.upload:
            self.policy.displayResults()
        else:
            self.policy.uploadResults()

        # Close all log files and perform any cleanup
        logging.shutdown()

    def ensure_root(self):
        if os.getuid() != 0:
            print _("sosreport requires root permissions to run.")
            self._exit(1)

    def ensure_plugins(self):
        if not self.loaded_plugins:
            self.soslog.error(_("no valid plugins were enabled"))
            self._exit(1)

def main(args):
    """The main entry point"""
    sos = SoSReport(args)
    if sos.opts.listPlugins:
        sos.list_plugins()

    sos.ensure_root()
    sos.ensure_plugins()
    sos.batch()

    if sos.opts.diagnose:
        sos.diagnose()

    sos.prework()
    sos.setup()

    print _(" Running plugins. Please wait ...")
    print

    sos.copy_stuff()

    print

    if sos.opts.report:
        sos.report()
        sos.html_report()

    sos.postproc()

    sos.final_work()
