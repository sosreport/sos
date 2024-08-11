# this script generates for each plugin:
# - its name
# - URL to upstream code
# - list of distros
# - list of profiles
# - list of packages that enable the plugin (no other enabling pieces)
# - list of paths it collects (add_copy_spec)
# - list of paths it forbits to collect (add_forbidden_path)
# - list of commands it calls (add_cmd_output)
#
# Output of the script:
# - a JSON object with plugins in keys
# - or CSV format in case "csv" cmdline is provided
#
# TODO:
# - improve parsing that will be never ideal :)
# - add other methods:
#   - add_blockdev_cmd
#   - add_string_as_file
#   - ??

import os
import re
import json
import sys

PLUGDIR = 'sos/report/plugins'

plugs_data = {}     # the map of all plugins data to collect


# method to parse an item of a_s_c/a_c_o/.. methods
# we work on an assumption the item is a string quoted by \" or optionally
# by \'. If we detect at least 2 such chars in the item, take what is between
# those.
def add_valid_item(dest, item):
    for qoutemark in "\"\'":
        split = item.split(qoutemark)
        if len(split) > 2:
            dest.append(split[1])
            return


# method to find all items of given method (a_c_s/a_c_o/..) in plugin content,
# split by comma; add each valid item to the `dest` list
def add_all_items(method, dest, plugfd, wrapopen=r'\(', wrapclose=r'\)'):
    regexp = f"{method}{wrapopen}(.*?){wrapclose}"
    for match in re.findall(regexp, plugfd,
                            flags=re.MULTILINE | re.DOTALL):
        # tuple of distros ended by either (class|from|import)
        if isinstance(match, tuple):
            for item in list(match):
                if item not in ['class', 'from', 'import']:
                    for it in item.split(','):
                        # dirty hack to remove spaces and "Plugin"
                        if "Plugin" not in it:
                            continue
                        it = it.strip(' ()')[0:-6]
                        if len(it):
                            dest.append(it)
        # list of specs separated by comma ..
        elif match.startswith('[') or match.startswith('('):
            for item in match.split(','):
                add_valid_item(dest, item)
        # .. or a singleton spec
        else:
            add_valid_item(dest, match)


# main body: traverse report's plugins directory and for each plugin, grep for
# add_copy_spec / add_forbidden_path / add_cmd_output there
for plugfile in sorted(os.listdir(PLUGDIR)):
    # ignore non-py files and __init__.py
    if not plugfile.endswith('.py') or plugfile == '__init__.py':
        continue
    plugname = plugfile[:-3]
#    if plugname != 'bcache':
#        continue
    plugs_data[plugname] = {
            'sourcecode': 'https://github.com/sosreport/sos/blob/'
                          f'main/sos/report/plugins/{plugname}.py',
            'distros': [],
            'profiles': [],
            'packages': [],
            'copyspecs': [],
            'forbidden': [],
            'commands': [],
            'service_status': [],
            'journals': [],
            'env': [],
    }
    with open(os.path.join(PLUGDIR, plugfile),
              encoding='utf-8').read().replace('\n', '') as pfd:
        add_all_items(
            "from sos.report.plugins import ", plugs_data[plugname]['distros'],
            pfd, wrapopen='', wrapclose='(class|from|import)'
        )
        add_all_items("profiles = ", plugs_data[plugname]['profiles'],
                      pfd, wrapopen='')
        add_all_items("packages = ", plugs_data[plugname]['packages'],
                      pfd, wrapopen='')
        add_all_items("add_copy_spec", plugs_data[plugname]['copyspecs'], pfd)
        add_all_items("add_forbidden_path",
                      plugs_data[plugname]['forbidden'], pfd)
        add_all_items("add_cmd_output", plugs_data[plugname]['commands'], pfd)
        add_all_items("collect_cmd_output",
                      plugs_data[plugname]['commands'], pfd)
        add_all_items("add_service_status",
                      plugs_data[plugname]['service_status'], pfd)
        add_all_items("add_journal", plugs_data[plugname]['journals'], pfd)
        add_all_items("add_env_var", plugs_data[plugname]['env'], pfd)

# print output; if "csv" is cmdline argument, print in CSV format, else JSON
if (len(sys.argv) > 1) and (sys.argv[1] == "csv"):
    print("plugin;url;distros;profiles;packages;copyspecs;forbidden;commands;"
          "service_status;journals;env_vars")
    for plugname, plugin in plugs_data.items():
        # determine max number of lines - usually
        # "max(len(copyspec),len(commands))"
        # ignore 'sourcecode' key as it
        maxline = 1
        plugkeys = list(plugin.keys())
        plugkeys.remove('sourcecode')
        for key in plugkeys:
            maxline = max(maxline, len(plugin[key]))
        for line in range(maxline):
            out = ";" if line > 0 else f"{plugname};{plugin['sourcecode']}"
            for key in plugkeys:
                out += ";"
                if line < len(plugin[key]):
                    out += plugin[key][line]
            print(out)
else:
    print(json.dumps(plugs_data))
