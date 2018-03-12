# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import re
import io
import sys

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


def parse_round(word, stack):
    m = re.match(
        r'\(([a-zA-Z0-9._\-/]*\.(?:tex|bbl|aux|cls|cfg|def|sty|fd|clo|mkii|out|toc|ind|dfu|rtx|tdo))(.*)?$',
        word
    )
    if m:
        filename, rest = m.groups()
        if os.path.isfile(filename):
            stack.append(filename)
            debug('pushed', filename, word)
            word = rest
    new_word = ''
    for c in word:
        if c == '(':
            stack.append('(')
            debug('pushed', '(', word)
        elif c == ')':
            popped = stack.pop()
            debug('popped', popped, word)
            assert popped == '(' or len(popped) > 1
            if popped != '(':
                continue
        new_word += c
    return new_word


def parse_square(word, stack):
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


def parse_angle(word, stack):
    m = re.match(r'(<?)([a-zA-Z0-9._\-/]*)(>?)(,?\]?\)?)$', word)
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


def run(fin, fout, skip_empty=False):
    stack = ['ROOT']
    in_package = None
    lines = ['']
    for line in fin.buffer:
        operate_on = -1
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
        if line.startswith('Overfull \\hbox') or line.startswith('Underfull \\hbox'):
            next(fin.buffer)
            lines.append('\n')
            operate_on = 0
        if re.match(r'l\.\d+ |<argument> ', line):
            next_line = next(fin.buffer).decode()
            if next_line.strip() and \
                    len(next_line)-len(next_line.lstrip()) >= len(line.rstrip()):
                lines[0] = line.rstrip() + '<<<' + next_line.lstrip()
                lines.append('\n')
            else:
                lines[0] = line
                lines.append(next_line)
            words = []
        loc = (len(stack), stack[-1])
        for word, sep in words:
            if word is '' and sep is '':
                break
            word = parse_angle(word, stack)
            word = parse_square(word, stack)
            word = parse_round(word, stack)
            if len(stack) < loc[0]:
                loc = (len(stack), stack[-1])
            lines[operate_on] += word + sep
        assert loc[1] != '('
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
