# -*- coding: utf-8 -*-

import functools

GROUPS = (
    'keyword',
    'comment',
    'trigger',
    'description',
    'option',
    'placeholder',
)


def _hi(group, line, column, length):
    return {
        'line': line,
        'column': column,
        'length': length,
        'group': 'snips_' + group
    }


class _Hi(object):
    def __init__(self):
        for g in GROUPS:
            f = functools.partial(_hi, g)
            setattr(self, g, f)


hi = _Hi()
