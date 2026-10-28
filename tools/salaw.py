"""Prints a Saudi law (basic-law-of-governance or labour-law), or one article of it, as it stood on a given day, from this repository.

    python tools/salaw.py 2016-01-01 labour-law 74        # Labour Law art. 74 on 1 January 2016
    python tools/salaw.py 2016-01-01 basic-law-of-governance   # the whole Basic Law on that day; 11-bis = art. 11 مكرر

Each commit carries the day its text took effect in an `In-force:` trailer. The text in force on a day is the last commit
on or before it, read by that trailer (not by commit time, so the reader's time zone does not matter). Article numbers
are those of the text in force that day (Royal Decree M/46 of 1436 H renumbered Labour Law arts. 240 and 242 as 231
and 232). Standard library only.
"""
import datetime as dt
import re
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(['git', *args], capture_output=True, text=True, encoding='utf-8', check=True).stdout


def commit_on(day: str, folder: str) -> str:
    out = git('log', '--no-merges', '--format=%H%x09%(trailers:key=In-force,valueonly,separator=)', 'main', '--', folder)
    for line in out.splitlines():
        h, _, d = line.partition('\t')
        if d.strip() and d.strip() <= day:
            return h
    return ''


def fname(key: str) -> str:
    n, _, sub = key.partition('-')
    if not n.isdigit():
        return key if key.endswith('.md') else key + '.md'
    return f'article-{int(n):03d}' + (f'-{sub}' if sub else '') + '.md'


def akey(name: str) -> tuple:
    m = re.fullmatch(r'article-(\d+)(-bis)?\.md', name)
    return (int(m.group(1)), 1 if m.group(2) else 0) if m else (10 ** 6, 0)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    day, folder = sys.argv[1], sys.argv[2].rstrip('/')
    dt.date.fromisoformat(day)
    c = commit_on(day, folder)
    if not c:
        first = git('log', '--reverse', '--format=%(trailers:key=In-force,valueonly,separator=)', 'main', '--',
                    folder).split()[:1]
        sys.exit(f'{folder} is not in the record on {day} (its record starts on {first[0] if first else "?"}).')
    if len(sys.argv) > 3:
        name = fname(sys.argv[3])
        try:
            sys.stdout.write(git('show', f'{c}:{folder}/{name}'))
        except subprocess.CalledProcessError:
            sys.exit(f'{folder}/{name} was not in the text on {day}.')
        return
    names = [n.split('/', 1)[1] for n in git('ls-tree', '-r', '--name-only', c, folder + '/').split('\n') if n]
    heads = {}
    for line in git('show', f'{c}:{folder}/structure.md').splitlines():
        m = re.fullmatch(r'(.*) \[article ([0-9]+(?:-bis)?)\]', line)
        if m:
            heads.setdefault(fname(m.group(2)), []).append(m.group(1))
    sys.stdout.write(git('show', f'{c}:{folder}/preamble.md') + '\n')
    for n in sorted((n for n in names if n.startswith('article-')), key=akey):
        for h in heads.get(n, []):
            sys.stdout.write(h + '\n')
        if n in heads:
            sys.stdout.write('\n')
        sys.stdout.write(git('show', f'{c}:{folder}/{n}') + '\n')


if __name__ == '__main__':
    main()
