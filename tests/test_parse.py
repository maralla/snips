import pytest
import os
import glob
from subprocess import call

from snips.parser import parse
from snips.ast import Snippet

snippets = 'https://github.com/honza/vim-snippets.git'


@pytest.fixture(scope='module')
def snippets_dir(current_dir):
    d = os.path.join(current_dir, 'data', 'vim-snippets')

    if not os.path.exists(d):
        retcode = call(['git', 'clone', snippets, d])
        if retcode != 0:
            raise Exception('clone vim-snippets failed')

    return os.path.join(d, 'UltiSnips')


def test_parse(snippets_dir):
    items = glob.glob(os.path.join(snippets_dir, '*'))

    for item in items:
        _, ext = os.path.splitext(item)
        if ext != '.snippets':
            continue

        with open(item) as f:
            data = f.read()

        parse(data, filename=item)


def test_parse_snippet():
    s = Snippet('', '', '', '')

    s.body = 'Indent is'
    assert s._parse_body()[0][0].literal == 'Indent is'

    s.body = 'Indent is: `!v indent(".")`.'
    assert s._parse_body()[0][1].literal == '!v indent(".")'

    s.body = r'`!p snip.rv = \`aaa\``'
    assert s._parse_body()[0][1].literal == r'!p snip.rv = `aaa`'

    s.body = r'''def ${1:function}(`!p
if snip.indent:
    snip.rv = 'self' + (", " if len(t[2]) else "")`${2:arg1}):
    `!p snip.rv = triple_quotes(snip)`${4:TODO: Docstring for $1.}`!p
write_function_docstring(t, snip) `
    ${5:${VISUAL:pass}}
'''
    d = s._parse_body()[0]
    assert d[3].type == 'interp'
    assert d[7].type == 'interp'
    assert d[11].type == 'interp'

    s.body = 'def ${1:fname}(`!p snip.rv = "self, " if snip.indent else ""`$2):\n\t$0'  # noqa
    d = s._parse_body()[0]
    assert d[3].literal == '!p snip.rv = "self, " if snip.indent else ""'
