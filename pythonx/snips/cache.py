# -*- coding: utf-8 -*-

import glob
import os
import logging
import builtins

from .parser import parse
from .ast import Extends, Priority, Global, Snippet

_ALL = 'all'

# Global snips cache.
# ft -> SnipInfo
cache = {}


logger = logging.getLogger("completor")

# Global state recorder.
g = type('_g', (object,), {})
g.current_snippet = None


def get(ft, token, dirs):
    """Gets all snips contain the token.
    """
    _try_init_all(dirs)
    snips = cache.get(ft, None)
    if snips is None:
        snips = SnipInfo()
        snips.load(ft, dirs)
        cache[ft] = snips
    ret = []
    for k, (_, s) in snips.snippets.items():
        if token in k:
            ret.append(s)
    for k, (_, s) in cache['all'].snippets.items():
        if token in k:
            ret.append(s)
    ret.sort(key=lambda x: x.trigger)
    return ret


def expand(fn, ft, trigger):
    try:
        logger.info("%s, %s", ft, trigger)
        snips = cache.get(ft, None)
        if snips is None:
            snips = cache.get(_ALL, None)
            if snips is None:
                return {}
        s = snips.snippets.get(trigger, None)
        if s is None:
            snips = cache.get(_ALL, {})
            s = snips.get(trigger, None)
            if s is None:
                return {}
        _, snippet = s
        g.current_snippet = snippet
        g.current_snips_info = snips
        content = snippet.render(snips.globals, fn, ft)
        lnum, col, length = snippet.jump_position()
        logger.info("jump: %s, %s, %s", lnum, col, length)
        return {
            'content': content,
            'lnum': lnum,
            'col': col,
            'length': length,
        }
    except Exception as e:
        logger.exception(e)
        raise


def jump(ft, direction):
    logger.info("jump %s", ft)
    snippet = g.current_snippet
    if snippet is None:
        return {}
    lnum, col, length = snippet.jump(direction)
    logger.info("jump: %s, %s, %s", lnum, col, length)
    return {
        'lnum': lnum,
        'col': col,
        'length': length,
    }


def reset_jump(ft):
    snip = g.current_snippet
    if snip is None:
        return
    snip.reset()
    g.current_snippet = None
    g.current_snips_info = None


def update_placeholder(fn, ft, content, line_delta, col):
    snip = g.current_snippet
    if snip is None:
        return {}
    line, col, length, updates = snip.update_placeholder(
        content, int(line_delta), int(col),
        g.current_snips_info.globals, fn, ft
    )
    logger.info("bb %s, %s, %s, %r", line, col, length, updates)
    return {
        'lnum': line,
        'col': col,
        'length': length,
        'updates': updates
    }


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
        bs = dict(builtins.__dict__)
        bs['print'] = _dumb_print
        self.globals = {'__builtins__': bs, 'vim': vim}
        self.extends = set([])
        self.snippets = {}

    def _eval_global(self, g):
        if g.tp != '!p':
            return
        exec(g.raw_body(), self.globals)

    def get(self, key, default=None):
        return self.snippets.get(key, default)

    def add_items(self, items):
        priority = 0
        for item in items:
            if not isinstance(item, Priority):
                continue
            priority = item.priority
            break

        logger.info("add %s", items)
        for item in items:
            logger.info(item)
            if isinstance(item, Extends):
                self.extends.update(item.types)
            if isinstance(item, Global):
                self._eval_global(item)
            if not isinstance(item, Snippet):
                continue
            s = self.snippets.get(item.trigger, None)
            if s is not None and s[0] > priority:
                continue
            self.snippets[item.trigger] = priority, item

    def load(self, ft, dirs):
        logger.info("load %s %s", ft, dirs)
        for d in dirs:
            self._load_in_dir(ft, d)

    def _load_in_dir(self, ft, d):
        logger.info("load in %s, %s", d, ft)
        files = glob.glob(os.path.join(d, '{}.snippets'.format(ft)))
        files.extend(glob.glob(os.path.join(d, '{}_*.snippets'.format(ft))))
        files.extend(glob.glob(os.path.join(d, ft, '*')))
        logger.info("files: %s", files)

        try:
            for f in files:
                with open(f) as r:
                    data = r.read()
                self.add_items(parse(data, filename=f))
        except Exception as e:
            logger.exception(e)
            raise
