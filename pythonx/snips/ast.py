# -*- coding: utf-8 -*-

import logging
import collections
from .interpolation import SnippetUtil, tab_indent

logger = logging.getLogger('completor')

VISUAL_NUM = 9999


class Base(object):
    fname = '<unknown>'
    line = -1


class Extends(object):
    def __init__(self, types):
        self.types = types

    def __repr__(self):
        return "<Extends types={}>".format(",".join(self.types))


class Priority(object):
    def __init__(self, priority):
        self.priority = priority

    def __repr__(self):
        return "<Priority {}>".format(self.priority)


class _ExpandAction(object):
    name = "unknown"

    def __init__(self, body):
        self.body = body

    def __repr__(self):
        return "<{} body={}>".format(self.__class__.__name__, self.body)


class PreExpand(_ExpandAction):
    name = "pre_expand"


class PostExpand(_ExpandAction):
    name = "post_expand"


class PostJump(_ExpandAction):
    name = "post_jump"


class _Location(object):
    def __init__(self):
        self.line = -1
        self.column = -1

    def __repr__(self):
        return "{}:{}".format(self.line, self.column)


class _SnippetPart(object):
    TEXT = 'text'
    INTERPOLATION = 'interp'
    PLACEHOLDER = 'ph'

    def __init__(self, t=None, start_offset=0, end_offset=0):
        self.type = t
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.literal = ''
        self.number = None
        self.default = []
        self.editted = False
        self.ph_text = ''
        self.nest_level = 0
        self.placeholders = {}

        self.lnum = -1
        self.col = -1

        self.start = _Location()
        self.end = _Location()

    def _adjust_location(self, p, line, column):
        for d in p.default:
            start_line = d.start.line
            end_line = d.end.line

            d.start.line += line
            d.end.line += line

            if start_line == 0:
                d.start.column += column

            if end_line == 0:
                d.end.column += column

            if d.type == self.PLACEHOLDER:
                self._adjust_location(d, d.start.line, d.start.column)

    def render(self, g, context, ph, is_nested=False):
        text = ''

        if not is_nested:
            self.start.line = line = context['_line']
            self.start.column = column = context['_column']

        if self.type == self.TEXT:
            text = self.literal
        elif self.type == self.PLACEHOLDER:
            if is_nested:
                p = ph.get(self.number)
                if p is None:
                    v = ''
                    for d in self.default:
                        v += d.render(g, context, is_nested=True, ph=ph)
                else:
                    v = p.ph_text
            else:
                v = self.ph_text
                p = ph.get(self.number)
                if p:
                    v = p.ph_text
                    self._adjust_location(p, p.start.line, p.start.column)

            text = v
        elif self.type == self.INTERPOLATION:
            phs = {p.number: p.ph_text for p in ph.values()}
            logger.info("%r", phs)
            interp = Interpolation(self.literal)
            text = interp.gen_text(g, context, phs)

        tmp = text

        # \nhello\n\t\t
        # hello
        while not is_nested:
            i = tmp.find('\n')
            if i < 0:
                context['_column'] = column + len(tmp)
                break

            line = context['_line'] = line + 1
            context['_column'] = column = 0
            tmp = tmp[i+1:]

        if not is_nested:
            self.end.line = context['_line']
            self.end.column = context['_column']

        return text

    def append_literal(self, literal):
        if self.type is None:
            self.type = self.TEXT

        self.literal += literal

    def __repr__(self):
        if self.type == self.PLACEHOLDER:
            v = 'number={}'.format(self.number)
        else:
            v = 'content={!r}'.format(self.literal)

        return "<SnippetPart type={} loc={} {}>".format(
            self.type, (self.start, self.end), v)


