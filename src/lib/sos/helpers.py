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
import os, popen2, fcntl, select, itertools, sys, commands
from time import time
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


def sosGetCommandOutput(command):
    """ Execute a command and gather stdin, stdout, and return status.
    Adapted from Python Cookbook - O'Reilly
    """
    stime = time()
    errdata = ''
    status,outdata=commands.getstatusoutput(command)
    return (status, outdata, time()-stime)


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


def commonPrefix(*sequences):
    ''' return a list of common elements at the start of all sequences,
        then a list of lists that are the unique tails of each sequence. '''
    # if there are no sequences at all, we're done
    if not sequences:
        return [], []
    # loop in parallel on the sequences
    common = []
    for elements in itertools.izip(*sequences):
        # unless all elements are equal, bail out of the loop
        if not allEqual(elements):
            break
        # got one more common element, append it and keep looping
        common.append(elements[0])
    # return the common prefix and unique tails
    return common, [ sequence[len(common):] for sequence in sequences ]

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

