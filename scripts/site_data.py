"""Small home/index payloads and lazy per-item evidence for a static Pages site."""
import calendar
import hashlib
import json
from datetime import datetime
from pathlib import Path


def write_site_data(data, directory):
    directory = Path(directory)
    detail_dir = directory / 'items'
    detail_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromisoformat(data['generated_at'])
    year, month = divmod(stamp.year * 12 + stamp.month - 1 - 6, 12)
    month += 1
    day = min(stamp.day, calendar.monthrange(year, month)[1])
    cutoff = f'{year:04}-{month:02}-{day:02}'
    items = data['items']
    stats = {'total': len(items), 'recent': sum(bool(x.get('published')) and x['published'] >= cutoff for x in items),
             'review': sum(bool(x.get('review')) for x in items)}
    metadata = {k: v for k, v in data.items() if k not in {'items', 'history'}}
    metadata['dataset_stats'] = stats
    metadata['metrics'] = {**data['metrics'], 'papers': {key: {k: v for k, v in value.items() if k != 'author_profiles'} for key, value in data['metrics']['papers'].items()}}
    picks = {p['id'] for p in data.get('editorial', {}).get('picks', [])}
    home_items, index_items = [], []
    keep = ['id', 'title', 'institution', 'region', 'published', 'updated', 'kind', 'routes', 'primary_route',
            'confidence', 'classification_method', 'summary_language', 'summary_zh', 'url', 'verified', 'review',
            'review_reasons', 'evidence', 'coverage', 'change', 'github', 'weekly_citations', 'weekly_stars', 'weekly_attention']
    for item in items:
        key = hashlib.sha256(item['id'].encode()).hexdigest()[:24]
        (detail_dir / (key + '.json')).write_text(json.dumps(item, ensure_ascii=False, separators=(',', ':')))
        thin = {k: item[k] for k in keep if k in item}
        thin['contribution'] = (item.get('summary_zh') or item.get('contribution') or '')[:240]
        thin['extraction'] = {k: v for k, v in item.get('extraction', {}).items() if k in {'status', 'document_count'}}
        thin['detail_key'] = key
        thin['resource_evidence'] = {k: {'status': v['status']} for k, v in item.get('resource_evidence', {}).items()}
        index_items.append(thin)
        if item['id'] in picks or item['url'] in picks:
            home_items.append({**item, 'detail_key': key})
    (directory / 'dashboard-home.json').write_text(json.dumps({**metadata, 'items': home_items, 'index_loaded': False}, ensure_ascii=False, separators=(',', ':')))
    (directory / 'dashboard-index.json').write_text(json.dumps({'items': index_items, 'dataset_stats': stats}, ensure_ascii=False, separators=(',', ':')))
