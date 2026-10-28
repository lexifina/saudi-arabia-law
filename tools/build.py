"""Builds the Saudi Arabia git-for-law repository: the Basic Law of Governance and the Labour Law, from laws.boe.gov.sa.

    python -X utf8 build.py --repo DIR [--offline] [--docs-date YYYY-MM-DD] [--wip] [--verify-rebuild]

Source: the Bureau of Experts at the Council of Ministers (هيئة الخبراء بمجلس الوزراء), laws.boe.gov.sa, read through
pinned Wayback captures (source.py). Each law page prints the ORIGINAL enacted text, and for each changed article one
editorial note per amendment ("تعديلات المادة") naming the amending royal decree or order, its Hijri date and the new
words in quotes. Articles added later appear in the text as such a note. There is no past-version list and no
consolidated text, so every later version is a REPLAY of the notes (replay.py), one commit per amending instrument.

Commits: one per instrument, authored by it (`<id>@boe.invalid`), dated noon Asia/Riyadh (UTC+3, no summer time) on
its in-force day; Hijri dates are kept in trailers. History is written with one `git fast-import` stream.
"""
import argparse
import datetime as dt
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import parse as P  # noqa: E402
import replay as R  # noqa: E402
import source as S  # noqa: E402

COMMITTER = ('Lexifina', 'saudi-arabia-law@lexifina.com')
PUBLISHER = ('Bureau of Experts at the Council of Ministers', 'laws@boe.invalid')
ROOT_SUBJECT_PLACEHOLDER = 'sources, before any law'


# ---- dates -----------------------------------------------------------------------------------------------------------
def stamp(day: str, sec: int = 0) -> str:
    """Noon in Riyadh. Saudi Arabia keeps UTC+3 all year (no summer time in the record, 1992 onward)."""
    d = dt.date.fromisoformat(day)
    if d.year < 1970:
        return f'1970-01-01T12:00:{sec:02d}+0300'
    return f'{d.isoformat()}T12:00:{sec:02d}+0300'


def git_date(day: str) -> str:
    d = dt.datetime.fromisoformat(stamp(day)[:19] + '+03:00')
    return f'{int(d.timestamp())} +0300'


# ---- git -------------------------------------------------------------------------------------------------------------
def git(repo, *args, inp=None):
    e = dict(os.environ)
    for k in ('GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL', 'GIT_AUTHOR_DATE', 'GIT_COMMITTER_NAME', 'GIT_COMMITTER_EMAIL',
              'GIT_COMMITTER_DATE'):
        e.pop(k, None)
    r = subprocess.run(['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false', *args], cwd=repo, env=e,
                       input=inp, capture_output=True)
    if r.returncode:
        raise SystemExit(f'git {" ".join(args)}: {r.stderr.decode("utf-8", "replace")}')
    return r.stdout.decode('utf-8')


def rmtree(p):
    def fix(func, path, exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    shutil.rmtree(p, onexc=fix)


def prepare(repo: Path):
    """Refuse a non-empty target that is not an earlier build of this repo (or the placeholder clone). Keep origin."""
    origin = ''
    if repo.exists() and any(repo.iterdir()):
        if not (repo / '.git').exists():
            raise SystemExit(f'{repo} is not empty and not a git repository')
        log = subprocess.run(['git', 'log', '--all', '--format=%ce|%s', '-500'], cwd=repo, capture_output=True,
                             text=True, encoding='utf-8').stdout.splitlines()
        ours = all(l.split('|')[0] == COMMITTER[1] or l.endswith(ROOT_SUBJECT_PLACEHOLDER) for l in log if l)
        if not ours:
            raise SystemExit(f'{repo} holds commits that are not from this builder; refusing to overwrite')
        origin = subprocess.run(['git', 'remote', 'get-url', 'origin'], cwd=repo, capture_output=True,
                                text=True).stdout.strip()
        for p in repo.iterdir():
            rmtree(p) if p.is_dir() else p.unlink()
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, 'init', '-q', '-b', 'main')
    if origin:
        git(repo, 'remote', 'add', 'origin', origin)


