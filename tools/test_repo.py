"""Functional smoke test of the built Saudi Arabia repository: the things a reader does with it work. Standard library only.

    python -X utf8 scripts/saudi-arabia-law/test_repo.py --repo ../saudi-arabia-law [--record]
    python -X utf8 tools/test_repo.py                   # from inside the repository

It asserts that:
1. `git blame` on Labour Law art. 74 names its instruments (M/51 for the unchanged lines, M/46, M/134, M/44);
2. tools/salaw.py gives the text the day before and the day of each change (Basic Law art. 5, Labour Law arts. 74 and
   22), each equal to the file at that instrument's tag and before it, and refuses a day before the record;
3. `git log --follow` on Labour Law art. 74 lists its instruments in the order they took effect;
4. every tag resolves to a commit, and every commit has an ISO `In-force:` trailer;
5. no commit is authored by Lexifina except the documentation commit (the last one), and every law author uses an
   `.invalid` address;
6. every git or tool command in the README's table runs and prints something.
With --record the result is written to verification.json next to this script (for REPRODUCE.md).
"""
import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAW = re.compile(r'^Royal (Decree|Order) [AM]/\d+ of \d+/\d+/\d+ H$')
F15 = 'labour-law/article-074.md'


def default_repo() -> Path:
    if (HERE.parent / '.git').exists():
        return HERE.parent
    return HERE.parents[2] / 'saudi-arabia-law'


