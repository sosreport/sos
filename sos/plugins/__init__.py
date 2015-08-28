# Copyright (C) 2006 Steve Conklin <sconklin@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

""" This exports methods available for use by plugins for sos """

from __future__ import with_statement

from sos.utilities import (sos_get_command_output, import_module, grep,
                           fileobj, tail)
import os
import glob
import re
import stat
from time import time
import logging
import fnmatch
import errno

# PYCOMPAT
import six
from six.moves import zip, filter


def regex_findall(regex, fname):
    '''Return a list of all non overlapping matches in the string(s)'''
    try:
        with fileobj(fname) as f:
            return re.findall(regex, f.read(), re.MULTILINE)
    except AttributeError:
        return []


def _mangle_command(command, name_max):
    mangledname = re.sub(r"^/(usr/|)(bin|sbin)/", "", command)
    mangledname = re.sub(r"[^\w\-\.\/]+", "_", mangledname)
    mangledname = re.sub(r"/", ".", mangledname).strip(" ._-")
    mangledname = mangledname[0:name_max]
    return mangledname


def _path_in_path_list(path, path_list):
    return any(p in path for p in path_list)


def _node_type(st):
    """ return a string indicating the type of special node represented by
    the stat buffer st (block, character, fifo, socket).
    """
    _types = [
        (stat.S_ISBLK, "block device"),
        (stat.S_ISCHR, "character device"),
        (stat.S_ISFIFO, "named pipe"),
        (stat.S_ISSOCK, "socket")
    ]
    for t in _types:
        if t[0](st.st_mode):
            return t[1]


