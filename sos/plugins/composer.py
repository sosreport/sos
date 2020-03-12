from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Composer(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Lorax Composer
    """

    plugin_name = 'composer'
    profiles = ('sysmgmt', 'virt', )

    packages = ('composer-cli',)

    def _get_entries(self, cmd):
        entries = []
        ent_file = self.collect_cmd_output(cmd)
        if ent_file['status'] == 0:
            for line in ent_file['output'].splitlines():
                entries.append(line)
        return entries

    def setup(self):
        self.add_copy_spec([
            "/etc/lorax/composer.conf",
            "/var/log/lorax-composer/composer.log",
            "/var/log/lorax-composer/dnf.log",
            "/var/log/lorax-composer/program.log",
            "/var/log/lorax-composer/server.log",
        ])
        blueprints = self._get_entries("composer-cli blueprints list")
        for blueprint in blueprints:
            self.add_cmd_output("composer-cli blueprints show %s" % blueprint)

        sources = self._get_entries("composer-cli sources list")
        for src in sources:
            self.add_cmd_output("composer-cli sources info %s" % src)

# vim: set et ts=4 sw=4 :
