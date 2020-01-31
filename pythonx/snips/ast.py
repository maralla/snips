# -*- coding: utf-8 -*-

import logging
from .interpolation import SnippetUtil

logger = logging.getLogger('completor')


class Base(object):
    def to_text(self):
        return ''


class _BodyMixin(object):
    def raw_body(self):
        text = ''
        for item in self.body:
            for e in item:
                text += e.to_text()
        return text

    def render(self, g, fn, ft):
        phs = [p.to_text() for p in self.placeholders]
        text = ''
        for item in self.body:
            for e in item:
                if isinstance(e, Interpolation):
                    text += e.render(g, fn, ft, phs)
                elif isinstance(e, Placeholder):
                    line_offset = text.count('\n')
                    cols = text.rfind('\n')
                    if cols == -1:
                        col_offset = len(text)
                    else:
                        col_offset = len(text) - cols - 1
                    text += e.render(line_offset, col_offset, g, fn, ft)
                else:
                    text += e.to_text()
        return text


class Extends(object):
    def __init__(self, types):
        self.types = types


class Priority(object):
    def __init__(self, priority):
        self.priority = priority


class SnippetStart(object):
    def __init__(self, trigger, description, options):
        self.trigger = trigger
        self.description = description
        self.options = options


class Snippet(_BodyMixin):
    def __init__(self, trigger, description, options, body):
        self.trigger = trigger
        self.description = description
        self.options = options
        self.body = body
        self.placeholders = self._fetch_placeholders()
        self.current_jump = None
        self.reset()

    def reset(self):
        if len(self.placeholders) > 1 and self.placeholders[0].index == 0:
            self.current_jump = 1
        elif self.placeholders:
            self.current_jump = 0

    def update_placeholder(self, content, line_delta, col):
        logger.info("update content: %r", content)
        if self.current_jump is None:
            return
        ph = self.placeholders[self.current_jump]
        if ph.value is None:
            ph.value = ''
        if col > ph.col_offset and content is not None:
            ph.value += content
        elif col < ph.col_offset:
            ph.value = ph.value[:ph.col_offset - col]
        logger.info("value: %r", ph.value)
        index = content.rfind('\n')
        for p in self.placeholders[self.current_jump+1:]:
            if p.line_offset == ph.line_offset:
                if line_delta == 0:
                    logger.info("offset: %s, %s, %s", p.col_offset, ph.col_offset, col)  # noqa
                    p.col_offset += col - ph.col_offset - ph.length
                else:
                    p.col_offset = p.col_offset - ph.col_offset - ph.length + len(content) - index  # noqa
            p.line_offset += line_delta
        ph.line_offset += line_delta
        ph.col_offset = col
        logger.info("offset %s", ph.col_offset)
        ph.length = 0
        return ph.line_offset, ph.col_offset, ph.length

    def jump_position(self):
        if self.current_jump is None:
            return -1, -1, -1
        j = self.placeholders[self.current_jump]
        return j.line_offset, j.col_offset, j.length

    def jump(self, direction):
        if self.current_jump is None:
            return -1, -1, -1
        sign = 1
        if direction == 'forward':
            self.current_jump += 1
        else:
            self.current_jump -= 1
            if self.current_jump < 0:
                sign = -1
        self.current_jump = sign * (
            abs(self.current_jump) % len(self.placeholders))
        return self.jump_position()

    def _fetch_placeholders(self):
        phs = []
        for item in self.body:
            for e in item:
                if not isinstance(e, Placeholder):
                    continue
                phs.append(e)
        phs.sort(key=lambda x: x.index)
        return phs


class Global(_BodyMixin):
    def __init__(self, tp, body):
        self.tp = tp
        self.body = body


class _Body(_BodyMixin):
    def __init__(self, body):
        self.placeholders = []
        self.body = body


class Placeholder(Base):
    def __init__(self, index, default=(), sub='', tp='normal'):
        self.value = None
        self.index = index
        self.default = default
        self.sub = sub
        self.tp = tp
        self.orig_line = self.orig_col = self.line_offset = self.col_offset = 0
        self.orig_length = self.length = 0
        self.orig_text = ''
        self._body = _Body([self.default])

    def raw(self):
        return '${{{}:{}}}'.format(self.index, self._body.raw_body())

    def render(self, line_offset, col_offset, g, fn, ft):
        self.orig_line = self.line_offset = line_offset
        self.orig_col = self.col_offset = col_offset
        text = self._body.render(g, fn, ft)
        self.orig_length = self.length = len(text)
        return text

    def to_text(self):
        return self.raw()


class Interpolation(Base):
    def __init__(self, value):
        self.value = value

    def to_text(self):
        return self.value

    def render(self, g, fn, ft, phs):
        content = self.value[1:-1]
        if content.startswith('!p'):
            return self.render_python(content[2:].lstrip(), g, fn, ft, phs)
        return content

    def render_python(self, codes, g, fn, ft, phs):
        snip = SnippetUtil(fn, ft)
        try:
            local = {
                'snip': snip,
                't': phs,
            }
            exec(codes, g, local)
        finally:
            snip.c = ''
        return str(snip.rv)


class Text(Base):
    def __init__(self, value):
        self.value = value

    def to_text(self):
        return str(self.value)

    def __repr__(self):
        return repr(self.to_text())


class ParseError(Exception):
    def __init__(self, file, line, msg):
        self.file = file
        self.line = line
        self.msg = msg

    def __repr__(self):
        return "{}:{}: {}".format(self.file, self.line, self.msg)
