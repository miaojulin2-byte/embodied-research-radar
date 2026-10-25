#!/usr/bin/env python3
"""Incremental research index. No credentials or unreviewed LLM claims in public data."""
import argparse
import calendar
import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_data import write_site_data
from evidence import initialize, enrich_documents, extract_document, refresh_coverage, VERSION, replay_cached

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'site/data'
UTC = timezone.utc
NS = {'a': 'http://www.w3.org/2005/Atom', 'o': 'http://a9.com/-/spec/opensearch/1.1/'}

def load(name):
    return yaml.safe_load((ROOT / 'config' / name).read_text())

def now():
    return datetime.now(UTC)

def error_label(e):
    if isinstance(e, urllib.error.HTTPError):
        return 'HTTP ' + str(e.code)
    if isinstance(e, urllib.error.URLError):
        return 'URLError: ' + type(e.reason).__name__
    return type(e).__name__

def iso():
    return now().isoformat(timespec='seconds')

def parse_date(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=UTC)

def arxiv_id(value):
    match = re.search(r'(?:arxiv:|arxiv.org/(?:abs|pdf)/)?((?:\d{4}\.\d{4,5}|[a-z-]+/\d{7}))(?:v\d+)?', value, re.I)
    return match.group(1) if match else None

def identity(item):
    aid = arxiv_id(item.get('id', '')) or arxiv_id(item.get('url', ''))
    if aid:
        return 'arxiv:' + aid.lower()
    return item.get('id') or 'url:' + hashlib.sha256(item['url'].encode()).hexdigest()[:20]

def merge_items(old, incoming):
    """Merge only explicit aliases, exact canonical URLs, or arXiv IDs; no fuzzy titles."""
    result = {identity(x): copy.deepcopy(x) for x in old}
    for raw in incoming:
        x = copy.deepcopy(raw)
        key = identity(x)
        aliases = set(x.get('aliases', []) + [x.get('url', '')]) - {''}
        for k, v in list(result.items()):
            if k != key and (k in aliases or v.get('url') in aliases or x.get('url') in v.get('aliases', [])):
                result[key] = {**v, **result.get(key, {})}
                result[key]['sources'] = sorted(set(v.get('sources', []) + [v['url']] + result[key].get('sources', [])))
                del result[k]
        prev = result.get(key, {})
        # Atom metadata cannot overwrite human-reviewed fields.
        if prev.get('verified') and not x.get('verified'):
            x = {**x, **{k: v for k, v in prev.items() if k not in ['abstract', 'updated', 'authors']}}
        combined = {**prev, **x, 'id': key}
        if not x.get('verified'):
            for name, record in prev.get('field_evidence', {}).items():
                if record.get('status') in {'supported', 'derived', 'llm_grounded'} and name not in {'routes'}:
                    combined[name] = record['value']
            combined['evidence'] = sorted(set(prev.get('evidence', []) + x.get('evidence', [])))
        combined['sources'] = sorted(set(prev.get('sources', []) + x.get('sources', []) + [x['url']]))
        combined['first_seen'] = prev.get('first_seen', iso())
        result[key] = combined
    return list(result.values())

class Client:
    def __init__(self):
        self.last = {}
    def get(self, url, headers=None, body=None, delay=0, host=None, max_bytes=20000000, method=None, attempts=3, timeout=45):
        host = host or urllib.parse.urlparse(url).netloc
        for attempt in range(attempts):
            wait = delay - (time.monotonic() - self.last.get(host, 0))
            if wait > 0:
                time.sleep(wait)
            req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                method=method, headers={'User-Agent': 'EmbodiedResearchRadar/1.0 (research metadata index)', **(headers or {})})
            try:
                self.last[host] = time.monotonic()
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    data = response.read(max_bytes + 1)
                    if len(data) > max_bytes:
                        raise ValueError('Source exceeds configured size limit')
                    return data
            except urllib.error.HTTPError as e:
                if e.code not in [429, 500, 502, 503, 504] or attempt == attempts - 1:
                    raise
                try:
                    retry = float(e.headers.get('Retry-After', 2 ** (attempt + 2)))
                except ValueError:
                    retry = 10
                time.sleep(min(60, retry))
            except (urllib.error.URLError, TimeoutError):
                if attempt == attempts - 1:
                    raise
                time.sleep(2 ** (attempt + 1))
    def head(self, url, **kwargs):
        return self.get(url, method='HEAD', **kwargs)
    def json(self, *args, **kwargs):
        return json.loads(self.get(*args, **kwargs))