class FastImport:
    """One `git fast-import` stream; each commit carries the whole tree (deleteall + every file)."""

    def __init__(self, repo: Path):
        self.p = subprocess.Popen(['git', 'fast-import', '--quiet', '--done'], cwd=repo, stdin=subprocess.PIPE)
        self.mark = 0
        self.tags = []

    def w(self, b: bytes):
        self.p.stdin.write(b)

    def data(self, s: str):
        b = s.encode('utf-8')
        self.w(b'data %d\n' % len(b) + b + b'\n')

    def commit(self, author, email, day, msg, files: dict, tag: str | None = None, committer=COMMITTER):
        self.mark += 1
        when = git_date(day)
        self.w(b'commit refs/heads/main\n')
        self.w(b'mark :%d\n' % self.mark)
        self.w(f'author {author} <{email}> {when}\n'.encode('utf-8'))
        self.w(f'committer {committer[0]} <{committer[1]}> {when}\n'.encode('utf-8'))
        self.data(msg)
        if self.mark > 1:
            self.w(b'from :%d\n' % (self.mark - 1))
        self.w(b'deleteall\n')
        for path in sorted(files):
            self.w(f'M 100644 inline {path}\n'.encode('utf-8'))
            self.data(files[path])
        if tag:
            self.tags.append((tag, self.mark))

    def finish(self):
        for t, m in self.tags:
            self.w(f'reset refs/tags/{t}\nfrom :{m}\n'.encode('utf-8'))
        self.w(b'done\n')
        self.p.stdin.close()
        if self.p.wait():
            raise SystemExit('git fast-import failed')


# ---- build -----------------------------------------------------------------------------------------------------------
def build(repo: Path, offline: bool, docs_date: str | None, wip: bool = False):
    events = R.events(offline)          # every version of both laws, in in-force order
    prepare(repo)
    fi = FastImport(repo)
    state = {}                          # path -> text, both laws
    for ev in events:
        for path in [p for p in state if p.startswith(ev['folder'] + '/')]:
            del state[path]
        state.update(ev['files'])
        fi.commit(ev['author'], ev['email'], ev['in_force'], ev['message'], dict(state), ev['tag'])
    day = docs_date or S.RETRIEVED
    import reproduce
    docs = reproduce.docs(events, day, HERE, wip)
    state.update(docs)
    msg = ('Documentation, tools and REPRODUCE.md\n\nNo law text changes: README, LICENSE, REPRODUCE.md, corpus.json, '
           'instruments.csv and the tools.\n\nKind: documentation\nIn-force: ' + day + '\n')
    fi.commit(COMMITTER[0], COMMITTER[1], day, msg, dict(state))
    fi.finish()
    git(repo, 'reset', '-q', '--hard', 'main')
    return git(repo, 'rev-parse', 'HEAD').strip(), events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--offline', action='store_true')
    ap.add_argument('--docs-date', default=None, help='documentation commit day (default: the data retrieval day)')
    ap.add_argument('--wip', action='store_true', help='README says "building" (for the wip branch only)')
    ap.add_argument('--verify-rebuild', action='store_true',
                    help='build again in a temporary folder and compare HEAD with --repo (does not touch --repo)')
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    if args.verify_rebuild:
        want = git(Path(args.repo), 'rev-parse', 'HEAD').strip()
        with tempfile.TemporaryDirectory() as td:
            got, _ = build(Path(td) / 'r', True, args.docs_date, args.wip)
        print('rebuild', got, 'repo', want, 'IDENTICAL' if got == want else 'DIFFERENT')
        raise SystemExit(0 if got == want else 1)
    head, events = build(Path(args.repo), args.offline, args.docs_date, args.wip)
    for ev in events:
        print(ev['tag'], ev['in_force'], ev['folder'], len(ev['files']), 'files', len(ev['applied']), 'ops',
              len(ev['not_applied']), 'not applied')
    print('main', head)


if __name__ == '__main__':
    main()
