# -*- coding: utf-8 -*-

import snips
from completor import Completor


class Snips(Completor):
    filetype = 'snips'
    sync = True

    def __init__(self, *args, **kwargs):
        Completor.__init__(self, *args, **kwargs)
        self._snippets_dirs = [
            v.decode() for v in self.get_option("snippets_dirs") or []]

    def parse(self, base):
        if not base or base.endswith((' ', '\t')):
            return []
        token = base.split()[-1]
        items = snips.get(self.ft_orig, token, self._snippets_dirs)
        offset = len(base) - len(token)
        candidates = [{
            'word': item.trigger,
            'dup': 1,
            'offset': offset,
            'menu': ' '.join(['[snip]', item.description]),
        } for item in items]

        index = token.rfind(base)
        if index > 0 and candidates:
            prefix = len(token[:index])
            for c in candidates:
                c['abbr'] = c['word']
                c['word'] = c['word'][prefix:]
        return candidates
