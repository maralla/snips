# -*- coding: utf-8 -*-

import logging
from .ast import ParseError, Extends, Priority, Snippet, Global, \
    PreExpand, PostJump, Comment, parse_snippet_body
from .highlight import hi

logger = logging.getLogger('completor')


class Doc(object):
    def __init__(self, fname):
        self.parse_body = False
        self.fname = fname
        self.stmts = []

    def parse_comment(self, lines, i):
        line = lines[i]

        pos = _nonempty(line)
        c = Comment(line[pos+1:])
        c.line = i
        c.column = pos
        self.stmts.append(c)

        return i + 1

    def parse_priority(self, lines, i):
        line = lines[i]
        parts = line.split()

        try:
            p = Priority(int(parts[1]))
            self.stmts.append(p)
        except Exception as e:
            raise ParseError(self.fname, i, line)

        return i + 1

    def parse_extends(self, lines, i):
        line = lines[i]
        parts = line.split(maxsplit=1)

        if len(parts) != 2:
            raise ParseError(self.fname, i, "invalid extends")

        self.stmts.append(Extends([t.strip() for t in parts[1].split(',')]))
        return i + 1

    @staticmethod
    def _parse_snippet_description(text, remain):
        description = ''
        index = remain[:-1].rfind('"')
        if index == -1:
            # no string found
            trigger = text[7:]
        elif remain[index-1] not in (' \t'):
            trigger = text[7:]
        else:
            trigger = remain[7:index].strip()
            if not trigger:
                trigger = text[7:]
            else:
                description = remain[index+1:-1]
        return trigger, description

    def _parse_snippet_start(self, i, text):
        text = text.strip()
        options = description = ''
        if text[-1] != '"':
            # options may exists.
            parts = text.rsplit(maxsplit=1)
            if len(parts) != 2:
                raise ParseError(self.fname, i, "invalid snippet definition")
            remain, opt = parts
            if remain[-1] != '"':
                # no options and description exist.
                trigger = text[7:]
            else:
                trigger, description = self._parse_snippet_description(
                    text, remain)
                if description:
                    options = opt
        else:
            trigger, description = self._parse_snippet_description(text, text)
        trigger = trigger.strip()
        # Space in trigger or the trigger is regex.
        if len(trigger.split()) > 1 or "r" in options:
            if trigger[0] != trigger[-1]:
                raise ParseError(
                    self.fname, i,
                    "invalid snippet trigger definition `{}`".format(trigger))
            trigger = trigger[1:-1]

        if not trigger:
            raise ParseError(self.fname, i, "snippet no trigger defined")

        return trigger, description, options

    def parse_global(self, lines, i):
        line = lines[i]
        parts = line.split()

        g = Global("unknown", "")
        g.line = i
        g.column = _nonempty(line)

        if len(parts) == 2:
            g.tp = parts[1]

        items = []

        for j, line in enumerate(lines[i+1:]):
            if line.rstrip().startswith("endglobal"):
                g.hi_groups.append(hi.keyword(j+i+1, _nonempty(line), 9))

                g.body = "\n".join(items)
                self.stmts.append(g)
                return i + j + 2

            items.append(line)

        raise ParseError(self.fname, i, "no endglobal found")

    def parse_snippet(self, lines, i):
        line = lines[i]

        trigger, desc, opts = self._parse_snippet_start(i, line)

        s = Snippet(trigger, desc, opts, "")
        s.fname = self.fname
        s.line = i
        s.column = _nonempty(line)

        trigger_pos = line.find(trigger)
        s.hi_groups.append(hi.trigger(i, trigger_pos, len(trigger)))

        desc_pos = trigger_pos
        if desc:
            desc_pos = line.find(desc, trigger_pos + len(trigger))
            s.hi_groups.append(hi.description(i, desc_pos, len(desc)))

        if opts:
            pos = line.find(opts, desc_pos + len(desc))
            s.hi_groups.append(hi.option(i, pos, len(opts)))


        items = []

        for j, line in enumerate(lines[i+1:]):
            if line.rstrip().startswith("endsnippet"):
                s.hi_groups.append(hi.keyword(j+i+1, _nonempty(line), 10))
                s.body = "\n".join(items)

                if self.parse_body:
                    phs = {}
                    parse_snippet_body(s.body, phs)

                    for ph in phs.values():
                        b = s.body[:ph.start_offset]
                        n = b.count('\n')
                        p = b.rfind('\n')
                        if p > 0:
                            c = ph.start_offset - p -1
                        else:
                            c = ph.start_offset

                        s.hi_groups.append(hi.placeholder(
                            i+1+n, c, ph.end_offset-ph.start_offset))

                self.stmts.append(s)
                return i + j + 2

            items.append(line)

        raise ParseError(self.fname, i, "no endsnippet found")

    def parse_expand_action(self, lines, i, action):
        line = lines[i]

        parts = line.split(maxsplit=1)

        if len(parts) != 2:
            raise ParseError(self.fname, i,
                             "invalid {} definition".format(action.name))

        content = parts[1]
        if len(content) < 2 or content[0] != content[-1] or content[0] != '"':
            raise ParseError(self.fname, i,
                             "invalid {} definition".format(action.name))

        self.stmts.append(action(content[1:-1]))
        return i + 1


def gen_highlight_groups(data):
    try:
        stmts = parse(data, is_lines=True, parse_body=True)
    except ParseError:
        stmts = []

    groups = []

    for s in stmts:
        groups.extend(s.gen_hi_groups())

    logger.info("%r", groups)

    return groups


def parse(data, filename="<unknown>", is_lines=False, parse_body=False):
    if is_lines:
        lines = data
    else:
        lines = data.splitlines()

    i = 0

    doc = Doc(filename)
    doc.parse_body = parse_body

    while i < len(lines):
        line = lines[i]

        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped[0] == '#':
            i = doc.parse_comment(lines, i)
            continue

        if stripped.startswith('priority'):
            i = doc.parse_priority(lines, i)
            continue

        if stripped.startswith('global'):
            i = doc.parse_global(lines, i)
            continue

        if stripped.startswith('snippet'):
            i = doc.parse_snippet(lines, i)
            continue

        if stripped.startswith('extends'):
            i = doc.parse_extends(lines, i)
            continue

        if stripped.startswith(PreExpand.name):
            i = doc.parse_expand_action(lines, i, PreExpand)
            continue

        if stripped.startswith(PostJump.name):
            i = doc.parse_expand_action(lines, i, PostJump)
            continue

        raise ParseError(filename, i, "unknown syntax")

        i += 1

    return doc.stmts


def _nonempty(text):
    i = 0
    while text and text[i] in " \t":
        pass
    return i
