## helpers.py
## Implement policies required for the sos system support tool

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

## Some code adapted from "Python Cookbook, 2nd ed", by Alex
## Martelli, Anna Martelli Ravenscroft, and David Ascher
## (O'Reilly Media, 2005) 0-596-00797-3
##

"""
helper functions used by sosreport and plugins
"""
import os, popen2, fcntl, select, sys, commands, signal
from time import time, sleep
import logging
from tempfile import mkdtemp

def importPlugin(pluginname, name):
    """ Import a plugin to extend capabilities of sosreport
    """
    try:
        plugin = __import__(pluginname, globals(), locals(), [name])
    except ImportError:
        return None
    return getattr(plugin, name)


def sosFindTmpDir():
    """Find a temp directory to form the root for our gathered information
    and reports.
    """
    workingBase = mkdtemp("","sos_")
    return workingBase


def makeNonBlocking(afd):
    """ Make the file descriptor non-blocking. This prevents deadlocks.
    """
    fl = fcntl.fcntl(afd, fcntl.F_GETFL)
    try:
        fcntl.fcntl(afd, fcntl.F_SETFL, fl | os.O_NDELAY)
    except AttributeError:
        fcntl.fcntl(afd, fcntl.F_SETFL, fl | os.FNDELAY)


def sosGetCommandOutput(command, timeout = 300):
    """ Execute a command and gather stdin, stdout, and return status.
    """
    soslog = logging.getLogger('sos')

    # Log if binary is not runnable or does not exist
    for path in os.environ["PATH"].split(":"):
        cmdfile = command.strip("(").split()[0]
        # handle both absolute or relative paths
        if ( ( not os.path.isabs(cmdfile) and os.access(os.path.join(path,cmdfile), os.X_OK) ) or \
           ( os.path.isabs(cmdfile) and os.access(cmdfile, os.X_OK) ) ):
            break
    else:
        soslog.log(logging.VERBOSE, "binary '%s' does not exist or is not runnable" % cmdfile)
        return (127, "", 0)

    # these are file descriptors, not file objects
    r, w = os.pipe()

    pid = os.fork()

    if pid:
        # we are the parent
        os.close(w) # use os.close() to close a file descriptor
        r_fd = os.fdopen(r) # turn r into a file object
        stime=time()
        txt = ""
        sts = -1
        soslog.log(logging.VERBOSE2, 'forked command "%s" with pid %d, timeout is %d' % (command, pid, timeout) )
        while True:
            # read output from pipe
            ready = select.select([r], [], [], 1)
            if r in ready[0]:
               txt = txt + r_fd.read()
            # is child still running ?
            try:    os.waitpid(pid, os.WNOHANG)
            except:
               # not running, make sure the child process gets cleaned up
               try:    sts = os.waitpid(pid, 0)[1]
               except: pass
               break
            # has timeout passed ?
            if time() - stime > timeout:
               soslog.log(logging.VERBOSE, 'killing hung child with pid %s after %d seconds (command was "%s")' % (pid,timeout,command) )
               try:    os.kill(pid, signal.SIGKILL)
               except: pass
               break
        if txt[-1:] == '\n': txt = txt[:-1]
        return (sts, txt, time()-stime)
    else:
        # we are the child
        os.dup2(r, 0)
        os.dup2(w, 1)
        os.dup2(w, 2)

        import resource
        maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1] 
        if not hasattr(resource, "RLIM_INFINITY"):
               resource.RLIM_INFINITY = -1L
        if (maxfd == resource.RLIM_INFINITY): 
           maxfd = MAXFD 
        for fd in range(3, maxfd): 
           try:            os.close(fd) 
           except OSError: pass
        os.execl("/bin/sh", "/bin/sh", "-c", command)
        os._exit(127)

# FIXME: this needs to be made clean and moved to the plugin tools, so
# that it prints nice color output like sysreport if the progress bar
# is not enabled.
def sosStatus(stat):
    """ Complete a status line that has been output to the console,
    providing pass/fail indication.
    """
    if not stat:
        print "    [   OK   ]"
    else:
        print "    [ FAILED ]"
    sys.stdout.flush()
    return


def allEqual(elements):
    ''' return True if all the elements are equal, otherwise False. '''
    first_element = elements[0]
    for other_element in elements[1:]:
        if other_element != first_element:
            return False
    return True

def commonPrefix(l1, l2, common = []):
    ''' return a list of common elements at the start of all sequences,
        then a list of lists that are the unique tails of each sequence. '''
    if len(l1) < 1 or len(l2) < 1 or  l1[0] != l2[0]: return common, [l1, l2]
    return commonPrefix(l1[1:], l2[1:], common+[l1[0]])

def sosRelPath(path1, path2, sep=os.path.sep, pardir=os.path.pardir):
    ''' return a relative path from path1 equivalent to path path2.
        In particular: the empty string, if path1 == path2;
                       path2, if path1 and path2 have no common prefix.
    '''
    try:
        common, (u1, u2) = commonPrefix(path1.split(sep), path2.split(sep))
    except AttributeError:
        return path2

    if not common:
        return path2      # leave path absolute if nothing at all in common
    return sep.join( [pardir]*len(u1) + u2 )

def sosReadFile(fname):
    ''' reads a file and returns its contents'''
    fp = open(fname,"r")
    content = fp.read()
    fp.close()
    return content
