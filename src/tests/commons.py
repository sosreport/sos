# commons.py
import sys, os

commons = {}
commons['bin'] = '/usr/sbin/sosreport'
commons['testName'] = 'tester'
commons['testID'] = 1
commons['batch'] = True
commons['i18n'] = 'en_US.UTF-8'
commons['pluginpath'] = None
commons['plugins'] = []
if os.path.isfile('/etc/fedora-release'):
    commons['distro'] = 'Fedora'
else:
    commons['distro'] = 'RHEL'

paths = sys.path
for path in paths:
    if path.strip()[-len("site-packages"):] == "site-packages" \
    and os.path.isdir(path + "/sos/plugins"):
        commons['pluginpath'] = path + "/sos/plugins"

for plugin in os.listdir(commons['pluginpath']):
    plugbase =  plugin[:-3]
    if not plugin[-3:] == '.py' or plugbase == "__init__":
        continue
    commons['plugins'].append(plugbase) 

