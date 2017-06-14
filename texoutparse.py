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
                stack.pop()
        return ''
    return word


def parse_pdffig(word, stack):
    m = re.match(r'(<?)([^<>]*)(>?)(\]?)$', word)
    if not m:
        return word
    paren_open, filename, paren_close, rest = m.groups()
    nopen = len(paren_open)
    nclose = len(paren_close)
    if (nopen or nclose) and (filename is '' or os.path.isfile(filename)):
        if nopen:
            stack.append(filename)
        if nclose:
            stack.pop()
        return rest
    return word


def parse_page(word):
    m = re.match(r'(\[?)(\d*)({[^{}]+})?(\]?)$', word)
    if not m:
        return word
    paren_open, page, _, paren_close = m.groups()
    nopen = len(paren_open)
    nclose = len(paren_close)
    if nopen or nclose:
        return ''
    return word


def run(fin, fout):
    stack = ['ROOT']
    in_package = None
    lines = ['']
    for line in fin:
        words = chunks(re.split(r'(\s+)', line), 2, '')
        m = re.match('Package (\w+) \w+: ', line)
        if m or (in_package and line.startswith('({0})'.format(in_package))):
            if m:
                in_package = m.group(1)
            else:
                next(words)
                lines[0] += ' '
                lines.append('\n')
            for word, sep in words:
                lines[0] += word + sep
            lines[0] = lines[0].rstrip()
            continue
        if in_package:
            in_package = False
            lines[0] += '\n'
            lines.append('')
        loc = (len(stack), stack[-1])
        for word, sep in words:
            if word is '' and sep is '':
                break
            word = parse_texfile(word, stack)
            word = parse_pdffig(word, stack)
            word = parse_page(word)
            if len(stack) < loc[0]:
                loc = (len(stack), stack[-1])
            lines[-1] += word + sep
        while lines:
            fout.write(loc[1] + ':' + lines.pop(0))
        lines = ['']
    assert stack == ['ROOT']


if __name__ == '__main__':
    import sys
    run(sys.stdin, sys.stdout)
