import platform

import redhat

SYSTEM = platform.system()

def load():
    if SYSTEM == "Java":
        return redhat.Jython()
    elif SYSTEM == "Linux":
        return redhat.CPython()
    elif SYSTEM == "Windows":
        return None  # Need to build a windows policy
    else:
        raise Exception(
            "System type could not be determined. No policy can be loaded.")
