"""Render a self-contained update report from a batch JSON file."""

import argparse
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


BATCH_FIELDS = {'batch', 'caption', 'groups', 'current', 'paused'}
ITEM_TEXT_FIELDS = ('target', 'current', 'candidate')
USER_ACTION_FIELDS = {'target', 'action', 'waiting'}


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


def require_list(value, label):
    if not isinstance(value, list):
        raise ValueError(f'{label} must be a list')


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


def validate_actions(actions, label):
    require_nonempty_list(actions, label)
    for index, action in enumerate(actions):
        entry = f'{label}[{index}]'
        require_object(action, entry, {'when', 'work', 'verify'})
        if action['when'] not in ('now', 'after-authorization'):
            raise ValueError(f'{entry}.when must be now or after-authorization')
        require_text(action['work'], f'{entry}.work')
        require_text(action['verify'], f'{entry}.verify')


def validate_followups(followups):
    require_list(followups, 'followups')
    for index, followup in enumerate(followups):
        label = f'followups[{index}]'
        require_object(followup, label, {'target', 'status', 'actions'})
        require_text(followup['target'], f'{label}.target')
        require_text(followup['status'], f'{label}.status')
        validate_actions(followup['actions'], f'{label}.actions')


def validate_choices(decision, label):
    options = decision['options']
    if not isinstance(options, list) or len(options) < 2:
        raise ValueError(f'{label}.options must be a list with at least two options')
    labels = set()
    for index, option in enumerate(options):
        entry = f'{label}.options[{index}]'
        require_object(option, entry, {'label', 'impact'})
        require_text(option['label'], f'{entry}.label')
        require_text(option['impact'], f'{entry}.impact')
        option_label = option['label'].strip()
        if option_label in labels:
            raise ValueError(f'{entry}.label duplicates another option')
        labels.add(option_label)
    recommendation = decision['recommendation']
    if type(recommendation) is not int or not 0 <= recommendation < len(options):
        raise ValueError(f'{label}.recommendation must be a zero-based option index')


def validate_user_actions(entries, key, candidate_ids):
    require_list(entries, key)
    decisions = key == 'decisions'
    fields = USER_ACTION_FIELDS | {'options', 'recommendation'} if decisions else USER_ACTION_FIELDS
    for index, entry in enumerate(entries):
        label = f'{key}[{index}]'
        require_object(entry, label, fields, ('candidateId',))
        for field in sorted(USER_ACTION_FIELDS):
            require_text(entry[field], f'{label}.{field}')
        if 'candidateId' in entry:
            identifier = entry['candidateId']
            if not isinstance(identifier, str) or identifier not in candidate_ids:
                raise ValueError(f'{label}.candidateId must match a candidate ID')
        if decisions:
            validate_choices(entry, label)


def validate_groups(groups, *, legacy):
    text_fields = (*ITEM_TEXT_FIELDS, 'risk', 'action') if legacy else ITEM_TEXT_FIELDS
    flag_fields = ('safe', 'ready') if legacy else ('ready',)
    fields = {'id', 'details', *text_fields, *flag_fields}
    optional = ('source',)
    if not legacy:
        fields.add('actions')
        optional += ('notice',)

    require_nonempty_list(groups, 'groups')
    seen = set()
    for group_index, group in enumerate(groups):
        group_label = f'groups[{group_index}]'
        require_object(group, group_label, {'name', 'items'})
        require_text(group['name'], f'{group_label}.name')
        require_nonempty_list(group['items'], f'{group_label}.items')
        for item_index, item in enumerate(group['items']):
            label = f'{group_label}.items[{item_index}]'
            require_object(item, label, fields, optional)
            identifier = item['id']
            if not isinstance(identifier, str) or not re.fullmatch(r'[A-Z][A-Z0-9-]*[0-9]', identifier):
                raise ValueError(f'{label}.id is invalid')
            if identifier in seen:
                raise ValueError(f'duplicate candidate ID: {identifier}')
            seen.add(identifier)
            for key in text_fields:
                require_text(item[key], f'{identifier}.{key}')
            for key in flag_fields:
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
            if not legacy:
                validate_actions(item['actions'], f'{identifier}.actions')
                if 'notice' in item:
                    require_text(item['notice'], f'{identifier}.notice')
    return seen


def load_batch(path):
    batch = json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=unique_keys)
    if not isinstance(batch, dict):
        raise ValueError('batch plan must be an object')
    schema = batch.get('schema', 1)
    if type(schema) is not int or schema not in (1, 2):
        raise ValueError('schema must be the integer 1 or 2')
    legacy = schema == 1
    extra_fields = {'pending'} if legacy else {'followups', 'notices', 'decisions', 'operations'}
    require_object(batch, 'batch plan', BATCH_FIELDS | extra_fields, ('schema',))
    batch_date = batch['batch']
    if not isinstance(batch_date, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', batch_date):
        raise ValueError('batch must be an ISO date (YYYY-MM-DD)')
    date.fromisoformat(batch_date)
    require_text(batch['caption'], 'caption')
    for key in ('pending' if legacy else 'notices', 'current', 'paused'):
        require_list(batch[key], key)
        for index, value in enumerate(batch[key]):
            require_text(value, f'{key}[{index}]')
    candidate_ids = validate_groups(batch['groups'], legacy=legacy)
    if not legacy:
        validate_followups(batch['followups'])
        for key in ('decisions', 'operations'):
            validate_user_actions(batch[key], key, candidate_ids)
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