class Smoke:
    def __init__(self, repo: Path):
        self.repo = repo
        self.results = []

    def git(self, *args):
        out = subprocess.run(['git', *args], cwd=self.repo, capture_output=True, text=True, encoding='utf-8')
        if out.returncode:
            raise AssertionError(f'git {" ".join(args)}: {out.stderr.strip()}')
        return out.stdout

    def tool(self, *args, ok=True):
        out = subprocess.run([sys.executable, '-X', 'utf8', 'tools/salaw.py', *args], cwd=self.repo,
                             capture_output=True, text=True, encoding='utf-8')
        if ok and out.returncode:
            raise AssertionError(f'salaw {" ".join(args)}: {out.stderr.strip()}')
        return out.stdout if ok else out

    def check(self, name, fn):
        try:
            detail = fn() or ''
            self.results.append((name, True, detail))
            print(f'PASS {name}: {detail}')
        except AssertionError as exc:
            self.results.append((name, False, str(exc)))
            print(f'FAIL {name}: {exc}')

    def blame(self):
        out = self.git('blame', '--line-porcelain', 'main', '--', F15)
        authors = {l[7:] for l in out.splitlines() if l.startswith('author ')}
        assert all(LAW.match(a) for a in authors), f'unexpected authors {authors}'
        want = {'Royal Decree M/51 of 23/8/1426 H', 'Royal Decree M/46 of 5/6/1436 H', 'Royal Decree M/134 of 27/11/1440 H',
                'Royal Decree M/44 of 8/2/1446 H'}
        assert want <= authors, f'authors {authors}'
        return f'{F15} on main by {", ".join(sorted(authors))}'

    def on_date(self):
        done = []
        for tag, law, art, path, before, after in [
                ('basic-law/a-256-1438', 'basic-law-of-governance', '5', 'basic-law-of-governance/article-005.md',
                 '2017-06-20', '2017-06-21'),
                ('basic-law/a-135-1427', 'basic-law-of-governance', '5', 'basic-law-of-governance/article-005.md',
                 '2006-10-18', '2006-10-19'),
                ('labour-law/m-46-1436', 'labour-law', '74', F15, '2015-03-24', '2015-03-25'),
                ('labour-law/m-134-1440', 'labour-law', '74', F15, '2019-07-29', '2019-07-30'),
                ('labour-law/m-44-1446', 'labour-law', '22', 'labour-law/article-022.md', '2025-02-18', '2025-02-19')]:
            a, b = self.tool(before, law, art), self.tool(after, law, art)
            assert a and b and a != b, f'no change between {before} and {after}'
            assert b == self.git('show', f'{tag}:{path}'), f'{after} is not the file at {tag}'
            assert a == self.git('show', f'{tag}~1:{path}'), f'{before} is not the file before {tag}'
            done.append(f'{law} {art}: {before} != {after}')
        whole = self.tool('2000-01-01', 'basic-law-of-governance')
        assert 'بسم الله الرحمن الرحيم' in whole and '# المادة الثالثة والثمانون' in whole, 'whole text on 2000-01-01'
        early = self.tool('2006-04-25', 'labour-law', ok=False)
        assert early.returncode != 0 and 'not in the record' in early.stderr, 'a day before the record must fail'
        gone = self.tool('2014-01-01', 'labour-law', '210', ok=False)
        assert gone.returncode != 0, 'a repealed article must not print'
        return '; '.join(done) + '; whole Basic Law in reading order; 2006-04-25 refused; art. 210 gone in 2014'

    def follow(self):
        out = self.git('log', '--follow', '--format=%an%x09%(trailers:key=In-force,valueonly,separator=)', 'main', '--',
                       F15)
        rows = [l.split('	') for l in out.splitlines() if l]
        days = [d.strip() for _, d in rows]
        assert len(rows) >= 4, f'{len(rows)} commits'
        assert days == sorted(days, reverse=True), f'not in date order {days}'
        assert all(LAW.match(a) for a, _ in rows), f'authors {[a for a, _ in rows]}'
        return f'{F15}: ' + ', '.join(f'{a} {d}' for a, d in rows)

    def tags_and_trailers(self):
        tags = self.git('tag').split()
        assert len(tags) == 11, f'tags {tags}'
        for t in tags:
            self.git('rev-parse', '--verify', '-q', f'{t}^{{commit}}')
        rows = self.git('log', '--format=%H%x09%an%x09%(trailers:key=In-force,valueonly,separator=)', 'main').splitlines()
        bad = [r for r in rows if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', r.split('\t')[2].strip())]
        assert not bad, f'missing or malformed In-force {bad[:2]}'
        parsed = subprocess.run(['git', 'log', '--format=%(trailers:only,unfold)%x00', 'main'], cwd=self.repo,
                                capture_output=True, text=True, encoding='utf-8').stdout.split('\x00')
        assert all('In-force:' in p for p in parsed if p.strip()), 'a trailer block does not parse'
        return f'{len(tags)} tags resolve; {len(rows)} commits carry In-force; trailer blocks parse'

    def lexifina(self):
        rows = self.git('log', '--format=%H%x09%an%x09%ae%x09%cn', 'main').splitlines()
        by_lex = [r for r in rows if r.split('\t')[1] == 'Lexifina']
        assert len(by_lex) == 1 and by_lex[0] == rows[0], f'{len(by_lex)} commits by Lexifina'
        assert all(r.split('\t')[3] == 'Lexifina' for r in rows), 'a committer other than Lexifina'
        assert all(r.split('\t')[2].endswith('.invalid') for r in rows[1:]), 'a law author without .invalid'
        return f'only the documentation commit {rows[0][:10]} is by Lexifina; {len(rows) - 1} law commits'

    def readme(self):
        text = (self.repo / 'README.md').read_text(encoding='utf-8')
        table = text[text.index('## The questions'):text.index('PowerShell splits')]
        cmds = [c for c in re.findall(r'`([^`]+)`', table) if c.startswith(('git ', 'python '))]
        assert len(cmds) >= 8, f'only {len(cmds)} commands found'
        for c in cmds:
            args = shlex.split(c)
            if args[0] == 'python':
                args[0:1] = [sys.executable, '-X', 'utf8']
            out = subprocess.run(args, cwd=self.repo, capture_output=True, text=True, encoding='utf-8')
            assert out.returncode == 0, f'{c}: exit {out.returncode} {out.stderr.strip()[:200]}'
            assert out.stdout.strip(), f'{c}: printed nothing'
        return f'{len(cmds)} README commands ran and printed output'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=None)
    ap.add_argument('--record', action='store_true')
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    s = Smoke(Path(args.repo) if args.repo else default_repo())
    s.check('blame names the acts', s.blame)
    s.check('text before and after each act', s.on_date)
    s.check('log --follow in date order', s.follow)
    s.check('tags resolve, In-force on every commit', s.tags_and_trailers)
    s.check('only the documentation commit is by Lexifina', s.lexifina)
    s.check('README commands run', s.readme)
    ok = all(r[1] for r in s.results)
    print(f'{sum(r[1] for r in s.results)}/{len(s.results)} passed')
    if args.record:
        p = HERE / 'verification.json'
        rec = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
        rec['smoke'] = {'passed': sum(r[1] for r in s.results), 'total': len(s.results),
                        'results': [{'test': n, 'ok': o, 'detail': d} for n, o, d in s.results]}
        p.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8',
                     newline='\n')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
