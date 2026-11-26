"""One immutable directory: original workbook + additive, reviewed sidecars.
Caches public resources only, never intake text. Snapshot mismatches fail closed.
"""
from collections import Counter
import copy
import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from scripts.resource_source import ROOT, MASTER, read_source
from .display import description_for_display
from .tag_validation import validate_tags


class DirectoryError(RuntimeError):
    pass


def read_json(path):
    return json.loads(Path(path).read_text())


def verified_date(value):
    try:
        return datetime.strptime(str(int(float(value))).zfill(8), '%m%d%Y').date().isoformat()
    except (ValueError, TypeError):
        return None


class Directory:
    def __init__(self):
        sha, sources = read_source()
        self.source_sha256 = sha
        self.taxonomy = read_json(ROOT / 'audits/phase1/taxonomy.json')
        self.allowed_needs = {t['tag'] for t in self.taxonomy['tags'] if t['layer'] == 'need'}
        sidecar = read_json(ROOT / 'input_data/resource_tags.json')
        if sidecar['source_sha256'] != sha:
            raise DirectoryError('Tag snapshot needs a new audit.')
        try:
            validate_tags(sidecar, self.taxonomy, sources)
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            raise DirectoryError('Active tags failed evidence validation; re-audit the sidecar.') from error
        counts = Counter(t for row in sidecar['resources'].values() for t in row['tags'])
        for tag in self.taxonomy['tags']:
            tag['resource_count'] = counts[tag['tag']]
        self.records = {}
        self.active = []
        for row in sources:
            rid = row['resource_id']
            tags = sidecar['resources'].get(str(rid))
            if tags and tags['record_sha256'] != row['record_sha256']:
                raise DirectoryError('Tag evidence is stale.')
            record = copy.deepcopy(row)
            record["display_description"]=description_for_display(rid,row["description"])
            record.update(tags=tags['tags'] if tags else [], evidence=tags['evidence'] if tags else {},
                          tag_status=('automatically_tagged' if tags and tags.get('assignment_method') == 'automatic'
                                      else 'reviewed_for_service_matching' if tags else 'no_active_service_tags'),
                          verified_date=verified_date(row['protected_metadata']['Date Verified']),
                          reliability_score=row['protected_metadata']['Reliability Score'],
                          classification=row['protected_metadata']['Classification'])
            self.records[rid] = record
            if tags:
                self.active.append(record)
        for entry in read_json(ROOT / 'input_data/safety_directory.json')['resources']:
            if entry['resource_id'] in self.records:
                raise DirectoryError('Duplicate directory ID.')
            self.records[entry['resource_id']] = entry
        # Program-scoped hard facts are separate from reported, unscoped tags.
        self.eligibility = read_json(ROOT / 'input_data/eligibility_facts.json')['facts']
        for fact in self.eligibility:
            record = self.records.get(fact['resource_id'])
            if (not record or fact['record_sha256'] != record.get('record_sha256') or
                fact['need'] not in record['tags'] or not fact['reviewer'] or
                not fact['verified_at'] or not fact['evidence'] or fact.get('evidence_field') not in ('description', 'restrictions') or fact['evidence'] not in record[fact['evidence_field']] or not fact['source_url'] or
                fact['decision'] not in ('allows', 'excludes')):
                raise DirectoryError('Invalid scoped eligibility evidence.')

    def get(self, rid):
        record = self.records.get(int(rid))
        return copy.deepcopy(record) if record else None

    def safety_records(self, crisis=True):
        return [self.get(rid) for rid in ((900001, 900002, 900004) if crisis else (900003,))]


def _signature():
    paths = [MASTER, ROOT/'input_data/resource_tags.json', ROOT/'input_data/safety_directory.json',
             ROOT/'input_data/eligibility_facts.json', ROOT/'audits/phase1/taxonomy.json']
    return tuple((p.stat().st_mtime_ns, p.stat().st_size) for p in paths)


@lru_cache(maxsize=1)
def _cached(signature):
    return Directory()


def directory():
    return _cached(_signature())


class SafetyDirectory:
    """Crisis lookup remains available when the workbook/tag index is unavailable."""
    def safety_records(self, crisis=True):
        ids=(900001,900002,900004) if crisis else (900003,)
        records=read_json(ROOT/'input_data/safety_directory.json')['resources']
        return [copy.deepcopy(r) for rid in ids for r in records if r['resource_id']==rid]
