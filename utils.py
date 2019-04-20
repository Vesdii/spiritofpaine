from collections import OrderedDict

def unique(li):
    """Return a new list, with duplicates removed."""
    return list(OrderedDict.fromkeys(li))
