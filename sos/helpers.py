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
import os, sys
import logging
from subprocess import Popen, PIPE, STDOUT

def importPlugin(pluginname, name):
    """ Import a plugin to extend capabilities of sosreport
    """
    try:
        plugin = __import__(pluginname, globals(), locals(), [name])
    except ImportError:
        return None
    return getattr(plugin, name)

def sosGetCommandOutput(command, timeout = 300):
    """ Execute a command and gather stdin, stdout, and return status.
    """
    for path in os.environ["PATH"].split(":"):
        exists = False
        cmdfile = command.strip("(").split()[0]
        # handle both absolute or relative paths
        if ( ( not os.path.isabs(cmdfile) and os.access(os.path.join(path,cmdfile), os.X_OK) ) or \
           ( os.path.isabs(cmdfile) and os.access(cmdfile, os.X_OK) ) ):
            exists = True
            break
    if not exists:
        return (127, "", 0)

    p = Popen(command, shell=True, stdout=PIPE, stderr=STDOUT, bufsize=-1)
    stdout, stderr = p.communicate()
    # hack to delete trailing '\n' added by p.communicate()
    if stdout[-1:] == '\n': stdout = stdout[:-1]
    return (p.returncode, stdout, 0)

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