def parse_atom(raw):
    root = ET.fromstring(raw)
    entries = []
    for e in root.findall('a:entry', NS):
        url = e.findtext('a:id', '', NS)
        aid = arxiv_id(url)
        if not aid:
            raise ValueError('arXiv returned an error entry')
        entries.append({'id': 'arxiv:' + aid, 'title': ' '.join(e.findtext('a:title', '', NS).split()),
            'url': 'https://arxiv.org/abs/' + aid, 'arxiv_version_url': url, 'published': e.findtext('a:published', '', NS)[:10],
            'updated': e.findtext('a:updated', '', NS),
            'abstract': ' '.join(e.findtext('a:summary', '', NS).split()),
            'authors': [x.findtext('a:name', '', NS) for x in e.findall('a:author', NS)],
            'author_affiliations': [a.text for a in e.findall('.//{http://arxiv.org/schemas/atom}affiliation') if a.text],
            'kind': '论文', 'evidence': ['paper'], 'verified': False,
            'institution': '待核验', 'region': '待核验', 'hardware': '待核验'})
    return entries, int(root.findtext('o:totalResults', '0', NS))


def fetch_arxiv(client, cfg, since):
    cats = ' OR '.join('cat:' + c for c in cfg['categories'])
    terms = ' OR '.join('all:"' + k + '"' for k in cfg['keywords'])
    # lastUpdatedDate catches revisions; overlap also covers late indexing.
    query = f'({cats}) AND ({terms}) AND lastUpdatedDate:[{since:%Y%m%d}0000 TO {now():%Y%m%d}2359]'
    items = []
    total = 0
    for page in range(cfg['max_pages']):
        start = page * cfg['page_size']
        params = urllib.parse.urlencode({'search_query': query, 'start': start, 'max_results': cfg['page_size'],
            'sortBy': 'lastUpdatedDate', 'sortOrder': 'descending'})
        try:
            raw = client.get('https://export.arxiv.org/api/query?' + params, delay=max(3.1, cfg['delay_seconds']), host='arxiv.org')
            batch, total = parse_atom(raw)
        except Exception as e:
            return items, {'count': len(items), 'total': total, 'complete': False, 'since': since.isoformat(), 'error': error_label(e)}
        items.extend(batch)
        if start + len(batch) >= total:
            return items, {'count': len(items), 'total': total, 'complete': True, 'since': since.isoformat()}
        if not batch:
            break
    return items, {'count': len(items), 'total': total, 'complete': False, 'since': since.isoformat(),
        'error': '分页上限；下次继续保留原水位，请提高 max_pages 或缩小首次窗口'}



def rss_items(raw, keywords):
    root = ET.fromstring(raw)
    result = []
    for e in list(root.findall('.//item')) + list(root.findall('a:entry', NS)):
        title = e.findtext('title') or e.findtext('a:title', '', NS)
        description = e.findtext('description') or e.findtext('a:summary', '', NS)
        if keywords and not any(k.lower() in (title + description).lower() for k in keywords):
            continue
        url = e.findtext('link')
        if not url:
            link = e.find('a:link', NS)
            url = link.get('href') if link is not None else None
        stamp = e.findtext('pubDate') or e.findtext('a:published', '', NS)
        date = None
        if stamp:
            try:
                date = parse_date(stamp).date().isoformat()
            except ValueError:
                from email.utils import parsedate_to_datetime
                date = parsedate_to_datetime(stamp).date().isoformat()
        if url:
            result.append({'title': title, 'url': url, 'published': date, 'kind': '官方博客线索', 'abstract': description[:8000],
                'evidence': [], 'verified': False, 'institution': '待核验', 'region': '待核验'})
    return result


