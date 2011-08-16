import os
from sos.utilities import ImporterHelper, import_module

def import_policy(name):
    policy_fqname = "sos.policies.%s" % name
    try:
        return import_module(policy_fqname)
    except ImportError:
        return None

def load():
    helper = ImporterHelper(os.path.join('sos', 'policies'))
    policies = []
    for module in helper.get_modules():
        for policy in import_policy(module):
            p = policy()
            if p.check():
                return p
    raise Exception("No policy could be loaded.")
