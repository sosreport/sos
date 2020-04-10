# Copyright Red Hat 2020, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import logging
import subprocess


class Cluster():

    option_list = []
    packages = ('',)
    sos_plugins = []
    sos_plugin_options = {}
    sos_preset = ''
    cluster_name = None

    def __init__(self, commons):
        '''This is the class that cluster profile should subclass in order to
        add support for different clustering technologies and environments to
        sos-collector.

        A profile should at minimum define a package that indicates the node is
        configured for the type of cluster the profile is intended to serve and
        then additionall be able to return a list of enumerated nodes via the
        get_nodes() method
        '''

        self.master = None
        self.tmpdir = commons['tmpdir']
        self.opts = commons['opts']
        self.cluster_type = [self.__class__.__name__]
        for cls in self.__class__.__bases__:
            if cls.__name__ != 'Cluster':
                self.cluster_type.append(cls.__name__)
        self.node_list = None
        self.soslog = logging.getLogger('sos')
        self.ui_log = logging.getLogger('sos_ui')
        self.options = []
        self._get_options()

    @classmethod
    def name(cls):
        '''Returns the cluster's name as a string.
        '''
        if cls.cluster_name:
            return cls.cluster_name
        return cls.__name__.lower()

    def _get_options(self):
        '''Loads the options defined by a cluster and sets the default value'''
        for opt in self.option_list:
            option = ClusterOption(name=opt[0], opt_type=opt[1].__class__,
                                   value=opt[1], cluster=self.cluster_type,
                                   description=opt[2])
            self.options.append(option)

    def _fmt_msg(self, msg):
        return '[%s] %s' % (self.cluster_type, msg)

    def log_info(self, msg):
        '''Used to print info messages'''
        self.soslog.info(self._fmt_msg(msg))

    def log_error(self, msg):
        '''Used to print error messages'''
        self.soslog.error(self._fmt_msg(msg))

    def log_debug(self, msg):
        '''Used to print debug messages'''
        self.soslog.debug(self._fmt_msg(msg))

    def log_warn(self, msg):
        '''Used to print warning messages'''
        self.soslog.warn(self._fmt_msg(msg))

    def get_option(self, option):
        '''This is used to by clusters to check if a cluster option was
        supplied to sos-collector.
        '''
        # check CLI before defaults
        for opt in self.opts.cluster_options:
            if opt.name == option and opt.cluster in self.cluster_type:
                return opt.value
        # provide defaults otherwise
        for opt in self.options:
            if opt.name == option:
                return opt.value
        return False

    def exec_master_cmd(self, cmd, need_root=False):
        '''Used to retrieve output from a (master) node in a cluster'''
        res = self.master.run_command(cmd, get_pty=True, need_root=need_root)
        if res['stdout']:
            res['stdout'] = res['stdout'].replace('Password:', '')
        return res

    def setup(self):
        '''This MAY be used by a cluster to do prep work in case there are
        extra commands to be run even if a node list is given by the user, and
        thus get_nodes() would not be called
        '''
        pass

    def check_enabled(self):
        '''This may be overridden by clusters

        This is called by sos-collector on each cluster type that exists, and
        is meant to return True when the cluster type matches a criteria
        that indicates that is the cluster type is in use.

        Only the first cluster type to determine a match is run
        '''
        for pkg in self.packages:
            if self.master.is_installed(pkg):
                return True
        return False

    def get_nodes(self):
        '''This MUST be overridden by a cluster.
        A cluster should use this method to return a list or string that
        contains all the nodes that a report should be collected from
        '''
        pass

    def _get_nodes(self):
        try:
            return self.format_node_list()
        except Exception as e:
            self.log_debug('Failed to get node list: %s' % e)
            return []

    def get_node_label(self, node):
        '''Used by SosNode() to retrieve the appropriate label from the cluster
        as set by set_node_label() in the cluster profile.
        '''
        return self.set_node_label(node)

    def set_node_label(self, node):
        '''This may be overridden by clusters.

        If there is a distinction between masters and nodes, or types of nodes,
        then this can be used to label the sosreport archive differently.
        '''
        return ''

    def modify_sos_cmd(self):
        '''This is used to modify the sosreport command run on the nodes.
        By default, sosreport is run without any options, using this will
        allow the profile to specify what plugins to run or not and what
        options to use.

        This will NOT override user supplied options.
        '''
        if self.sos_preset:
            if not self.opts.preset:
                self.opts.preset = self.sos_preset
            else:
                self.log_debug('Cluster specified preset %s but user has also '
                               'defined a preset. Using user specification.'
                               % self.sos_preset)
        if self.sos_plugins:
            for plug in self.sos_plugins:
                if plug not in self.opts.enable_plugins:
                    self.opts.enable_plugins.append(plug)
        if self.sos_plugin_options:
            for opt in self.sos_plugin_options:
                if not any(opt in o for o in self.opts.plugin_options):
                    option = '%s=%s' % (opt, self.sos_plugin_options[opt])
                    self.opts.plugin_options.append(option)

    def format_node_list(self):
        '''Format the returned list of nodes from a cluster into a known
        format. This being a list that contains no duplicates
        '''
        try:
            nodes = self.get_nodes()
        except Exception as e:
            self.log_error('\n%s failed to enumerate nodes: %s'
                           % (self.cluster_type, e))
            raise
        if isinstance(nodes, list):
            node_list = [n.strip() for n in nodes if n]
        elif isinstance(nodes, str):
            node_list = [n.split(',').strip() for n in nodes]
        node_list = list(set(node_list))
        for node in node_list:
            if node.startswith(('-', '_', '(', ')', '[', ']', '/', '\\')):
                node_list.remove(node)
        return node_list

    def _run_extra_cmd(self):
        '''Ensures that any files returned by a cluster's run_extra_cmd()
        method are properly typed as a list for iterative collection. If any
        of the files are an additional sosreport (e.g. the ovirt db dump) then
        the md5 sum file is automatically added to the list
        '''
        files = []
        try:
            res = self.run_extra_cmd()
            if res:
                if not isinstance(res, list):
                    res = [res]
                for extra_file in res:
                    extra_file = extra_file.strip()
                    files.append(extra_file)
                    if 'sosreport' in extra_file:
                        files.append(extra_file + '.md5')
        except AttributeError:
            pass
        return files


class ClusterOption():
    '''Used to store/manipulate options for cluster profiles.'''

    def __init__(self, name, value, opt_type, cluster, description=None):
        self.name = name
        self.value = value
        self.opt_type = opt_type
        self.cluster = cluster
        self.description = description
