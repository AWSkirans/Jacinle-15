# -*- coding: utf-8 -*-
# File   : registry.py
# Author : Jiayuan Mao
# Email  : maojiayuan@gmail.com
# Date   : 12/29/16
#
# This file is part of Jacinle.

import collections
import threading

from .context import EmptyContext

__all__ = ['Registry', 'RegistryGroup', 'CallbackRegistry']


class Registry(object):
    __FALLBACK_KEY__ = '__fallback__'

    def __init__(self):
        self._registry = dict()

    @property
    def fallback(self):
        return self._registry.get(self.__FALLBACK_KEY__, None)

    def set_fallback(self, value):
        self._registry[self.__FALLBACK_KEY__] = value
        return self

    def register(self, entry, value):
        self._registry[entry] = value
        return self

    def has(self, entry):
        return entry in self._registry

    def lookup(self, entry, fallback=True, default=None):
        if fallback:
            fallback_value = self._registry.get(self.__FALLBACK_KEY__, default)
        else:
            fallback_value = default
        return self._registry.get(entry, fallback_value)


class DefaultRegistry(Registry):
    __base_class__ = dict

    def __init__(self):
        super().__init__()
        base_class = type(self).__base_class__
        self._registry = collections.defaultdict(base_class)

    def lookup(self, entry, fallback=False, default=None):
        assert fallback is False and default is None
        return self._registry[entry]

    def __getitem__(self, item):
        return self.lookup(item)


class RegistryGroup(object):
    __base_class__ = Registry

    def __init__(self):
        base_class = type(self).__base_class__
        self._registries = collections.defaultdict(base_class)

    def __getitem__(self, item):
        return self._registries[item]

    def register(self, registry_name, entry, value):
        return self._registries[registry_name].register(entry, value)

    def lookup(self, registry_name, entry, fallback=True, default=None):
        return self._registries[registry_name].lookup(entry, fallback=fallback, default=default)


class CallbackRegistry(Registry):
    """
    A callable manager utils.

    If there exists a super callback, it will block all callbacks.
    A super callback will receive the called name as its first argument.

    Then the dispatcher will try to call the callback by name.
    If such name does not exists, a fallback callback will be called.

    The fallback callback will also receive the called name as its first argument.

    Usage:

    >>> registry = CallbackRegistry()
    >>> callback_func = print
    >>> registry.register('name', callback_func)  # register a callback.
    >>> registry.dispatch('name', 'arg1', 'arg2', kwarg1='kwarg1')  # dispatch.
    """
    def __init__(self):
        super().__init__()
        self._super_callback = None

    @property
    def super_callback(self):
        return self._super_callback

    def set_super_callback(self, callback):
        self._super_callback = callback
        return self

    @property
    def fallback_callback(self):
        return self.fallback

    def set_fallback_callback(self, callback):
        return self.set_fallback(callback)

    def dispatch(self, name, *args, **kwargs):
        if self._super_callback is not None:
            return self._super_callback(self, name, *args, **kwargs)
        return self.dispatch_direct(name, *args)

    def dispatch_direct(self, name, *args, **kwargs):
        """Dispatch by name, ignoring the super callback."""
        callback = self.lookup(name, fallback=False)
        if callback is None:
            if self.fallback_callback is None:
                raise ValueError('Unknown callback entry: "{}".',format(name))
            return self.fallback_callback(self, name, *args, **kwargs)
        return callback(*args, **kwargs)


class LockRegistry(DefaultRegistry):
    __base_class__ = threading.Lock()

    def synchronized(self, entry, activate=True):
        if activate:
            return self.lookup(entry)
        return EmptyContext()