class Plugin(object):
    """ This is the base class for sosreport plugins. Plugins should subclass
    this and set the class variables where applicable.

    plugin_name is a string returned by plugin.name(). If this is set to None
    (the default) class_.__name__.tolower() will be returned. Be sure to set
    this if you are defining multiple plugins that do the same thing on
    different platforms.

    requires_root is a boolean that specifies whether or not sosreport should
    execute this plugin as a super user.

    version is a string representing the version of the plugin. This can be
    useful for post-collection tooling.

    packages (files) is an iterable of the names of packages (the paths
    of files) to check for before running this plugin. If any of these packages
    or files is found on the system, the default implementation of
    check_enabled will return True.

    profiles is an iterable of profile names that this plugin belongs to.
    Whenever any of the profiles is selected on the command line the plugin
    will be enabled (subject to normal check_enabled tests).
    """

    plugin_name = None
    requires_root = True
    version = 'unversioned'
    packages = ()
    files = ()
    archive = None
    profiles = ()
    sysroot = '/'

    def __init__(self, commons):
        if not getattr(self, "option_list", False):
            self.option_list = []

        self.copied_files = []
        self.executed_commands = []
        self.alerts = []
        self.custom_text = ""
        self.opt_names = []
        self.opt_parms = []
        self.commons = commons
        self.forbidden_paths = []
        self.copy_paths = set()
        self.copy_strings = []
        self.collect_cmds = []
        self.sysroot = commons['sysroot']

        self.soslog = self.commons['soslog'] if 'soslog' in self.commons \
            else logging.getLogger('sos')

        # get the option list into a dictionary
        for opt in self.option_list:
            self.opt_names.append(opt[0])
            self.opt_parms.append({'desc': opt[1], 'speed': opt[2],
                                   'enabled': opt[3]})

    @classmethod
    def name(class_):
        """Returns the plugin's name as a string. This should return a
        lowercase string.
        """
        if class_.plugin_name:
            return class_.plugin_name
        return class_.__name__.lower()

    def _format_msg(self, msg):
        return "[plugin:%s] %s" % (self.name(), msg)

    def _log_error(self, msg):
        self.soslog.error(self._format_msg(msg))

    def _log_warn(self, msg):
        self.soslog.warning(self._format_msg(msg))

    def _log_info(self, msg):
        self.soslog.info(self._format_msg(msg))

    def _log_debug(self, msg):
        self.soslog.debug(self._format_msg(msg))

    def policy(self):
        return self.commons["policy"]

    def join_sysroot(self, path):
        if path[0] == os.sep:
            path = path[1:]
        return os.path.join(self.sysroot, path)

    def strip_sysroot(self, path):
        if not self.use_sysroot():
            return path
        if path.startswith(self.sysroot):
            return path[len(self.sysroot):]
        return path

    def use_sysroot(self):
        return self.sysroot != os.path.abspath(os.sep)

    def tmp_in_sysroot(self):
        paths = [self.sysroot, self.archive.get_tmp_dir()]
        return os.path.commonprefix(paths) == self.sysroot

    def is_installed(self, package_name):
        '''Is the package $package_name installed?'''
        return self.policy().pkg_by_name(package_name) is not None

    def do_cmd_output_sub(self, cmd, regexp, subst):
        '''Apply a regexp substitution to command output archived by sosreport.
        cmd is the command name from which output is collected (i.e. excluding
        parameters). The regexp can be a string or a compiled re object. The
        substitution string, subst, is a string that replaces each occurrence
        of regexp in each file collected from cmd. Internally 'cmd' is treated
        as a glob with a leading and trailing '*' and each matching file from
        the current module's command list is subjected to the replacement.

        This function returns the number of replacements made.
        '''
        globstr = '*' + cmd + '*'
        self._log_debug("substituting '%s' for '%s' in commands matching '%s'"
                        % (subst, regexp, globstr))

        if not self.executed_commands:
            return 0

        replacements = None
        try:
            for called in self.executed_commands:
                # was anything collected?
                if called['file'] is None:
                    continue
                if fnmatch.fnmatch(called['exe'], globstr):
                    path = os.path.join(self.commons['cmddir'], called['file'])
                    self._log_debug("applying substitution to '%s'" % path)
                    readable = self.archive.open_file(path)
                    result, replacements = re.subn(
                        regexp, subst, readable.read())
                    if replacements:
                        self.archive.add_string(result, path)

        except Exception as e:
            msg = "regex substitution failed for '%s' with: '%s'"
            self._log_error(msg % (called['exe'], e))
            replacements = None
        return replacements

    def do_file_sub(self, srcpath, regexp, subst):
        '''Apply a regexp substitution to a file archived by sosreport.
        srcpath is the path in the archive where the file can be found.  regexp
        can be a regexp string or a compiled re object.  subst is a string to
        replace each occurance of regexp in the content of srcpath.

        This function returns the number of replacements made.
        '''
        try:
            path = self._get_dest_for_srcpath(srcpath)
            self._log_debug("substituting scrpath '%s'" % srcpath)
            self._log_debug("substituting '%s' for '%s' in '%s'"
                            % (subst, regexp, path))
            if not path:
                return 0
            readable = self.archive.open_file(path)
            result, replacements = re.subn(regexp, subst, readable.read())
            if replacements:
                self.archive.add_string(result, srcpath)
            else:
                replacements = 0
        except Exception as e:
            msg = "regex substitution failed for '%s' with: '%s'"
            self._log_error(msg % (path, e))
            replacements = 0
        return replacements

    def do_path_regex_sub(self, pathexp, regexp, subst):
        '''Apply a regexp substituation to a set of files archived by
        sos. The set of files to be substituted is generated by matching
        collected file pathnames against pathexp which may be a regular
        expression string or compiled re object. The portion of the file
        to be replaced is specified via regexp and the replacement string
        is passed in subst.'''
        if not hasattr(pathexp, "match"):
            pathexp = re.compile(pathexp)
        match = pathexp.match
        file_list = [f for f in self.copied_files if match(f['srcpath'])]
        for file in file_list:
            self.do_file_sub(file['srcpath'], regexp, subst)

    def do_regex_find_all(self, regex, fname):
        return regex_findall(regex, fname)

    def _copy_symlink(self, srcpath):
        # the target stored in the original symlink
        linkdest = os.readlink(srcpath)
        dest = os.path.join(os.path.dirname(srcpath), linkdest)
        # Absolute path to the link target. If SYSROOT != '/' this path
        # is relative to the host root file system.
        absdest = os.path.normpath(dest)
        # adjust the target used inside the report to always be relative
        if os.path.isabs(linkdest):
            reldest = os.path.relpath(linkdest, os.path.dirname(srcpath))
            # trim leading /sysroot
            if self.use_sysroot():
                reldest = reldest[len(os.sep + os.pardir):]
            self._log_debug("made link target '%s' relative as '%s'"
                            % (linkdest, reldest))
        else:
            reldest = linkdest

        self._log_debug("copying link '%s' pointing to '%s' with isdir=%s"
                        % (srcpath, linkdest, os.path.isdir(absdest)))

        dstpath = self.strip_sysroot(srcpath)
        # use the relative target path in the tarball
        self.archive.add_link(reldest, dstpath)

        if os.path.isdir(absdest):
            self._log_debug("link '%s' is a directory, skipping..." % linkdest)
            return

        # copy the symlink target translating relative targets
        # to absolute paths to pass to _do_copy_path.
        self._log_debug("normalized link target '%s' as '%s'"
                        % (linkdest, absdest))

        # skip recursive copying of symlink pointing to itself.
        if (absdest != srcpath):
            self._do_copy_path(self.strip_sysroot(absdest))
        else:
            self._log_debug("link '%s' points to itself, skipping target..."
                            % linkdest)

        self.copied_files.append({'srcpath': srcpath,
                                  'dstpath': dstpath,
                                  'symlink': "yes",
                                  'pointsto': linkdest})

    def _copy_dir(self, srcpath):
        try:
            for afile in os.listdir(srcpath):
                self._log_debug("recursively adding '%s' from '%s'"
                                % (afile, srcpath))
                self._do_copy_path(os.path.join(srcpath, afile), dest=None)
        except OSError as e:
            if e.errno == errno.ELOOP:
                msg = "Too many levels of symbolic links copying"
                self._log_error("_copy_dir: %s '%s'" % (msg, srcpath))
                return
            raise e

    def _get_dest_for_srcpath(self, srcpath):
        if self.use_sysroot():
            srcpath = self.join_sysroot(srcpath)
        for copied in self.copied_files:
            if srcpath == copied["srcpath"]:
                return copied["dstpath"]
        return None

    def _is_forbidden_path(self, path):
        if self.use_sysroot():
            path = self.join_sysroot(path)
        return _path_in_path_list(path, self.forbidden_paths)

    def _copy_node(self, path, st):
        dev_maj = os.major(st.st_rdev)
        dev_min = os.minor(st.st_rdev)
        mode = st.st_mode
        self.archive.add_node(path, mode, os.makedev(dev_maj, dev_min))

    # Methods for copying files and shelling out
    def _do_copy_path(self, srcpath, dest=None):
        '''Copy file or directory to the destination tree. If a directory, then
        everything below it is recursively copied. A list of copied files are
        saved for use later in preparing a report.
        '''
        if self._is_forbidden_path(srcpath):
            self._log_debug("skipping forbidden path '%s'" % srcpath)
            return ''

        if not dest:
            dest = srcpath

        if self.use_sysroot():
            dest = self.strip_sysroot(dest)

        try:
            st = os.lstat(srcpath)
        except (OSError, IOError):
            self._log_info("failed to stat '%s'" % srcpath)
            return

        if stat.S_ISLNK(st.st_mode):
            self._copy_symlink(srcpath)
            return
        else:
            if stat.S_ISDIR(st.st_mode):
                self._copy_dir(srcpath)
                return

        # handle special nodes (block, char, fifo, socket)
        if not (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)):
            ntype = _node_type(st)
            self._log_debug("creating %s node at archive:'%s'"
                            % (ntype, dest))
            self._copy_node(srcpath, st)
            return

        # if we get here, it's definitely a regular file (not a symlink or dir)
        self._log_debug("copying path '%s' to archive:'%s'" % (srcpath, dest))

        # if not readable(srcpath)
        if not st.st_mode & 0o444:
            # FIXME: reflect permissions in archive
            self.archive.add_string("", dest)
        else:
            self.archive.add_file(srcpath, dest)

        self.copied_files.append({
            'srcpath': srcpath,
            'dstpath': dest,
            'symlink': "no"
        })

    def add_forbidden_path(self, forbidden):
        """Specify a path to not copy, even if it's part of a copy_specs[]
        entry.
        """
        if self.use_sysroot():
            forbidden = self.join_sysroot(forbidden)
        # Glob case handling is such that a valid non-glob is a reduced glob
        for path in glob.glob(forbidden):
            self.forbidden_paths.append(path)

    def get_all_options(self):
        """return a list of all options selected"""
        return (self.opt_names, self.opt_parms)

    def set_option(self, optionname, value):
        '''set the named option to value.'''
        for name, parms in zip(self.opt_names, self.opt_parms):
            if name == optionname:
                parms['enabled'] = value
                return True
        else:
            return False

    def get_option(self, optionname, default=0):
        """Returns the first value that matches 'optionname' in parameters
        passed in via the command line or set via set_option or via the
        global_plugin_options dictionary, in that order.

        optionaname may be iterable, in which case the first option that
        matches any of the option names is returned.
        """

        global_options = ('verify', 'all_logs', 'log_size')

        if optionname in global_options:
            return getattr(self.commons['cmdlineopts'], optionname)

        def _check(key):
            if hasattr(optionname, "__iter__"):
                return key in optionname
            else:
                return key == optionname

        for name, parms in zip(self.opt_names, self.opt_parms):
            if _check(name):
                val = parms['enabled']
                if val is not None:
                    return val

        items = six.iteritems(self.commons.get('global_plugin_options', {}))
        for key, value in items:
            if _check(key):
                return value

        return default

    def get_option_as_list(self, optionname, delimiter=",", default=None):
        '''Will try to return the option as a list separated by the
        delimiter.
        '''
        option = self.get_option(optionname)
        try:
            opt_list = [opt.strip() for opt in option.split(delimiter)]
            return list(filter(None, opt_list))
        except Exception:
            return default

    def _add_copy_paths(self, copy_paths):
        self.copy_paths.update(copy_paths)

    def add_copy_spec_limit(self, copyspec, sizelimit=None, tailit=True):
        """Add a file or glob but limit it to sizelimit megabytes. If fname is
        a single file the file will be tailed to meet sizelimit. If the first
        file in a glob is too large it will be tailed to meet the sizelimit.
        """
        if not (copyspec and len(copyspec)):
            return False

        if self.use_sysroot():
            copyspec = self.join_sysroot(copyspec)
        files = glob.glob(copyspec)
        files.sort()
        if len(files) == 0:
            return

        current_size = 0
        limit_reached = False
        sizelimit *= 1024 * 1024  # in MB
        _file = None

        for _file in files:
            current_size += os.stat(_file)[stat.ST_SIZE]
            if sizelimit and current_size > sizelimit:
                limit_reached = True
                break
            self._add_copy_paths([_file])

        if limit_reached and tailit:
            file_name = _file

            if file_name[0] == os.sep:
                file_name = file_name.lstrip(os.sep)
            strfile = file_name.replace(os.path.sep, ".") + ".tailed"
            self.add_string_as_file(tail(_file, sizelimit), strfile)
            rel_path = os.path.relpath('/', os.path.dirname(_file))
            link_path = os.path.join(rel_path, 'sos_strings',
                                     self.name(), strfile)
            self.archive.add_link(link_path, _file)

    def add_copy_spec(self, copyspecs):
        """Add a file specification (can be file, dir,or shell glob) to be
        copied into the sosreport by this module.
        """
        if isinstance(copyspecs, six.string_types):
            copyspecs = [copyspecs]
        for copyspec in copyspecs:
            if self.use_sysroot():
                copyspec = self.join_sysroot(copyspec)
            if not (copyspec and len(copyspec)):
                self._log_warn("added null or empty copy spec")
                return False
            copy_paths = self._expand_copy_spec(copyspec)
            self._add_copy_paths(copy_paths)
            self._log_info("added copyspec '%s'" % copy_paths)

    def get_command_output(self, prog, timeout=300, stderr=True,
                           chroot=True, runat=None):
        if chroot or self.commons['cmdlineopts'].chroot == 'always':
            root = self.sysroot
        else:
            root = None

        result = sos_get_command_output(prog, timeout=timeout, stderr=stderr,
                                        chroot=root, chdir=runat)

        if result['status'] == 124:
            self._log_warn("command '%s' timed out after %ds"
                           % (prog, timeout))

        # command not found or not runnable
        if result['status'] == 126 or result['status'] == 127:
            # automatically retry chroot'ed commands in the host namespace
            if chroot and self.commons['cmdlineopts'].chroot != 'always':
                self._log_info("command '%s' not found in %s - "
                               "re-trying in host root"
                               % (prog.split()[0], root))
                return self.get_command_output(prog, timeout=timeout,
                                               chroot=False, runat=runat)
            self._log_debug("could not run '%s': command not found" % prog)
        return result

    def call_ext_prog(self, prog, timeout=300, stderr=True,
                      chroot=True, runat=None):
        """Execute a command independantly of the output gathering part of
        sosreport.
        """
        return self.get_command_output(prog, timeout=timeout, stderr=stderr,
                                       chroot=chroot, runat=runat)

    def check_ext_prog(self, prog):
        """Execute a command independently of the output gathering part of
        sosreport and check the return code. Return True for a return code of 0
        and False otherwise.
        """
        return self.call_ext_prog(prog)['status'] == 0

    def add_cmd_output(self, cmds, suggest_filename=None,
                       root_symlink=None, timeout=300, stderr=True,
                       chroot=True, runat=None):
        """Run a program or a list of programs and collect the output"""
        if isinstance(cmds, six.string_types):
            cmds = [cmds]
        if len(cmds) > 1 and (suggest_filename or root_symlink):
            self._log_warn("ambiguous filename or symlink for command list")
        for cmd in cmds:
            cmdt = (
                cmd, suggest_filename, root_symlink, timeout, stderr,
                chroot, runat
            )
            _tuplefmt = "('%s', '%s', '%s', %s, '%s', '%s', '%s')"
            _logstr = "packed command tuple: " + _tuplefmt
            self._log_debug(_logstr % cmdt)
            self.collect_cmds.append(cmdt)
            self._log_info("added cmd output '%s'" % cmd)

    def get_cmd_output_path(self, name=None, make=True):
        """Return a path into which this module should store collected
        command output
        """
        cmd_output_path = os.path.join(self.archive.get_tmp_dir(),
                                       'sos_commands', self.name())
        if name:
            cmd_output_path = os.path.join(cmd_output_path, name)
        if make:
            os.makedirs(cmd_output_path)

        return cmd_output_path

    def file_grep(self, regexp, *fnames):
        """Returns lines matched in fnames, where fnames can either be
        pathnames to files to grep through or open file objects to grep through
        line by line.
        """
        return grep(regexp, *fnames)

    def _mangle_command(self, exe):
        name_max = self.archive.name_max()
        return _mangle_command(exe, name_max)

    def _make_command_filename(self, exe):
        """The internal function to build up a filename based on a command."""

        outfn = os.path.join(self.commons['cmddir'], self.name(),
                             self._mangle_command(exe))

        # check for collisions
        if os.path.exists(outfn):
            inc = 2
            while True:
                newfn = "%s_%d" % (outfn, inc)
                if not os.path.exists(newfn):
                    outfn = newfn
                    break
                inc += 1

        return outfn

    def add_string_as_file(self, content, filename):
        """Add a string to the archive as a file named `filename`"""
        self.copy_strings.append((content, filename))
        content = "..." + (content.splitlines()[0]).decode('utf8', 'ignore')
        self._log_debug("added string '%s' as '%s'" % (content, filename))

    def get_cmd_output_now(self, exe, suggest_filename=None,
                           root_symlink=False, timeout=300, stderr=True,
                           chroot=True, runat=None):
        """Execute a command and save the output to a file for inclusion in the
        report.
        """
        start = time()
        result = self.get_command_output(exe, timeout=timeout, stderr=stderr,
                                         chroot=chroot, runat=runat)
        # 126 means 'found but not executable'
        if result['status'] == 126 or result['status'] == 127:
            return None
        self._log_debug("collected output of '%s' in %s"
                        % (exe.split()[0], time() - start))

        if suggest_filename:
            outfn = self._make_command_filename(suggest_filename)
        else:
            outfn = self._make_command_filename(exe)

        outfn_strip = outfn[len(self.commons['cmddir'])+1:]
        self.archive.add_string(result['output'], outfn)
        if root_symlink:
            self.archive.add_link(outfn, root_symlink)

        # save info for later
        # save in our list
        self.executed_commands.append({'exe': exe, 'file': outfn_strip})
        self.commons['xmlreport'].add_command(cmdline=exe,
                                              exitcode=result['status'],
                                              f_stdout=outfn_strip)

        return os.path.join(self.archive.get_archive_path(), outfn)

    def is_module_loaded(self, module_name):
        """Return whether specified moudle as module_name is loaded or not"""
        if len(grep("^" + module_name + " ", "/proc/modules")) == 0:
            return None
        else:
            return True

    # For adding output
    def add_alert(self, alertstring):
        """Add an alert to the collection of alerts for this plugin. These
        will be displayed in the report
        """
        self.alerts.append(alertstring)

    def add_custom_text(self, text):
        """Append text to the custom text that is included in the report. This
        is freeform and can include html.
        """
        self.custom_text += text

    def _expand_copy_spec(self, copyspec):
        return glob.glob(copyspec)

    def _collect_copy_specs(self):
        for path in self.copy_paths:
            self._log_info("collecting path '%s'" % path)
            self._do_copy_path(path)

    def _collect_cmd_output(self):
        for progs in zip(self.collect_cmds):
            (
                prog,
                suggest_filename, root_symlink,
                timeout,
                stderr,
                chroot, runat
            ) = progs[0]
            self._log_debug("unpacked command tuple: " +
                            "('%s', '%s', '%s', %s, '%s', '%s', '%s')" %
                            progs[0])
            self._log_info("collecting output of '%s'" % prog)
            self.get_cmd_output_now(prog, suggest_filename=suggest_filename,
                                    root_symlink=root_symlink, timeout=timeout,
                                    stderr=stderr, chroot=chroot, runat=runat)

    def _collect_strings(self):
        for string, file_name in self.copy_strings:
            content = "..."
            content += (string.splitlines()[0]).decode('utf8', 'ignore')
            self._log_info("collecting string '%s' as '%s'"
                           % (content, file_name))
            try:
                self.archive.add_string(string,
                                        os.path.join('sos_strings',
                                                     self.name(),
                                                     file_name))
            except Exception as e:
                self._log_debug("could not add string '%s': %s"
                                % (file_name, e))

    def collect(self):
        """Collect the data for a plugin."""
        start = time()
        self._collect_copy_specs()
        self._collect_cmd_output()
        self._collect_strings()
        fields = (self.name(), time() - start)
        self._log_debug("collected plugin '%s' in %s" % fields)

    def get_description(self):
        """ This function will return the description for the plugin"""
        try:
            if hasattr(self, '__doc__') and self.__doc__:
                return self.__doc__.strip()
            return super(self.__class__, self).__doc__.strip()
        except:
            return "<no description available>"

    def check_enabled(self):
        """This method will be used to verify that a plugin should execute
        given the condition of the underlying environment. The default
        implementation will return True if neither class.files or
        class.packages is specified. If either are specified the plugin will
        check for the existence of any of the supplied files or packages and
        return True if any exist. It is encouraged to override this method if
        this behavior isn't applicable.
        """
        # some files or packages have been specified for this package
        if self.files or self.packages:
            if isinstance(self.files, six.string_types):
                self.files = [self.files]

            if isinstance(self.packages, six.string_types):
                self.packages = [self.packages]

            return (any(os.path.exists(fname) for fname in self.files) or
                    any(self.is_installed(pkg) for pkg in self.packages))
        return True

    def default_enabled(self):
        """This decides whether a plugin should be automatically loaded or
        only if manually specified in the command line."""
        return True

    def setup(self):
        """Collect the list of files declared by the plugin. This method
        may be overridden to add further copy_specs, forbidden_paths, and
        external programs if required.
        """
        self.add_copy_spec(list(self.files))

    def postproc(self):
        """Perform any postprocessing. To be replaced by a plugin if required.
        """
        pass

    def report(self):
        """ Present all information that was gathered in an html file that
        allows browsing the results.
        """
        # make this prettier
        html = '<hr/><a name="%s"></a>\n' % self.name()

        # Intro
        html = html + "<h2> Plugin <em>" + self.name() + "</em></h2>\n"

        # Files
        if len(self.copied_files):
            html = html + "<p>Files copied:<br><ul>\n"
            for afile in self.copied_files:
                html = html + '<li><a href="%s">%s</a>' % \
                    (".." + afile['dstpath'], afile['srcpath'])
                if afile['symlink'] == "yes":
                    html = html + " (symlink to %s)" % afile['pointsto']
                html = html + '</li>\n'
            html = html + "</ul></p>\n"

        # Command Output
        if len(self.executed_commands):
            html = html + "<p>Commands Executed:<br><ul>\n"
            # convert file name to relative path from our root
            # don't use relpath - these are HTML paths not OS paths.
            for cmd in self.executed_commands:
                if cmd["file"] and len(cmd["file"]):
                    cmd_rel_path = "../" + self.commons['cmddir'] \
                        + "/" + cmd['file']
                    html = html + '<li><a href="%s">%s</a></li>\n' % \
                        (cmd_rel_path, cmd['exe'])
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
        if self.custom_text != "":
            html = html + "<p>Additional Information:<br>\n"
            html = html + self.custom_text + "</p>\n"

        return html


class RedHatPlugin(object):
    """Tagging class for Red Hat's Linux distributions"""
    pass


class PowerKVMPlugin(RedHatPlugin):
    """Tagging class for IBM PowerKVM Linux"""
    pass


class ZKVMPlugin(RedHatPlugin):
    """Tagging class for IBM ZKVM Linux"""
    pass


class UbuntuPlugin(object):
    """Tagging class for Ubuntu Linux"""
    pass


class DebianPlugin(object):
    """Tagging class for Debian Linux"""
    pass


class IndependentPlugin(object):
    """Tagging class for plugins that can run on any platform"""
    pass


class ExperimentalPlugin(object):
    """Tagging class that indicates that this plugin is experimental"""
    pass


def import_plugin(name, superclasses=None):
    """Import name as a module and return a list of all classes defined in that
    module. superclasses should be a tuple of valid superclasses to import,
    this defaults to (Plugin,).
    """
    plugin_fqname = "sos.plugins.%s" % name
    if not superclasses:
        superclasses = (Plugin,)
    return import_module(plugin_fqname, superclasses)

# vim: set et ts=4 sw=4 :
