"""Validate activated tag evidence on every directory reload, not just migration."""
from datetime import datetime

SCOPES = {'described_service', 'enrolled_clients_or_residents',
          'program_or_location_unconfirmed', 'referral_or_partner_delivery_unconfirmed',
          'program_scope_requires_confirmation', 'site_hours_not_program_intake'}


def validate_tags(sidecar, taxonomy, sources):
    if sidecar.get('schema_version') != 1 or sidecar.get('taxonomy_version') != taxonomy['version']:
        raise ValueError('Tag schema/taxonomy mismatch')
    allowed = {t['tag'] for t in taxonomy['tags']}
    source_by_id = {str(r['resource_id']): r for r in sources}
    resources = sidecar.get('resources')
    if not isinstance(resources, dict) or not set(resources) <= set(source_by_id):
        raise ValueError('Unknown tag resource ID')
    for rid, record in resources.items():
        source = source_by_id[rid]
        if record.get('record_sha256') != source['record_sha256']:
            raise ValueError('Stale tag evidence')
        tags, evidence = record.get('tags'), record.get('evidence')
        if (not isinstance(tags, list) or any(not isinstance(t, str) for t in tags)
                or len(tags) != len(set(tags)) or not set(tags) <= allowed
                or not isinstance(evidence, dict) or set(evidence) != set(tags)):
            raise ValueError('Every valid tag needs evidence')
        if not isinstance(record.get('reviewer'), str) or not record['reviewer'].strip():
            raise ValueError('Missing review attribution')
        stamp = datetime.fromisoformat(record['reviewed_at'].replace('Z', '+00:00'))
        if stamp.utcoffset() is None or record.get('confidence') not in {'high', 'medium', 'low'}:
            raise ValueError('Invalid review metadata')
        for tag, fact in evidence.items():
            field = fact.get('field')
            if field not in {'description', 'restrictions', 'hours'} or (tag.startswith('need:') and field != 'description'):
                raise ValueError('Invalid evidence field')
            start, end = fact.get('start'), fact.get('end')
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(source[field]):
                raise ValueError('Invalid evidence span')
            if source[field][start:end] != fact.get('snippet') or not fact.get('context') or fact['context'] not in source[field]:
                raise ValueError('Evidence differs from source')
            if fact.get('scope') not in SCOPES or fact.get('hard_filter_eligible') is not False:
                raise ValueError('Unscoped evidence cannot establish eligibility')