class Snippet(Base):
    def __init__(self, trigger, description, options, body):
        self.trigger = trigger
        self.description = description
        self.options = options
        self.body = body
        self.body_parts = []
        self.ph_list = []
        self.placeholders = {}

        self.current_jump = None
        self.current_g = None
        self.current_context = None

    def is_block(self):
        return 'b' in self.options

    def clone(self):
        """Clone the snippet object.
        """
        return self.__class__(self.trigger, self.description, self.options,
                              self.body)

    def _parse_body(self, body=None, start=0, in_placeholder=False, nest=0):
        if body is None:
            body = self.body

        i = start

        parts = []

        current = _SnippetPart()
        while i < len(body):
            c = body[i]

            # Escape.
            if c == '\\':
                current.append_literal(body[i+1])
                i += 2
                continue

            # Placeholder.
            if c == '$' and body[i+1] in '0123456789{':
                current.end_offset = i
                parts.append(current)

                p, j = self._parse_tabstop(body, i + 1, i, nest)

                exist = self.placeholders.get(p.number)
                if not exist or exist.nest_level > nest:
                    self.placeholders[p.number] = p

                parts.append(p)
                current = _SnippetPart(start_offset=j)
                i = j
                continue

            # Interpolation.
            if c == '`':
                current.end_offset = i
                parts.append(current)
                current = _SnippetPart(
                    _SnippetPart.INTERPOLATION, start_offset=i)

                j = i + 1
                while j < len(body):
                    d = body[j]
                    # if d == '\\':
                    #     current.append_literal(body[j+1])
                    #     j += 2
                    #     continue

                    if d == '`':
                        i = current.end_offset = j + 1
                        parts.append(current)
                        current = _SnippetPart(start_offset=j+1)
                        break

                    current.append_literal(d)
                    j += 1

                continue

            if c == '}' and in_placeholder:
                current.end_offset = i
                parts.append(current)
                return parts, i + 1

            current.append_literal(c)
            i += 1

        current.end_offset = i
        parts.append(current)
        return parts, i

    # $12
    # ${12:self, }
    # ${12:Default value $0 111.}
    # ${12}
    # ${12:hello ${3:world} yoyo}
    # ${12:hello ${3:world ${4:ppppp} qq} yoyo}
    def _parse_tabstop(self, data, i, start, nest):
        p = _SnippetPart(_SnippetPart.PLACEHOLDER, start_offset=start)
        p.nest_level = nest

        n, j = _parse_tabstop_number(data, i)
        if n:
            p.number = int(n)
            p.end_offset = j
            return p, j

        if data[i] != '{':
            raise InvalidTabstop(self.fname, self.line)

        i += 1

        if data[i:].startswith('VISUAL'):
            n = VISUAL_NUM
            j = i + 6  # i + len('VISUAL')
        else:
            n, j = _parse_tabstop_number(data, i)
            if not n:
                raise InvalidTabstop(self.fname, self.line)

        p.number = int(n)

        if data[j] == '}':
            p.end_offset = j + 1
            return p, j + 1

        if data[j] != ':':
            raise InvalidTabstop(self.fname, self.line)

        parts, i = self._parse_body(data, start=j+1, in_placeholder=True,
                                    nest=nest+1)
        p.default = parts
        p.end_offset = i
        return p, p.end_offset

    def _render_placeholders(self, g, context):
        logger.info("%r", self.placeholders)

        for p in self.placeholders.values():
            p.ph_text = ''

            line = column = 0

            for d in p.default:
                d.start.line = line
                d.start.column = column

                tmp = text = d.render(g, context, is_nested=True,
                                      ph=self.placeholders)

                while True:
                    i = tmp.find('\n')
                    if i < 0:
                        column += len(tmp)
                        break

                    line += 1
                    column = 0
                    tmp = tmp[i+1:]

                d.end.line = line
                d.end.column = column

                p.ph_text += text
                logger.info("ph text %r", p.ph_text)

    def render(self, g, context):
        self.current_g = g
        self.current_context = context

        text = context.get('_prefix', '')

        if self.body and not self.body_parts:
            self.body_parts, _ = self._parse_body()
            self.ph_list = sorted(self.placeholders.values(),
                                  key=lambda x: x.number)

        context['_line'] = 0
        context['_column'] = 0

        self._render_placeholders(g, context)

        context['_line'] = 0
        context['_column'] = len(text)

        logger.info("%r", self.body_parts)

        for part in self.body_parts:
            if part.type is None:
                continue

            text += part.render(g, context, self.placeholders)

        logger.info("%r", text)

        line_map = collections.defaultdict(list)

        for p in self.placeholders.values():
            start_line = p.start.line
            end_line = p.end.line

            if start_line == end_line:
                line_map[start_line].append(p)
            else:
                line_map[start_line].append(p)
                line_map[end_line].append(p)

        logger.info("%r", self.ph_list)
        lines = 0
        end_pos = 0

        res = ''
        while True:
            i = text.find('\n')

            if i < 0:
                line = text
            else:
                line = text[:i]

            indented, offset = tab_indent(context, line, options=self.options)

            logger.info("line %r %r", indented, offset)
            for p in line_map.get(lines, []):
                if p.start.line == lines:
                    p.start.column += offset

                if p.end.line == lines:
                    p.end.column += offset

            if i < 0:
                res += indented
                end_pos = len(indented)
                break

            res += indented + '\n'
            text = text[i+1:]
            lines += 1

        res += context.get('_suffix', '')

        if self.current_jump is None:
            if self.ph_list and self.ph_list[0].number != 0:
                self.current_jump = 0
            else:
                self.current_jump = 1

        logger.info("%r", self.ph_list)
        logger.info("text %r", res)
        return res, end_pos

    def rerender(self, content):
        d = _SnippetPart()
        d.append_literal(content)

        if self.ph_list:
            p = self.ph_list[self.current_jump]

            numbers = []
            self._remove_ph(p, numbers)

            if numbers:
                self.ph_list = [
                    p for p in self.ph_list if p.number not in numbers]

            p.default = [d]
            p.editted = True

        return self.render(self.current_g, self.current_context)

    def _remove_ph(self, p, numbers):
        for s in p.default:
            if s.type != _SnippetPart.PLACEHOLDER:
                continue

            ph = self.placeholders.get(s.number)
            if ph is s:
                self.placeholders.pop(s.number)
                numbers.append(s.number)

                self._remove_ph(s, numbers)

    def reset(self):
        pass

    def jump_position(self):
        if not self.ph_list:
            return -1, -1, -1, -1

        if self.current_jump >= len(self.ph_list):
            self.current_jump = 0

        p = self.ph_list[self.current_jump]

        if p.end.line != p.start.line:
            return -1, -1, -1, -1

        column = p.start.column
        length = p.end.column - p.start.column
        if p.editted:
            column += len(p.ph_text)
            length = 0
        return p.start.line, p.start.column, column, length

    def jump(self, direction):
        if not self.ph_list:
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

    def __repr__(self):
        return "<Snippet trigger={}>".format(self.trigger)


