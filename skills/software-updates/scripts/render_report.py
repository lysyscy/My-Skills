"""Render a self-contained update report from a batch JSON file."""

import argparse
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


BATCH_FIELDS = {'batch', 'caption', 'groups', 'pending', 'current', 'paused'}
ITEM_TEXT_FIELDS = ('target', 'current', 'candidate', 'risk', 'action')
ITEM_FIELDS = {'id', 'safe', 'ready', 'details', *ITEM_TEXT_FIELDS}


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key!a}')
        result[key] = value
    return result


def require_object(value, label, required, optional=()):
    if not isinstance(value, dict):
        raise ValueError(f'{label} must be an object')
    missing = required - value.keys()
    if missing:
        raise ValueError(f'{label} is missing keys: {sorted(missing)!a}')
    unknown = value.keys() - required - set(optional)
    if unknown:
        raise ValueError(f'{label} has unknown keys: {sorted(unknown)!a}')


def require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be a nonempty string')


def require_nonempty_list(value, label):
    if not isinstance(value, list) or not value:
        raise ValueError(f'{label} must be a nonempty list')


def validate_source(value, label):
    require_text(value, label)
    if re.search(r'[\s\x00-\x1f\x7f\\<>"^`{|}]|%(?![0-9a-fA-F]{2})', value):
        raise ValueError(f'{label} must be an HTTPS URL')
    source = urlsplit(value)
    authority = source.netloc.rsplit('@', 1)[-1]
    if (
        source.scheme != 'https'
        or not source.hostname
        or source.netloc.count('@') > 1
        or not re.fullmatch(r'(?:\[[^\]]+\]|[^:\[\]]+)(?::[0-9]*)?', authority)
    ):
        raise ValueError(f'{label} must be an HTTPS URL with a hostname')
    if not authority.startswith('['):
        hostname = unquote(source.hostname, errors='strict')
        if re.search(r'[\s\x00-\x1f\x7f#%/:<>?@\[\\\]\^|]', hostname):
            raise ValueError(f'{label} has an invalid hostname')
    _ = source.port  # urlsplit validates the port lazily.


def load_batch(path):
    batch = json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=unique_keys)
    require_object(batch, 'batch plan', BATCH_FIELDS, ('schema',))
    if 'schema' in batch and (type(batch['schema']) is not int or batch['schema'] != 1):
        raise ValueError('schema must be the integer 1')
    batch_date = batch['batch']
    if not isinstance(batch_date, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', batch_date):
        raise ValueError('batch must be an ISO date (YYYY-MM-DD)')
    date.fromisoformat(batch_date)
    require_text(batch['caption'], 'caption')
    for key in ('pending', 'current', 'paused'):
        if not isinstance(batch[key], list):
            raise ValueError(f'{key} must be a list of strings')
        for index, value in enumerate(batch[key]):
            require_text(value, f'{key}[{index}]')
    require_nonempty_list(batch['groups'], 'groups')
    seen = set()
    for group_index, group in enumerate(batch['groups']):
        group_label = f'groups[{group_index}]'
        require_object(group, group_label, {'name', 'items'})
        require_text(group['name'], f'{group_label}.name')
        require_nonempty_list(group['items'], f'{group_label}.items')
        for item_index, item in enumerate(group['items']):
            label = f'{group_label}.items[{item_index}]'
            require_object(item, label, ITEM_FIELDS, ('source',))
            identifier = item['id']
            if not isinstance(identifier, str) or not re.fullmatch(r'[A-Z][A-Z0-9-]*[0-9]', identifier):
                raise ValueError(f'{label}.id is invalid')
            if identifier in seen:
                raise ValueError(f'duplicate candidate ID: {identifier}')
            seen.add(identifier)
            for key in ITEM_TEXT_FIELDS:
                require_text(item[key], f'{identifier}.{key}')
            for key in ('safe', 'ready'):
                if not isinstance(item[key], bool):
                    raise ValueError(f'{identifier}.{key} must be boolean')
            details = item['details']
            if not isinstance(details, dict) or not details:
                raise ValueError(f'{identifier}.details must be a nonempty object')
            for key, value in details.items():
                require_text(key, f'{identifier}.details key')
                require_text(value, f'{identifier}.details[{key!a}]')
            if 'source' in item:
                validate_source(item['source'], f'{identifier}.source')
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
        payload.encode('utf-8')  # Reject unpaired surrogates before creating the output.
        with args.output.open('x', encoding='utf-8') as output:
            output.write(template.replace('@@REPORT_DATA@@', payload, 1))
    except (OSError, ValueError, RecursionError) as exc:
        parser.exit(2, f'{exc}\n')


if __name__ == '__main__':
    main()
