# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import re


def chunks(lst, n, fill=None):
    for i in range(0, len(lst), n):
        chunk = lst[i:i+n]
        if len(chunk) != n:
            chunk = chunk + (n-len(chunk))*[fill]
        yield chunk


def parse_texfile(word, stack):
    m = re.match(r'(\(*)([^()]*)(\)*)$', word)
    if not m:
        return word
    paren_open, filename, paren_close = m.groups()
    nopen = len(paren_open)
    nclose = len(paren_close)
    if (nopen or nclose) and (filename is '' or os.path.isfile(filename)):
        if nopen:
            stack.append(filename)
        if nclose:
            for _ in range(nclose):
                filename = stack.pop()
        return ''
    return word


def run(fin, fout):
    stack = ['ROOT']
    for line in fin:
        words = chunks(re.split(r'(\s+)', line), 2, '')
        linebuff = ''
        loc = (len(stack), stack[-1])
        for word, sep in words:
            if word is '' and sep is '':
                break
            word = parse_texfile(word, stack)
            if len(stack) < loc[0]:
                loc = (len(stack), stack[-1])
            linebuff += word + sep
        fout.write(loc[1] + ':' + linebuff)
    assert stack == ['ROOT']


if __name__ == '__main__':
    import sys
    run(sys.stdin, sys.stdout)
