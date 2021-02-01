# this script generates for each plugin:
# - list of paths it collects (add_copy_spec)
# - list of paths it forbits to collect (add_forbidden_path)
# - list of commands it calls (add_cmd_output)
#
# Output of the script: a JSON object with plugins in keys
#
# TODO:
# - improve parsing that will be never ideal :)
# - add other methods:
#   - add_blockdev_cmd
#   - add_string_as_file
#   - ??
# - profile info?
# - distro info?
# - output in csv (multiline per plugin)

import os
import re
import json

PLUGDIR = 'sos/report/plugins'

plugs_data = {}     # the map of all plugins data to collect
plugcontent = ''    # content of plugin file just being processed

# method to parse items of a_s_c/a_c_o/.. methods to fetch list of
# copyspecs/commands without all the mess around. The method removes:
# 1) trailing/leading whitespace
# 2) trailing+leading quote marks
# 3) comments (anything after '#')
# 3) anything after ',' supposed to be an optional arguments of a_s_c/a_c_o
#    methods like sizelimit or suggest_filename
def my_strip(item):
    return item.strip().strip("\"'").split("#")[0].split(",")[0]

# method to find in `plugcontent` all items of given method (a_c_s/a_c_o/..) and
# to extend the `dest` list by the parsed items
def add_all_items(method, dest):
    for match in re.findall("%s\((.*?)\)" % method, plugcontent, flags=re.MULTILINE|re.DOTALL):
        # list of specs separated by comma ..
        if match.startswith('['):
            dest.extend([my_strip(item) for item in match[1:-1].split(',')])
        # .. or a singleton spec
        else:
            dest.append(my_strip(match))

# main body: traverse report's plugins directory and for each plugin, grep for 
# add_copy_spec / add_forbidden_path / add_cmd_output there
for plugfile in sorted(os.listdir(PLUGDIR)):
    # ignore non-py files and __init__.py
    if not plugfile.endswith('.py') or plugfile == '__init__.py':
        continue
    plugname = plugfile[:-3]
    plugs_data[plugname] = {
            'sourcecode': 'https://github.com/sosreport/sos/blob/master/sos/report/plugins/%s.py' % plugname,
            'copyspecs': [],
            'forbidden': [],
            'commands': [],
            'service_status': [],
            'journals': [],
            'env': [],
    }
    plugcontent = open(os.path.join(PLUGDIR, plugfile)).read().replace('\n','')
    add_all_items("add_copy_spec", plugs_data[plugname]['copyspecs'])
    add_all_items("add_forbidden_path", plugs_data[plugname]['forbidden'])
    add_all_items("add_cmd_output", plugs_data[plugname]['commands'])
    add_all_items("collect_cmd_output", plugs_data[plugname]['commands'])
    add_all_items("add_service_status", plugs_data[plugname]['service_status'])
    add_all_items("add_journal", plugs_data[plugname]['journals'])
    add_all_items("add_env_var", plugs_data[plugname]['env'])

print(json.dumps(plugs_data))
