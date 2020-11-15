# -*- coding: utf-8 -*-

import functools

GROUPS = (
    'keyword',
    'comment',
    'trigger',
    'description',
    'option',
    'placeholder',
    'interpolation',
)


def _hi(group, line, column, length=None, end_line=None, end_column=None):
    h = {
        'line': line,
        'column': column,
        'group': 'snips_' + group,
    }

    if length is None:
        h['end_line'] = end_line
        h['end_column'] = end_column
    else:
        h['length'] = length

    return h


class _Hi(object):
    def __init__(self):
        for g in GROUPS:
            f = functools.partial(_hi, g)
            setattr(self, g, f)


hi = _Hi()
