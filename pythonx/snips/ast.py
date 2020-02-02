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
        phs = {p.index: p.to_text() for p in self.placeholders}
        if 9999 in phs:
            phs['VISUAL'] = phs[9999]
        text = ''
        logger.info("%r", phs)
        for item in self.body:
            for e in item:
                line_offset = text.count('\n')
                cols = text.rfind('\n')
                if cols == -1:
                    col_offset = len(text)
                else:
                    col_offset = len(text) - cols - 1
                if isinstance(e, Interpolation):
                    logger.info("in off: %s", col_offset)
                    text += e.render(line_offset, col_offset, g, fn, ft, phs)
                    logger.info("after %s", text)
                elif isinstance(e, Placeholder):
                    logger.info("888888888 %s %s", col_offset, e.raw())
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
        self.current_jump = None
        self.placeholders = self.interpolations = None

    def render(self, g, fn, ft):
        self.placeholders, self.interpolations = self._fetch_placeholders(
            g, fn, ft)
        logger.info("%r", self.placeholders)
        self._init_jump_position()
        return _BodyMixin.render(self, g, fn, ft)

    def _init_jump_position(self):
        if len(self.placeholders) > 1 and self.placeholders[0].index == 0:
            self.current_jump = 1
        elif self.placeholders:
            self.current_jump = 0

    def reset(self):
        self._init_jump_position()

        for p in self.placeholders:
            p.value = None
            p.text = None

    def update_placeholder(self, content, line_delta, col, g, fn, ft):
        logger.info("update content: %r", content)
        if self.current_jump is None:
            return
        ph = self.placeholders[self.current_jump]
        if ph.value is None:
            ph.value = ''
        if content:
            ph.value += content
        trunc_offset = ph.col_offset
        if line_delta > 0:
            trunc_offset = 1
        elif line_delta < 0:
            trunc_offset = col + 1
        if col < ph.col_offset or line_delta < 0:
            logger.info("truncate: %s, %s", col, trunc_offset)
            ph.value = ph.value[:len(ph.value) - trunc_offset + col]
        logger.info("value: %r, %s", ph.value, line_delta)
        index = content.rfind('\n')

        for p in self.placeholders[self.current_jump + 1:]:
            self._update_offset(p, ph, len(content), index, line_delta, col)
            logger.info("ph offset %s, %s, %s", p.raw(), p.line_offset, p.col_offset)

        for i in self.interpolations:
            self._update_offset(i, ph, len(content), index, line_delta, col)
            logger.info("ip offset %s, %s", i.line_offset, i.col_offset)

        ph.line_offset += line_delta
        ph.col_offset = col
        ph.length = 0

        logger.info("offset %s, value %r", ph.col_offset, ph.value)

        updates = self._rerender_interpolations(g, fn, ft)

        for p in self.placeholders:
            logger.info("update col offset: %s, %s, %s", p.raw(), p.col_offset, p.line_offset)

        return ph.line_offset, ph.col_offset, ph.length, updates

    def _populate_offsets(self, base_line, base_col, line_delta, col_delta,
                          remain):
        logger.info("update: %r, %s, %s, %s", base_line, base_col, line_delta, col_delta)
        for p in self.placeholders:
            if p.line_offset < base_line:
                continue
            if p.line_offset == base_line:
                if p.col_offset <= base_col and line_delta == 0:
                    continue
                p.col_offset += col_delta
            p.line_offset += line_delta

    def _rerender_interpolations(self, g, fn, ft):
        phs = {p.index: p.to_text() for p in self.placeholders}
        if 9999 in phs:
            phs['VISUAL'] = phs[9999]
        updates = []
        for i in self.interpolations:
            text = i.gen_text(g, fn, ft, phs)
            if text == i.text:
                continue
            length = len(i.text)
            prev_lines = i.text.count('\n')
            prev_last = i.text.rsplit('\n', 1)[-1]
            i.text = text
            lines = text.count('\n')
            last = text.rsplit('\n', 1)[-1]
            updates.append({
                'content': text,
                'line_offset': i.line_offset,
                'col_offset': i.col_offset,
                'length': length,
            })
            self._populate_offsets(i.line_offset, i.col_offset,
                                   lines - prev_lines,
                                   len(last) - len(prev_last), [])
        return updates

    def _update_offset(self, obj, ph, content_length, nl_index, line_delta,
                       col):
        if obj.line_offset == ph.line_offset:
            if line_delta == 0:
                logger.info("offset: %s, %s, %s, %s", obj.col_offset,
                            ph.col_offset, col, ph.length)
                if obj.col_offset > ph.col_offset or \
                        (obj.col_offset == ph.col_offset and obj.seq > ph.seq):
                    obj.col_offset += col - ph.col_offset - ph.length
            else:
                obj.col_offset = obj.col_offset - ph.col_offset - ph.length + \
                    content_length - nl_index
        obj.line_offset += line_delta

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
        self.current_jump = sign * (abs(self.current_jump) %
                                    len(self.placeholders))
        return self.jump_position()

    def _fetch_placeholders(self, g, fn, ft):
        phs = []
        ips = []
        i = -1
        for item in self.body:
            for e in item:
                i += 1
                e.seq = i
                if isinstance(e, Placeholder):
                    e.render(0, 0, g, fn, ft)
                    phs.append(e)
                elif isinstance(e, Interpolation):
                    ips.append(e)
        phs.sort(key=lambda x: x.index)
        return phs, ips


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
        self.seq = 0
        self.value = None
        self.text = None
        self.index = index
        if index == 'VISUAL':
            self.index = 9999
        self.default = default
        self.sub = sub
        self.tp = tp
        self.orig_line = self.orig_col = self.line_offset = self.col_offset = 0
        self.orig_length = self.length = 0
        self.orig_text = ''
        self._body = _Body([self.default])

    def raw(self):
        return '${{{}:{}}}'.format(self.index, self._body.raw_body())

    def __repr__(self):
        return self.raw()

    def render(self, line_offset, col_offset, g, fn, ft):
        self.orig_line = self.line_offset = line_offset
        self.orig_col = self.col_offset = col_offset
        if self.text is not None:
            return self.text
        text = self.gen_text(g, fn, ft)
        self.orig_length = self.length = len(text)
        self.text = text
        return text

    def gen_text(self, g, fn, ft):
        return self._body.render(g, fn, ft)

    def to_text(self):
        if self.value is not None:
            return self.value
        if self.text is not None:
            return self.text
        return ''


class Interpolation(Base):
    def __init__(self, value):
        self.seq = 0
        self.value = value
        self.line_offset = -1
        self.col_offset = -1
        self.text = ''

    def to_text(self):
        return self.value

    def render(self, line, col, g, fn, ft, phs):
        self.line_offset = line
        self.col_offset = col
        self.text = self.gen_text(g, fn, ft, phs)
        return self.text

    def gen_text(self, g, fn, ft, phs):
        content = self.value[1:-1]
        if content.startswith('!p'):
            return self.render_python(content[2:].lstrip(), g, fn, ft, phs)
        if content.startswith('!v'):
            return self.render_vim(content[2:].lstrip())
        return content

    def render_python(self, codes, g, fn, ft, phs):
        snip = SnippetUtil(fn, ft)
        try:
            local = {
                'snip': snip,
                't': phs,
            }
            g['snip'] = snip
            exec(codes, g, local)
        finally:
            g.pop('snip')
            snip.c = ''
        return str(snip.rv)

    def render_vim(self, codes):
        import vim
        return str(vim.eval(codes))


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
