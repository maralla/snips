# -*- coding: utf-8 -*-

import os


class SnippetUtil(object):
    def __init__(self, fn, ft):
        self.rv = ''
        self.c = ''
        self.v = None
        self.fn = fn
        self.basename, _ = os.path.splitext(fn)
        self.ft = ft

    def opt(self, v, default=None):
        import vim
        ret = vim.vars.get(v)
        if ret is None:
            return default
        if isinstance(ret, bytes):
            return ret.decode()
        return ret
