# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import re
import io
import sys

# TODO isolated ), >

DEBUG = bool(os.environ.get('DEBUG'))


def debug(*args):
    if DEBUG:
        print('DEBUG:', *args, file=sys.stderr)


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
    if (nopen and filename or nclose) and \
            (filename is '' or os.path.isfile(filename)):
        if nopen:
            stack.append(filename)
            debug('pushed', word, filename)
        if nclose:
            for _ in range(nclose):
        return ''
                debug('popped', word, stack.pop())
    return word


def parse_pdffig(word, stack):
    m = re.match(r'(<?)([^<>]*)(>?)(\]?\)?)$', word)
    if not m:
        return word
    paren_open, filename, paren_close, rest = m.groups()
    nopen = len(paren_open)
    nclose = len(paren_close)
    if (nopen or nclose) and (filename is '' or os.path.isfile(filename)):
        if nopen:
            stack.append(filename)
            debug('pushed', filename, word)
        if nclose:
            debug('popped', stack.pop(), word)
        return rest
    return word


def parse_page(word, stack):
    m = re.match(r'(\[?)(\d*)({[^{}]+})?(\]?)(\)?)$', word)
    if not m:
        return word
    paren_open, page, _, paren_close, rest = m.groups()
    nopen = len(paren_open)
    nclose = len(paren_close)
    if nopen and page or nclose:
        if nopen:
            name = stack[-1] + ':[{}]'.format(page)
            stack.append(name)
            debug('pushed', name, word)
        if nclose:
            debug('popped', stack.pop(), word)
        return rest
    return word


def run(fin, fout, skip_empty=False):
    stack = ['ROOT']
    in_package = None
    lines = ['']
    for line in fin.buffer:
        try:
            line = line.decode()
        except UnicodeDecodeError as e:
            fout.write(stack[-1] + ':' + str(line) + '\n')
            continue
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
            word = parse_pdffig(word, stack)
            word = parse_page(word, stack)
            word = parse_texfile(word, stack)
            if len(stack) < loc[0]:
                loc = (len(stack), stack[-1])
            lines[-1] += word + sep
        while lines:
            line = lines.pop(0)
            if skip_empty and not line.strip():
                continue
            fout.write(loc[1] + ':' + line)
        lines = ['']
    if stack != ['ROOT']:
        raise RuntimeError('Invalid final stack:', stack)


def select_last(fin, fout, **kwargs):
    foutbuff = io.StringIO()
    run(fin, foutbuff, **kwargs)
    current = None
    last = None
    for line in foutbuff.getvalue().split('\n'):
        if line.startswith('ROOT:This is pdfTeX'):
            current = ''
        if current is not None:
            current += line + '\n'
        if line.startswith('ROOT:Transcript written'):
            assert current
            last = current
            current = None
    assert not current
    if not last:
        raise RuntimeError('No pdftex output found')
    fout.write(last)


def parse_cli():
    from argparse import ArgumentParser
    parser = ArgumentParser()
    arg = parser.add_argument
    arg('-n', action='store_true', dest='skip_empty', help='skip empty lines')
    arg('-l', action='store_true', dest='only_last', help=(
        'if multiple pdftex runs, print only last '
        '(this prints only at the end)'
    ))
    return vars(parser.parse_args())


def main(fin, fout, only_last=False, **kwargs):
    if only_last:
        select_last(fin, fout, **kwargs)
    else:
        run(fin, fout, **kwargs)


if __name__ == '__main__':
    main(sys.stdin, sys.stdout, **parse_cli())
