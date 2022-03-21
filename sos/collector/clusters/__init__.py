# Copyright Red Hat 2020, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import logging

from sos.options import ClusterOption
from sos.utilities import bold
from threading import Lock


class Cluster():
    """This is the class that cluster profiles should subclass in order to
    add support for different clustering technologies and environments to
    sos-collector.

    A profile should at minimum define a package that indicates the node is
    configured for the type of cluster the profile is intended to serve and
    then additionally be able to return a list of enumerated nodes via the
    ``get_nodes()`` method


    :param commons: The commons dict containing system information. The same as
                    what is handed to ``Plugin()``
    :type commons: ``dict``


    :cvar option_list:  Options supported by the profile, and set by the
                        --cluster-option cmdline arg
    :vartype option_list: ``list`` of ``tuples``

    :cvar packages: What package(s) should this profile enable on
    :vartype packages: ``tuple``

    :cvar sos_plugins: Which plugins to forcibly enable for node reports
    :vartype sos_plugins: ``list``

    :cvar sos_plugin_options: Plugin options to forcibly set for nodes
    :vartype sos_plugin_options: ``dict``

    :cvar sos_preset: A SoSReport preset to forcibly enable on nodes
    :vartype sos_preset: ``str``

    :cvar cluster_name: The name of the cluster type
    :vartype cluster_name: ``str``
    """

    option_list = []
    packages = ('',)
    sos_plugins = []
    sos_plugin_options = {}
    sos_preset = ''
    cluster_name = None
    # set this to True if the local host running collect should *not* be
    # forcibly added to the node list. This can be helpful in situations where
    # the host's fqdn and the name the cluster uses are different
    strict_node_list = False

    def __init__(self, commons):
        self.primary = None
        self.cluster_ssh_key = None
        self.tmpdir = commons['tmpdir']
        self.opts = commons['cmdlineopts']
        self.cluster_type = [self.__class__.__name__]
        for cls in self.__class__.__bases__:
            if cls.__name__ != 'Cluster':
                self.cluster_type.append(cls.__name__)
        self.node_list = None
        self.lock = Lock()
        self.soslog = logging.getLogger('sos')
        self.ui_log = logging.getLogger('sos_ui')
        self.options = []
        self._get_options()

    @classmethod
    def name(cls):
        """Returns the cluster's name as a string.
        """
        if cls.cluster_name:
            return cls.cluster_name
        return cls.__name__.lower()

    @classmethod
    def display_help(cls, section):
        if cls is Cluster:
            cls.display_self_help(section)
            return
        section.set_title("%s Cluster Profile Detailed Help"
                          % cls.cluster_name)
        if cls.__doc__ and cls.__doc__ is not Cluster.__doc__:
            section.add_text(cls.__doc__)
        # [1] here is the actual cluster profile
        elif cls.__mro__[1].__doc__ and cls.__mro__[1] is not Cluster:
            section.add_text(cls.__mro__[1].__doc__)
        else:
            section.add_text(
                "\n\tDetailed help not available for this profile\n"
            )

        if cls.packages:
            section.add_text(
                "Enabled by the following packages: %s"
                % ', '.join(p for p in cls.packages),
                newline=False
            )

        if cls.sos_preset:
            section.add_text(
                "Uses the following sos preset: %s" % cls.sos_preset,
                newline=False
            )

        if cls.sos_plugins:
            section.add_text(
                "Enables the following plugins: %s"
                % ', '.join(plug for plug in cls.sos_plugins),
                newline=False
            )

        if cls.sos_plugin_options:
            _opts = cls.sos_plugin_options
            opts = ', '.join("%s=%s" % (opt, _opts[opt]) for opt in _opts)
            section.add_text(
                "Sets the following plugin options: %s" % opts,
                newline=False
            )

        if cls.option_list:
            optsec = section.add_section("Available cluster options")
            optsec.add_text(
                "These options may be toggled or changed using '%s'"
                % bold("-c %s.$option=$value" % cls.__name__)
            )
            optsec.add_text(bold(
                "\n{:<4}{:<20}{:<30}{:<20}\n".format(
                    ' ', "Option Name", "Default", "Description")
                ), newline=False
            )
            for opt in cls.option_list:
                val = opt[1]
                if isinstance(val, bool):
                    if val:
                        val = 'True/On'
                    else:
                        val = 'False/Off'
                _ln = "{:<4}{:<20}{:<30}{:<20}".format(' ', opt[0], val,
                                                       opt[2])
                optsec.add_text(_ln, newline=False)

    @classmethod
    def display_self_help(cls, section):
        section.set_title('SoS Collect Cluster Profiles Detailed Help')
        section.add_text(
            '\nCluster profiles are used to represent different clustering '
            'technologies or platforms. Profiles define how cluster nodes are '
            'discovered, and optionally filtered, for default executions of '
            'collector.'
        )
        section.add_text(
            'Cluster profiles are enabled similarly to SoS report plugins; '
            'usually by package, command, or configuration file presence. '
            'Clusters may also define default transports for SoS collect.'
        )

        from sos.collector import SoSCollector
        import inspect
        clusters = SoSCollector._load_modules(inspect.getmodule(cls),
                                              'clusters')

        section.add_text(
            'The following cluster profiles are locally available:\n'
        )
        section.add_text(
            "{:>8}{:<40}{:<30}".format(' ', 'Name', 'Description'),
            newline=False
        )
        for cluster in clusters:
            _sec = bold("collect.clusters.%s" % cluster[0])
            section.add_text(
                "{:>8}{:<40}{:<30}".format(' ', _sec, cluster[1].cluster_name),
                newline=False
            )

    def _get_options(self):
        """Loads the options defined by a cluster and sets the default value"""
        for opt in self.option_list:
            option = ClusterOption(name=opt[0], opt_type=opt[1].__class__,
                                   value=opt[1], cluster=self.cluster_type,
                                   description=opt[2])
            self.options.append(option)

    def _fmt_msg(self, msg):
        return '[%s] %s' % (self.cluster_type[0], msg)

    def log_info(self, msg):
        """Used to print info messages"""
        self.soslog.info(self._fmt_msg(msg))

    def log_error(self, msg):
        """Used to print error messages"""
        self.soslog.error(msg)

    def log_debug(self, msg):
        """Used to print debug messages"""
        self.soslog.debug(self._fmt_msg(msg))

    def log_warn(self, msg):
        """Used to print warning messages"""
        self.soslog.warn(self._fmt_msg(msg))

    def get_option(self, option):
        """
        This is used to by clusters to check if a cluster option was
        supplied to sos collect

        :param option: The name of the option to fetch
        :type option: ``str``

        :returns: The value of the requested option if it exists, or ``False``
        """
        # check CLI before defaults
        for opt in self.opts.cluster_options:
            if opt.name == option and opt.cluster in self.cluster_type:
                return opt.value
        # provide defaults otherwise
        for opt in self.options:
            if opt.name == option:
                return opt.value
        return False

    def add_default_ssh_key(self, key):
        """Some clusters generate and/or deploy well-known and consistent
        SSH keys across environments. If this is the case, the cluster profile
        may call this command so that subsequent node connections will use that
        key rather than prompting the user for one or a password.

        Note this will only function if collector is being run locally on the
        primary node.
        """
        self.cluster_ssh_key = key

    def set_node_options(self, node):
        """If there is a need to set specific options on ONLY the non-primary
        nodes in a collection, override this method in the cluster profile
        and do that here.

        :param node:        The non-primary node
        :type node:         ``SoSNode``
        """
        pass

    def set_transport_type(self):
        """The default connection type used by sos collect is to leverage the
        local system's SSH installation using ControlPersist, however certain
        cluster types may want to use something else.

        Override this in a specific cluster profile to set the ``transport``
        option according to what type of transport should be used.
        """
        return 'control_persist'

    def set_primary_options(self, node):
        """If there is a need to set specific options in the sos command being
        run on the cluster's primary nodes, override this method in the cluster
        profile and do that here.

        :param node:       The primary node
        :type node:        ``SoSNode``
        """
        pass

    def check_node_is_primary(self, node):
        """In the event there are multiple primaries, or if the collect command
        is being run from a system that is technically capable of enumerating
        nodes but the cluster profiles needs to specify primary-specific
        options for other nodes, override this method in the cluster profile

        :param node:        The node for the cluster to check
        :type node:         ``SoSNode``
        """
        return node.address == self.primary.address

    def exec_primary_cmd(self, cmd, need_root=False):
        """Used to retrieve command output from a (primary) node in a cluster

        :param cmd: The command to run
        :type cmd: ``str``

        :param need_root: Does the command require root privileges
        :type need_root: ``bool``

        :returns: The output and status of `cmd`
        :rtype: ``dict``
        """
        pty = self.primary.local is False
        res = self.primary.run_command(cmd, get_pty=pty, need_root=need_root)
        if res['output']:
            res['output'] = res['output'].replace('Password:', '')
        return res

    def setup(self):
        """
        This MAY be used by a cluster to do prep work in case there are
        extra commands to be run even if a node list is given by the user, and
        thus get_nodes() would not be called
        """
        pass

    def check_enabled(self):
        """
        This may be overridden by clusters

        This is called by sos collect on each cluster type that exists, and
        is meant to return True when the cluster type matches a criteria
        that indicates that is the cluster type is in use.

        Only the first cluster type to determine a match is run

        :returns: ``True`` if the cluster profile should be used, or ``False``
        :rtype: ``bool``
        """
        for pkg in self.packages:
            if self.primary.is_installed(pkg):
                return True
        return False

    def cleanup(self):
        """
        This may be overridden by clusters

        Perform any necessary cleanup steps required by the cluster profile.
        This helps ensure that sos does make lasting changes to the environment
        in which we are running
        """
        pass

    def get_nodes(self):
        """
        This MUST be overridden by a cluster profile subclassing this class

        A cluster should use this method to return a list or string that
        contains all the nodes that a report should be collected from

        :returns: A list of node FQDNs or IP addresses
        :rtype: ``list`` or ``None``
        """
        pass

    def _get_nodes(self):
        try:
            return self.format_node_list()
        except Exception as e:
            self.log_debug('Failed to get node list: %s' % e)
            return []

    def get_node_label(self, node):
        """
        Used by ``SosNode()`` to retrieve the appropriate label from the
        cluster as set by ``set_node_label()`` in the cluster profile.

        :param node: The name of the node to get a label for
        :type node: ``str``

        :returns: The label to use for the node's report
        :rtype: ``str``
        """
        label = self.set_node_label(node)
        node.manifest.add_field('label', label)
        return label

    def set_node_label(self, node):
        """This may be overridden by clusters profiles subclassing this class

        If there is a distinction between primaries and nodes, or types of
        nodes, then this can be used to label the sosreport archive differently
        """
        return ''

    def format_node_list(self):
        """
        Format the returned list of nodes from a cluster into a known
        format. This being a list that contains no duplicates

        :returns: A list of nodes, without extraneous entries from cmd output
        :rtype: ``list``
        """
        try:
            nodes = self.get_nodes()
        except Exception as e:
            self.log_error('Cluster failed to enumerate nodes: %s' % e)
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
        """
        Ensures that any files returned by a cluster's run_extra_cmd()
        method are properly typed as a list for iterative collection. If any
        of the files are an additional sosreport (e.g. the ovirt db dump) then
        the md5 sum file is automatically added to the list
        """
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
