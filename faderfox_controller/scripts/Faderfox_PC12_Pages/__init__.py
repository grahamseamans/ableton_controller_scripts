from __future__ import absolute_import, print_function, unicode_literals


def create_instance(c_instance):
    from .pc12_surface import PC12Surface
    return PC12Surface(c_instance)
