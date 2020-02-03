# -*- coding: utf-8 -*-

import os

_none = object()


class SnippetUtil(object):
    def __init__(self, fn, ft):
        self.rv = _none
        self.c = ''
        self.v = None
        self.fn = fn
        self.basename, _ = os.path.splitext(fn)
        self.ft = ft

    def is_set(self):
        return self.rv is not _none

    def opt(self, v, default=None):
        import vim
        ret = vim.vars.get(v)
        if ret is None:
            return default
        if isinstance(ret, bytes):
            return ret.decode()
        return ret