def enrich(client, cfg, items, metrics, status):
    token = os.getenv('GITHUB_TOKEN')
    headers = {'Authorization': 'Bearer ' + token} if token else {}
    for repo in cfg['github']['repositories']:
        try:
            info = client.json('https://api.github.com/repos/' + repo, headers=headers, delay=1)
            releases = client.json('https://api.github.com/repos/' + repo + '/releases?per_page=5', headers=headers, delay=1)
            metrics['repositories'][repo] = {'stars': info['stargazers_count'], 'observed_at': iso(),
                'license': (info.get('license') or {}).get('spdx_id'), 'url': info['html_url'],
                'releases': [{'name': r['tag_name'], 'published': r['published_at'], 'url': r['html_url']} for r in releases]}
            status.append({'source': 'github:' + repo, 'ok': True})
        except Exception as e:
            status.append({'source': 'github:' + repo, 'ok': False, 'error': error_label(e)})
    for author in cfg['huggingface']['authors']:
        try:
            models = client.json('https://huggingface.co/api/models?' + urllib.parse.urlencode({'author': author, 'sort': 'lastModified', 'direction': -1, 'limit': cfg['huggingface']['limit'], 'full': 'true'}), delay=1)
            for m in models:
                mid = m['id']
                metrics['models'][mid] = {'url': 'https://huggingface.co/' + mid, 'created': m.get('createdAt'), 'updated': m.get('lastModified'), 'observed_at': iso(), 'gated': m.get('gated'), 'license': (m.get('cardData') or {}).get('license'), 'weight_files_detected': any(re.search(r'\.(safetensors|bin|pt|pth)$', f['rfilename']) for f in m.get('siblings', []))}
            status.append({'source': 'huggingface:' + author, 'ok': True, 'count': len(models), 'limited': len(models) == cfg['huggingface']['limit']})
        except Exception as e:
            status.append({'source': 'huggingface:' + author, 'ok': False, 'error': error_label(e)})
    if cfg['semantic_scholar']['enabled']:
        candidates = sorted([x for x in items if x['id'].startswith('arxiv:')], key=lambda x: metrics['papers'].get(x['id'], {}).get('observed_at', ''))
        for x in candidates[:cfg['semantic_scholar']['max_per_run']]:
            try:
                url = 'https://api.semanticscholar.org/graph/v1/paper/ARXIV:' + x['id'][6:] + '?fields=title,citationCount,authors.name,authors.affiliations'
                s2 = client.json(url, headers={'x-api-key': os.environ['S2_API_KEY']} if os.getenv('S2_API_KEY') else {}, delay=1.1)
                metrics['papers'][x['id']] = {'citations': s2['citationCount'], 'observed_at': iso(), 'author_profiles': s2.get('authors', [])}
                status.append({'source': 's2:' + x['id'], 'ok': True})
            except Exception as e:
                status.append({'source': 's2:' + x['id'], 'ok': False, 'error': error_label(e)})
                if isinstance(e, urllib.error.HTTPError) and e.code == 429:
                    status[-1]['remaining_skipped'] = True
                    break  # shared public quota: preserve prior metrics and retry next day


def week_growth(history, current, group, key, field):
    cutoff = now() - timedelta(days=7)
    eligible = [h for h in history if parse_date(h['at']) <= cutoff and key in h.get(group, {})]
    latest = current.get(group, {}).get(key, {})
    if not eligible or field not in latest or now() - parse_date(latest['observed_at']) > timedelta(days=2):
        return None
    baseline = eligible[-1]
    if cutoff - parse_date(baseline['at']) > timedelta(days=2):
        return None
    before = baseline[group][key]
    if parse_date(baseline['at']) - parse_date(before['observed_at']) > timedelta(days=2):
        return None
    return latest[field] - before[field] if field in before else None