class Global(object):
    def __init__(self, tp, body):
        self.tp = tp
        self.body = body


class Interpolation(Base):
    def __init__(self, value):
        self.value = value

    def gen_text(self, g, context, phs):
        content = self.value
        if content.startswith('!p'):
            return self.render_python(content[2:].lstrip(), g, context, phs)
        if content.startswith('!v'):
            return self.render_vim(content[2:].lstrip())

        # shell command.
        return self.render_shell(content)

    def render_python(self, codes, g, context, phs):
        snip = context.get('snip')
        if snip is None:
            snip = context['snip'] = SnippetUtil(context)
            snip._local = {
                'fn': context['fname'],
                'snip': snip,
            }
            snip.c = ''

        snip._local['t'] = phs
        snip.reset_indent()
        snip.rv = ''

        try:
            g['snip'] = snip
            exec(codes, g, snip._local)
        finally:
            g.pop('snip')
            snip.c = codes

        logger.info("py %r", snip.rv)
        return snip.rv

    def render_vim(self, codes):
        import vim
        return str(vim.eval(codes))

    def render_shell(self, command):
        import subprocess
        out = subprocess.check_output(command.split())
        return out.strip().decode('utf-8')


class ParseError(Exception):
    def __init__(self, file, line, msg):
        self.file = file
        self.line = line
        self.msg = msg

    def __str__(self):
        return "{}:{}: {}".format(self.file, self.line+1, self.msg)


class InvalidTabstop(ParseError):
    def __init__(self, file, line):
        ParseError.__init__(self, file, line, "invalid tabstop")


def _parse_tabstop_number(data, i):
    n = ''
    while i < len(data) and data[i] in '0123456789':
        n += data[i]
        i += 1
    return n, i
