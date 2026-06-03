from __future__ import absolute_import, print_function, unicode_literals

def index_of(seq, item):
    if seq is None:
        return -1

    i = 0
    for n in seq:
        if n == item:
            return i
        i += 1

    return -1

def normalize_relative_value(n):
    return n if n <= 64 else n - 128

def adjust_size(seq, size):
    if len(seq) < size:
        return seq + [None] * (size - len(seq))
    else:
        return seq[:size]

def dumpObject(obj):
    r = []
    for attr in dir(obj):
        r.append(attr)
        #print("obj.%s = %r" % (attr, getattr(obj, attr)))
    return r
