"""Cached fetches of laws.boe.gov.sa pages through the Internet Archive (Wayback Machine).

laws.boe.gov.sa (Bureau of Experts at the Council of Ministers) does not answer from the build machine's network (TCP
connect to 66.9.136.215:443 and :80 times out), so every page is read from a pinned Wayback capture: the URL
`http://web.archive.org/web/<timestamp>id_/<original>` returns the bytes the portal served on that day, unmodified.
Each capture timestamp is pinned in SOURCES so a rebuild reads the same bytes.

Cache: ./cache/<sha1(url)>.gz (gzip of the body as served, after gzip transfer decoding). Self-gitignored.
robots.txt of laws.boe.gov.sa (Wayback capture 20251020104010): `User-agent: *`, `Crawl-delay: 10`, Disallow
/Identity/, /admin/, /search/ and a few Drupal paths. No AI-agent rules. The law pages (/BoeLaws/Laws/LawDetails/) are
allowed. We send at most one request at a time and wait 10 s between live requests to archive.org.
"""
import gzip
import hashlib
import json
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / 'cache'
UA = 'LexifinaLawBot/1.0 (+https://lexifina.com; git-for-law research)'
RETRIEVED = '2026-10-28'   # the day these captures were downloaded (dates the documentation commit)

SOURCES = {
    'basic-law': ('20260114204621',
                  'https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/16b97fcb-4833-4f66-8531-a9a700f161b6/1'),
    'labour-law': ('20260128140901',
                   'https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/08381293-6388-48e2-8ad2-a9a700f2aa94/1'),
    'robots': ('20251020104010', 'https://laws.boe.gov.sa/robots.txt'),
    'terms': ('20261022175531', 'https://www.boe.gov.sa/ar/Pages/TermsOfUse.aspx'),
}


def wayback(key: str) -> str:
    ts, url = SOURCES[key]
    return f'http://web.archive.org/web/{ts}id_/{url}'


def fetch(key: str, offline: bool = False) -> bytes:
    url = wayback(key)
    CACHE.mkdir(exist_ok=True)
    gi = CACHE / '.gitignore'
    if not gi.exists():
        gi.write_text('*\n', encoding='utf-8')
    f = CACHE / (hashlib.sha1(url.encode()).hexdigest() + '.gz')
    if f.exists():
        return gzip.decompress(f.read_bytes())
    if offline:
        raise SystemExit(f'not cached (offline): {url}')
    for attempt in range(6):
        r = subprocess.run(['curl', '-sS', '-f', '-m', '180', '--compressed', '-A', UA, url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            body = r.stdout
            if body[:2] == b'\x1f\x8b':          # some captures are stored gzip-encoded
                body = gzip.decompress(body)
            if b'Internet Archive: Temporarily Offline' in body[:2000]:
                time.sleep(30)
                continue
            f.write_bytes(gzip.compress(body, mtime=0))
            time.sleep(10)                      # robots.txt Crawl-delay: 10 (kept for archive.org too)
            return body
        time.sleep(30)
    raise SystemExit(f'fetch failed: {url}')


def manifest(offline: bool = True) -> dict:
    out = {}
    for k in sorted(SOURCES):
        b = fetch(k, offline)
        out[k] = {'capture': SOURCES[k][0], 'url': SOURCES[k][1], 'wayback': wayback(k),
                  'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)}
    return out


if __name__ == '__main__':
    import sys
    print(json.dumps(manifest(offline='--offline' in sys.argv), indent=1))