def export(items):
    out = io.StringIO()
    fields = ['id', 'title', 'institution', 'region', 'published', 'primary_route', 'routes', 'confidence', 'classification_method', 'contribution', 'summary_zh', 'url', 'review', 'review_reasons', 'missing_fields', 'field_evidence']
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows([{**x, 'routes': ';'.join(x.get('routes', [])), 'review_reasons': ';'.join(x.get('review_reasons', [])), 'missing_fields': ';'.join(x.get('missing_fields', [])), 'field_evidence': json.dumps(x.get('field_evidence', {}), ensure_ascii=False)} for x in items])
    (DATA / 'papers.csv').write_text('\ufeff' + out.getvalue())
    rows = ['| 名称 | 日期 | 路线 | 机构 | 状态 |', '|---|---|---|---|---|']
    for x in items:
        title = x['title'].replace('|', '\\|').replace('\n', ' ')
        rows.append(f"| [{title}]({x['url']}) | {x.get('published') or '待核验'} | {', '.join(x.get('routes', []))} | {x.get('institution', '待核验')} | {'分类需复核' if x.get('review') else '人工核验' if x.get('verified') else '自动整理'} |")
    (DATA / 'papers.md').write_text('\n'.join(rows) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true', help='merge reviewed YAML and render without network; do not advance cursor')
    parser.add_argument('--enrich-only', action='store_true', help='process existing backlog without refetching all metadata')
    parser.add_argument('--limit', type=int, help='maximum paper evidence jobs this run')
    parser.add_argument('--max-seconds', type=int, help='stop the evidence queue gracefully after this time budget')
    parser.add_argument('--ids', nargs='*', help='explicit arxiv IDs for source verification')
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / 'dashboard.json'
    previous = json.loads(path.read_text()) if path.exists() else {}
    cfg, routes = load('sources.yaml'), load('routes.yaml')
    old = previous.get('items', [])
    manual = load('manual.yaml')['items']
    milestones = load('milestones.yaml')['items']
    for x in manual + milestones:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', x.get('published', '')):
            raise ValueError('Reviewed records require YYYY-MM-DD')
        if not set(x['routes']) <= {r['id'] for r in routes} or x['primary_route'] not in x['routes']:
            raise ValueError('Invalid reviewed route')
        x.update(review=not x.get('verified', False), confidence=1 if x.get('verified') else 0, classification_method='human')
    items = merge_items(old, manual + milestones)
    status, cursor = [], previous.get('arxiv_cursor')
    metrics = copy.deepcopy(previous.get('metrics', {'repositories': {}, 'models': {}, 'papers': {}}))
    history = previous.get('history', [])
    client = Client()
    if not args.offline and not args.enrich_only:
        since = parse_date(cursor) - timedelta(days=cfg['arxiv']['overlap_days']) if cursor else now() - timedelta(days=cfg['arxiv']['initial_days'])
        try:
            fetched, info = fetch_arxiv(client, cfg['arxiv'], since)
            items = merge_items(items, fetched)
            status.append({'source': 'arxiv', 'ok': info['complete'], **info})
            if info['complete']:
                cursor = iso()
        except Exception as e:
            status.append({'source': 'arxiv', 'ok': False, 'error': error_label(e)})
        for feed in cfg['rss']:
            try:
                batch = rss_items(client.get(feed['url']), feed.get('keywords', []))
                items = merge_items(items, batch)
                status.append({'source': 'rss:' + feed['name'], 'ok': True, 'count': len(batch)})
            except Exception as e:
                status.append({'source': 'rss:' + feed['name'], 'ok': False, 'error': error_label(e)})
        enrich(client, cfg, items, metrics, status)
    # Cheap deterministic extraction runs over all candidates, with no API key required.
    for x in items:
        initialize(x, routes, cfg['llm']['review_threshold'])
        if x.get('author_affiliations'):
            extract_document(x, {'url': x['url'], 'text': x.get('abstract', ''), 'affiliations': ' '.join(x['author_affiliations'])}, load('organizations.yaml'))
    extraction_cfg = {**cfg.get('extraction', {}), 'progress': True, 'max_seconds': args.max_seconds if args.max_seconds is not None else 1200, 'checkpoint_every': 5, 'routes': routes, 'llm_max_per_run': cfg['llm']['max_per_run'], 'review_threshold': cfg['llm']['review_threshold'], 'use_llm': bool(cfg['llm']['enabled']) and cfg.get('extraction', {}).get('use_llm', True), 'max_per_run': args.limit if args.limit is not None else cfg.get('extraction', {}).get('max_per_run', 40)}
    def checkpoint(reports):
        snapshot = {**previous, 'generated_at': iso(), 'mode': 'backfill', 'items': items,
            'last_network_attempt': iso(), 'arxiv_cursor': cursor, 'routes': routes,
            'institutions': load('institutions.yaml'), 'metrics': metrics, 'history': history,
            'editorial': load('editorial.yaml'), 'milestones': [identity(x) for x in milestones],
            'sources': [s for s in previous.get('sources', []) if not s['source'].startswith('evidence:')] + status + reports,
            'extraction_pipeline': {'version': VERSION, 'enabled': True, 'llm_configured': bool(os.getenv('LLM_API_KEY')),
                'max_per_run': extraction_cfg['max_per_run'], 'last_batch_processed': len(reports),
                'pending_papers': sum(x['id'].startswith('arxiv:') and (x.get('extraction', {}).get('status') != 'complete' or x.get('extraction', {}).get('version') != VERSION) for x in items)}}
        temporary = path.with_suffix('.checkpoint')
        temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(path)
    if args.offline:
        replay_cached(items, load('organizations.yaml'), ROOT / '.cache/evidence')
    if not args.offline and extraction_cfg.get('enabled', True):
        ids = {'arxiv:' + (arxiv_id(v) or v.removeprefix('arxiv:')) for v in args.ids} if args.ids else None
        status.extend(enrich_documents(items, client, extraction_cfg, load('organizations.yaml'), ROOT / '.cache/evidence', ids, checkpoint=checkpoint))
    for x in items:
        refresh_coverage(x)
    oldmap = {x['id']: x for x in old}
    for x in items:
        x['change'] = 'new' if x['id'] not in oldmap else 'changed' if any(x.get(k) != oldmap[x['id']].get(k) for k in ['updated', 'evidence', 'contribution', 'routes']) else None
        x['weekly_citations'] = week_growth(history, metrics, 'papers', x['id'], 'citations')
        x['weekly_stars'] = week_growth(history, metrics, 'repositories', x.get('github', ''), 'stars')
        # Only rank when both signals exist; formula is explicit and optional.
        a, b = x['weekly_citations'], x['weekly_stars']
        x['weekly_attention'] = round(max(0, a) + max(0, b) / 100, 3) if a is not None and b is not None else None
    if not args.offline:
        today = now().date().isoformat()
        history = [h for h in history if h['at'][:10] != today]
        history.append({'at': iso(), 'repositories': metrics['repositories'], 'papers': metrics['papers']})
        history = history[-200:]
    output = {'generated_at': iso(), 'last_network_attempt': previous.get('last_network_attempt') if args.offline else iso(),
        'mode': 'offline' if args.offline else 'enrichment' if args.enrich_only else 'live', 'arxiv_cursor': cursor,
        'extraction_pipeline': {'llm_configured': bool(os.getenv('LLM_API_KEY')), 'version': VERSION, 'enabled': extraction_cfg.get('enabled', True), 'max_per_run': extraction_cfg['max_per_run'], 'last_batch_processed': sum(s['source'].startswith('evidence:') for s in status), 'pending_papers': sum(x['id'].startswith('arxiv:') and (x.get('extraction', {}).get('status') != 'complete' or x.get('extraction', {}).get('version') != VERSION) for x in items)},
        'window_days': cfg['arxiv']['initial_days'], 'routes': routes, 'institutions': load('institutions.yaml'),
        'items': sorted(items, key=lambda x: x.get('published') or '', reverse=True),
        'editorial': load('editorial.yaml'),
        'milestones': [identity(x) for x in milestones], 'sources': previous.get('sources', []) if args.offline else [p for p in previous.get('sources', []) if not p['source'].startswith('evidence:')] + status if args.enrich_only else status,
        'metrics': metrics, 'history': history}
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)
    export(output['items'])
    write_site_data(output, DATA)
    failures = [s['source'] for s in status if not s['ok']]
    print(json.dumps({'items': len(items), 'mode': output['mode'], 'failures': failures}, ensure_ascii=False))
    if not args.offline and status and not any(s['ok'] for s in status):
        sys.exit(1)

if __name__ == '__main__':
    main()
