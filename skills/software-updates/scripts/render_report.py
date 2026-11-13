"""Render a self-contained update report from a batch JSON file."""

import argparse
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


def load_batch(path):
    batch = json.loads(path.read_text(encoding='utf-8-sig'))
    if date.fromisoformat(batch['batch']).isoformat() != batch['batch']:
        raise ValueError('batch must be an ISO date (YYYY-MM-DD)')
    if not isinstance(batch['caption'], str) or not batch['caption'].strip():
        raise ValueError('caption must describe the snapshot')
    for key in ('pending', 'current', 'paused'):
        if not isinstance(batch[key], list) or not all(isinstance(text, str) for text in batch[key]):
            raise ValueError(f'{key} must be a list of strings')
    seen = set()
    for group in batch['groups']:
        if not group['name'] or not isinstance(group['items'], list) or not group['items']:
            raise ValueError('each group needs a name and at least one item')
        for item in group['items']:
            identifier = item['id']
            if not re.fullmatch(r'[A-Z][A-Z0-9-]*[0-9]', identifier) or identifier in seen:
                raise ValueError(f'invalid or duplicate candidate ID: {identifier}')
            seen.add(identifier)
            for key in ('name', 'installed', 'target', 'scope', 'status'):
                if not isinstance(item[key], str) or not item[key].strip():
                    raise ValueError(f'{identifier}: {key} must be a nonempty string')
            for key in ('ready', 'security'):
                if not isinstance(item[key], bool):
                    raise ValueError(f'{identifier}: {key} must be boolean')
            if not isinstance(item['details'], dict) or not all(isinstance(value, str) for value in item['details'].values()):
                raise ValueError(f'{identifier}: details must map labels to strings')
            if item.get('source'):
                source = urlsplit(item['source'])
                if source.scheme != 'https' or not source.hostname:
                    raise ValueError(f'{identifier}: source must be an HTTPS URL')
    return batch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batch', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        batch = load_batch(args.batch)
        template = Path(__file__).with_name('report.html').read_text(encoding='utf-8')
        payload = json.dumps(batch, ensure_ascii=False).replace('<', r'\u003c')
        with args.output.open('x', encoding='utf-8') as output:
            output.write(template.replace('@@REPORT_DATA@@', payload, 1))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(2, f'{exc}\n')


if __name__ == '__main__':
    main()
