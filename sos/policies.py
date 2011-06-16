import platform

import policyredhat
import policydummy

SYSTEM = platform.system()

def load():
    if SYSTEM == "Java":
        return policydummy.SosPolicy()
    elif SYSTEM == "Linux":
        return policyredhat.SosPolicy()
    elif SYSTEM == "Windows":
        return None  # Need to build a windows policy
    else:
        raise Exception(
            "System type could not be determined. No policy can be loaded.")
