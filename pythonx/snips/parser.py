# -*- coding: utf-8 -*-

from .ast import ParseError, Extends, Priority, Snippet, Global, \
    PreExpand, PostJump


class Doc(object):
    def __init__(self, fname):
        self.fname = fname
        self.stmts = []

    def parse_priority(self, lines, i):
        line = lines[i]
        parts = line.split()

        try:
            self.stmts.append(Priority(int(parts[1])))
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

        if len(parts) == 2:
            g.tp = parts[1]

        items = []

        for j, line in enumerate(lines[i+1:]):
            if line.rstrip().startswith("endglobal"):
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

        items = []

        for j, line in enumerate(lines[i+1:]):
            if line.rstrip().startswith("endsnippet"):
                s.body = "\n".join(items)
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


def parse(data, filename="<unknown>"):
    lines = data.splitlines()

    i = 0

    doc = Doc(filename)

    while i < len(lines):
        line = lines[i]

        stripped = line.strip()

        if not stripped or stripped[0] == '#':
            i += 1
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
