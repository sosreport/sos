# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class RabbitMQ(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """RabbitMQ messaging service
    """
    plugin_name = 'rabbitmq'
    profiles = ('services',)
    var_puppet_gen = "/var/lib/config-data/puppet-generated/rabbitmq"
    files = (
        '/etc/rabbitmq/rabbitmq.conf',
        var_puppet_gen + '/etc/rabbitmq/rabbitmq.config'
    )
    packages = ('rabbitmq-server',)

    def setup(self):
        in_container = False
        container_names = []
        _containers = self.get_containers()
        for _con in _containers:
            if _con[1].startswith('rabbitmq'):
                in_container = True
                container_names.append(_con[1])

        if in_container:
            for container in container_names:
                self.get_container_logs(container)
                self.add_cmd_output(
                    self.fmt_container_cmd(container, 'rabbitmqctl report')
                )
        else:
            self.add_cmd_output("rabbitmqctl report")

        self.add_copy_spec([
            "/etc/rabbitmq/*",
            self.var_puppet_gen + "/etc/rabbitmq/*",
            self.var_puppet_gen + "/etc/security/limits.d/",
            self.var_puppet_gen + "/etc/systemd/"
        ])
        self.add_copy_spec([
            "/var/log/rabbitmq/*",
        ])

    def postproc(self):
        self.do_file_sub("/etc/rabbitmq/rabbitmq.conf",
                         r"(\s*default_pass\s*,\s*)\S+", r"\1<<***>>},")

# vim: set et ts=4 sw=4 :
