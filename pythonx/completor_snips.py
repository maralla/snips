# -*- coding: utf-8 -*-

import logging
import snips
from completor import Completor


logger = logging.getLogger("completor")


class Snips(Completor):
    filetype = 'snips'
    sync = True

    def parse(self, base):
        if not base or base.endswith((' ', '\t')):
            return []
        token = base.split()[-1]
        items = snips.get(self.ft_orig, token)

        logger.info("items %r", items)

        offset = len(base) - len(token)
        candidates = [{
            'word': item.trigger,
            'dup': 1,
            'offset': offset,
            'menu': ' '.join(['[snipaa]', item.description]),
        } for item in items]

        index = token.rfind(base)
        if index > 0 and candidates:
            prefix = len(token[:index])
            for c in candidates:
                c['abbr'] = c['word']
                c['word'] = c['word'][prefix:]
        return candidates
