from __future__ import absolute_import, print_function, unicode_literals


def create_instance(c_instance):
    from .mx12_surface import MX12Surface
    return MX12Surface(c_instance)
