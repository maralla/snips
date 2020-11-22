# -*- coding: utf-8 -*-

import vim
import glob
import os
import logging
import string

try:
    import builtins
except ImportError:
    import future_builtins as builtins

from .parser import parse
from .ast import Extends, Priority, Global, Snippet

_ALL = 'all'

# Global snips cache.
# ft -> SnipInfo
cache = {}

ident_chars = string.ascii_letters + string.digits

logger = logging.getLogger("completor")

# Global state recorder.
g = type('_g', (object,), {})
g.current_snippet = None
g.snippets_dirs = []


def set_snippets_dirs(dirs):
    """Sets the snippets directory.
    """
    g.snippets_dirs = dirs


def _try_init_snippets(ft):
    dirs = g.snippets_dirs
    if not dirs:
        return

    _try_init_all(dirs)

    snips = cache.get(ft)
    if snips is None:
        snips = SnipInfo()
        snips.load(ft, dirs)
        cache[ft] = snips


def get(ft, token):
    """Gets all snips contain the token.
    """
    _try_init_snippets(ft)

    snips = cache.get(ft)
    if snips is None:
        return []

    ret = []
    for k, (_, s) in snips.snippets.items():
        if token in k:
            ret.append(s)
    for k, (_, s) in cache['all'].snippets.items():
        if token in k:
            ret.append(s)
    ret.sort(key=lambda x: x.trigger)
    return ret


class Context(dict):
    def __init__(self, data):
        dict.__init__(self, data)

        for k in list(self.keys()):
            v = self[k]
            if isinstance(v, bytes):
                v = v.decode()
            self[k.decode()] = v

    def on_trigger_ready(self, length, is_block):
        """The hook is called when snippet trigger is ready.

        :length: The trigger length.
        :is_block: Whether the trigger has block option.
        :returns: None
        """
        f = self.get('on_trigger_ready')
        if f:
            f(length, is_block)


def _ident(text, index):
    ident = ''

    index -= 1
    while index > 0:
        c = text[index]
        if c not in ident_chars:
            break
        ident = c + ident
        index -= 1

    return ident, index


def _get_snip(snips, trigger, ident_trigger, index, text, context):
    _, s = snips.get(trigger)
    if s and not s.is_block():
        return

    if s is None:
        if not ident_trigger:
            return

        _, s = snips.get(ident_trigger)
        if not s or s.is_block():
            return

        context['_prefix'] = text[:index+1]
        context['_suffix'] = text[context['column']:]

    return s


def expand(context):
    context = Context(context)

    text = context['text']

    if not text:
        return {}

    ftype = context['ftype']
    _try_init_snippets(ftype)

    trigger = text.lstrip()
    column = context['column']
    ident_trigger, index = _ident(text, column)

    s = None

    try:
        snips = cache.get(ftype)
        if snips:
            s = _get_snip(snips, trigger, ident_trigger, index, text, context)

        if s is None:
            snips = cache.get(_ALL, {})
            s = _get_snip(snips, trigger, ident_trigger, index, text, context)

        if s is None:
            return {}

        context.on_trigger_ready(len(s.trigger), s.is_block())

        snippet = s.clone()
        g.current_snippet = snippet
        g.current_snips_info = snips
        content, end = snippet.render(snips.globals, context)
        pos = snippet.jump_position()
        return {
            'content': content,
            'end_col': end,
            'pos': pos or {},
        }
    except Exception as e:
        logger.exception(e)
        raise


def rerender(content):
    snippet = g.current_snippet
    if snippet is None:
        return {}

    content, end = snippet.rerender(content)
    pos = snippet.jump_position()
    return {
        'content': content,
        'pos': pos or {},
        'end_col': end,
    }


def jump(ft, direction):
    snippet = g.current_snippet
    if snippet is None:
        return {}
    pos = snippet.jump(direction)
    return {
        'pos': pos or {},
    }


def reset_jump(ft):
    snip = g.current_snippet
    if snip is None:
        return
    snip.reset()
    g.current_snippet = None
    g.current_snips_info = None


def _try_init_all(dirs):
    if _ALL not in cache:
        snips = SnipInfo()
        snips.load(_ALL, dirs)
        cache[_ALL] = snips


def _dumb_print(*args, **kwargs):
    pass


class SnipInfo(object):
    def __init__(self):
        import vim
        import os
        import re
        bs = dict(builtins.__dict__)
        bs['print'] = _dumb_print
        self.globals = {'__builtins__': bs, 'vim': vim, 'os': os, 're': re}
        self.extends = set([])
        self.snippets = {}

    def _eval_global(self, g):
        if g.tp != '!p':
            return
        exec(g.body, self.globals)

    def get(self, key, default=(0, None)):
        return self.snippets.get(key, default)

    def add_items(self, items):
        priority = 0
        for item in items:
            if not isinstance(item, Priority):
                continue
            priority = item.priority
            break

        priority = 0

        for item in items:
            if isinstance(item, Priority):
                priority = item.priority
                continue

            if isinstance(item, Extends):
                self.extends.update(item.types)
                continue

            if isinstance(item, Global):
                self._eval_global(item)
                continue

            if not isinstance(item, Snippet) or 'r' in item.options:
                continue

            s = self.snippets.get(item.trigger, None)
            if s is not None and s[0] > priority:
                continue

            self.snippets[item.trigger] = priority, item

    def load(self, ft, dirs):
        for d in dirs:
            self._load_in_dir(ft, d)

    def _load_in_dir(self, ft, d):
        if not ft:
            ft = 'all'

        files = glob.glob(os.path.join(d, '{}.snippets'.format(ft)))
        files.extend(glob.glob(os.path.join(d, '{}_*.snippets'.format(ft))))
        files.extend(glob.glob(os.path.join(d, ft, '*')))

        try:
            for f in files:
                with open(f) as r:
                    data = r.read()
                self.add_items(parse(data, filename=f))
        except Exception as e:
            logger.exception(e)
            raise
