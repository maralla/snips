# -*- coding: utf-8 -*-

import os


def tab_indent(context, line, is_block=None):
    if not line:
        return line, 0

    if is_block and not is_block():
        return line, 0

    size = len(line)

    tabs = 0
    while tabs < size and line[tabs] == '\t':
        tabs += 1

    indent = context['indent']

    if tabs:
        indent += context['tabstop'] * tabs

    c = ' '
    if not context['expandtab']:
        indent = int(indent / context['tabstop'])
        c = '\t'

    return indent * c + line[tabs:], indent - tabs


class SnippetUtil(object):
    def __init__(self, context):
        self.rv = ''
        self.c = ''
        self.v = None
        self.fn = context['fname']
        self.ft = context['ftype']
        self.indent = context['indent']
        self.relative_indent = 0
        self.basename, _ = os.path.splitext(self.fn)

        self._orig_indent = self.indent
        self._context = context

    def mkline(self, line='', indent=None):
        if not line:
            return line

        indent = indent or self.relative_indent
        if self._context['expandtab']:
            prefix = ' ' * indent
        else:
            amount = int(indent / self._context['tabstop'])
            prefix = '\t' * amount
        return prefix + line

    def shift(self, amount=1):
        self.relative_indent += self._context['tabstop'] * amount

    def unshift(self, amount=1):
        self.relative_indent -= self._context['tabstop'] * amount
        if self.relative_indent < 0:
            self.relative_indent = 0

    def reset_indent(self):
        self.relative_indent = 0

    def opt(self, v, default=None):
        import vim
        ret = vim.vars.get(v)
        if ret is None:
            return default
        if isinstance(ret, bytes):
            return ret.decode()
        return ret

    def __rshift__(self, amount):
        self.shift(amount)

    def __lshift__(self, amount):
        self.unshift(amount)

    def __iadd__(self, line):
        self.rv += '\n' + self.mkline(line)
        return self
