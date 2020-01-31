# -*- coding: utf-8 -*-

from .packages.ply.lex import lex
from .packages.ply.yacc import yacc

from .ast import ParseError, Extends, Priority, Snippet, SnippetStart, \
    Global, Placeholder, Interpolation, Text


class SnipsParser(object):
    keywords = (
        'EXTENDS',
        'PRIORITY',
        'ENDSNIPPET',
        'GLOBAL',
        'ENDGLOBAL',
    )

    tokens = keywords + (
        'SNIPPET_START',
        'WHITESPACE',
        'COMMA',
        'DOLLAR',
        'LBRACE',
        'RBRACE',
        'NEWLINE',
        'COLON',
        'INTEGER',
        'COMMENT',
        'VISUAL',
        'REGEX',
        'ESCAPE_CHAR',
        'INTERPOLATION',
        'NO_WHITESPACE',
        'ANY',
    )

    def __init__(self):
        self.lexer = lex(module=self)
        self.parser = yacc(module=self)
        self.filename = '<unknown>'

    def parse(self, data, debug=False, filename=None):
        if filename is not None:
            self.filename = filename
        self.lexer.lineno = 1
        return self.parser.parse(data, debug=debug)

    def tokenize(self, data):
        self.lexer.input(data)
        return self.lexer

    def t_NEWLINE(self, t):
        r'\n'
        t.lexer.lineno += 1
        return t

    def t_COMMENT(self, t):
        r'(?m)^\s*\#[^\n]*'
        return t

    def t_EXTENDS(self, t):
        'extends'
        return t

    def t_PRIORITY(self, t):
        'priority'
        return t

    def t_ENDSNIPPET(self, t):
        'endsnippet'
        return t

    def t_SNIPPET_START(self, t):
        r'snippet\s+[^\n]+'
        return t

    def t_GLOBAL(self, t):
        'global'
        return t

    def t_ENDGLOBAL(self, t):
        'endglobal'
        return t

    def t_COMMA(self, t):
        ','
        return t

    def t_COLON(self, t):
        ':'
        return t

    def t_DOLLAR(self, t):
        '\$'
        return t

    def t_LBRACE(self, t):
        r'\{'
        return t

    def t_RBRACE(self, t):
        r'\}'
        return t

    def t_REGEX(self, t):
        r'/[^/\n]+/[^/\n]*/[gima]*'
        return t

    def t_INTEGER(self, t):
        r'-?\d+'
        t.value = int(t.value)
        return t

    def t_WHITESPACE(self, t):
        r'[ \t]+'
        return t

    def t_VISUAL(self, t):
        r'VISUAL'
        return t

    def t_ESCAPE_CHAR(self, t):
        r'\\.'
        return t

    def t_INTERPOLATION(self, t):
        '`[^`]*`'
        t.lexer.lineno += t.value.count('\n')
        return t

    def t_NO_WHITESPACE(self, t):
        r'[^ \t\n,"$`}{]+'
        return t

    def t_ANY(self, t):
        r'[^\n]+'
        return t

    def t_error(self, t):
        raise ParseError(self.filename, t.lineno,
                         "illegal character '{}'".format(t.value[0]))

    def p_doc(self, p):
        '''doc : statement
            | statement doc'''
        p[0] = []
        if p[1] is not None:
            p[0].append(p[1])
        if len(p) == 3:
            p[0].extend(p[2])

    def p_statement(self, p):
        '''statement : EXTENDS WHITESPACE extends_item NEWLINE
                     | PRIORITY WHITESPACE INTEGER NEWLINE
                     | snippet
                     | global
                     | COMMENT
                     | whitespace NEWLINE'''
        if p[1] == 'extends':
            p[0] = Extends(p[3])
        elif p[1] == 'priority':
            p[0] = Priority(p[3])
        elif isinstance(p[1], (Snippet, Global)):
            p[0] = p[1]
        else:
            p[0] = None

    def p_snippet(self, p):
        '''snippet : snippet_start NEWLINE snippet_body ENDSNIPPET whitespace NEWLINE'''  # noqa
        p[0] = Snippet(p[1].trigger, p[1].description, p[1].options, p[3])

    def p_global(self, p):
        '''global : GLOBAL WHITESPACE NO_WHITESPACE whitespace NEWLINE snippet_body ENDGLOBAL whitespace NEWLINE''' # noqa
        p[0] = Global(p[3], p[6])

    def p_extends_item(self, p):
        '''extends_item : NO_WHITESPACE whitespace
                        | NO_WHITESPACE whitespace COMMA whitespace extends_item'''  # noqa
        if len(p) == 3:
            p[0] = [p[1]]
        else:
            p[0] = [p[1]] + p[5]

    def p_snippet_start(self, p):
        '''snippet_start : SNIPPET_START'''
        # snippet !this is trigger! "description" b
        trigger, description, options = parse_snippet_start(p, p[1])
        p[0] = SnippetStart(trigger, description, options)

    def p_snippet_body(self, p):
        '''snippet_body : snippet_line snippet_body
                        |'''
        if len(p) == 3:
            p[0] = [p[1]] + p[2]
        else:
            p[0] = []

    def p_snippet_line(self, p):
        '''snippet_line : NEWLINE
                        | placeholder snippet_line
                        | interpolation snippet_line
                        | text snippet_line'''
        if len(p) == 3:
            p[0] = [p[1]] + p[2]
        else:
            p[0] = [Text(p[1])]

    def p_placeholder(self, p):
        '''placeholder : DOLLAR INTEGER
                       | DOLLAR LBRACE INTEGER RBRACE
                       | DOLLAR LBRACE VISUAL RBRACE
                       | DOLLAR LBRACE VISUAL COLON placeholder_default RBRACE
                       | DOLLAR LBRACE INTEGER COLON placeholder_default RBRACE
                       | DOLLAR LBRACE INTEGER REGEX whitespace RBRACE'''  # noqa
        sub = ''
        tp = 'normal'
        if len(p) == 3:
            p[0] = Placeholder(p[2])
        elif len(p) >= 5:
            default = ()
            if len(p) == 7:
                if p[4] == ':':
                    default = p[5]
                else:
                    sub = p[4]
                    tp = 'sub'
            p[0] = Placeholder(p[3], default, sub=sub, tp=tp)

    def p_placeholder_default(self, p):
        '''placeholder_default : placeholder_default_content placeholder_default
                               |'''
        p[0] = []
        if len(p) == 3:
            p[0] = [p[1]] + p[2]

    def p_placeholder_default_content(self, p):
        '''placeholder_default_content : NO_WHITESPACE
                                       | ESCAPE_CHAR
                                       | WHITESPACE
                                       | INTEGER
                                       | COMMA
                                       | interpolation
                                       | placeholder'''
        if not isinstance(p[1], Placeholder):
            p[0] = Text(p[1])
        else:
            p[0] = p[1]

    def p_interpolation(self, p):
        '''interpolation : INTERPOLATION'''
        p[0] = Interpolation(p[1])

    def p_text(self, p):
        '''text : ESCAPE_CHAR
                | NO_WHITESPACE
                | WHITESPACE
                | COMMENT
                | DOLLAR
                | COLON
                | LBRACE
                | RBRACE
                | VISUAL
                | COMMA
                | INTEGER
                | ANY'''
        p[0] = Text(p[1])

    def p_whitespace(self, p):
        '''whitespace : WHITESPACE
                    |'''
        if len(p) == 2:
            p[0] = Text(p[1])
        else:
            p[0] = Text('')

    def p_error(self, p):
        raise ParseError(self.filename, p.lineno,
                         "Syntax error at '{}'".format(p))


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


# snippet trigger_word [ "description" [ options ] ]
def parse_snippet_start(p, text):
    text = text.strip()
    options = description = ''
    if text[-1] != '"':
        # options may exists.
        parts = text.rsplit(maxsplit=1)
        if len(parts) != 2:
            raise ParseError(p.file, p.line, "invalid snippet definition")
        remain, opt = parts
        if remain[-1] != '"':
            # no options and description exist.
            trigger = text[7:]
        else:
            trigger, description = _parse_snippet_description(text, remain)
            if description:
                options = opt
    else:
        trigger, description = _parse_snippet_description(text, text)
    trigger = trigger.strip()
    if len(trigger.split()) > 1:
        if trigger[0] != trigger[-1]:
            raise ParseError(
                p.file, p.line,
                "invalid snippet trigger definition `{}`".format(trigger))
        trigger = trigger[1:-1].strip()
    if not trigger:
        raise ParseError(p.file, p.line, "snippet no trigger defined")
    return trigger, description, options


parser = SnipsParser()


def parse(data, filename=None, debug=False):
    return parser.parse(data, debug=debug, filename=filename)
