"""Apply an approved tag review to an ADDITIVE JSON sidecar, never the workbook.

Prepared for review; do not run until the Phase 1 approval checkpoint is passed.
Default is dry-run. --apply is required for writes. Rollback is hash-guarded.
"""
import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile

from resource_source import MASTER, ROOT, digest, json_bytes, read_source

DEFAULT_TARGET = ROOT / 'input_data/resource_tags.json'
DEFAULT_TAXONOMY = ROOT / 'audits/phase1/taxonomy.json'


def parse_json(raw):
    def pairs(items):
        out = {}
        for k,v in items:
            if k in out:
                raise ValueError(f'Duplicate JSON key: {k}')
            out[k] = v
        return out
    return json.loads(raw,object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite JSON number')))


def plan(review, taxonomy, source_sha, sources, previous=None):
    """Pure validation and planning. Returns new sidecar; performs no writes."""
    if review.get('schema_version') != 1:
        raise ValueError('Unsupported review schema')
    if review.get('source_sha256') != source_sha:
        raise ValueError('Stale workbook fingerprint')
    if review.get('taxonomy_version') != taxonomy.get('version'):
        raise ValueError('Taxonomy version mismatch')
    allowed = {r['tag'] for r in taxonomy['tags']}
    authoritative = {r['resource_id']:r for r in sources}
    rows = review.get('resources',[])
    ids = [r.get('resource_id') for r in rows]
    if any(type(i) is not int for i in ids) or len(ids)!=len(set(ids)) or set(ids)!=set(authoritative):
        raise ValueError('Review must contain every source ID exactly once')
    current = {}
    if previous is not None:
        if previous.get('schema_version')!=1 or previous.get('source_sha256')!=source_sha or previous.get('taxonomy_version')!=taxonomy['version']:
            raise ValueError('Existing sidecar schema/source/taxonomy mismatch')
        current = dict(previous.get('resources',{}))
        for key,record in current.items():
            if not isinstance(key,str) or not key.isdigit() or str(int(key))!=key or int(key) not in authoritative:
                raise ValueError('Existing sidecar contains an unknown resource ID')
            if record.get('record_sha256')!=authoritative[int(key)]['record_sha256']:
                raise ValueError('Existing sidecar has stale resource evidence')
            tags = record.get('tags')
            if not isinstance(tags,list) or any(not isinstance(t,str) for t in tags) or len(tags)!=len(set(tags)) or not set(tags)<=allowed:
                raise ValueError('Existing sidecar contains invalid tags')
    changed = 0
    for row in rows:
        rid = row['resource_id']
        source = authoritative[rid]
        if row.get('source') != source or row.get('name') != source['name'] or row.get('old_category')!=source['old_category']:
            raise ValueError(f'Source snapshot/name/category modified for {rid}')
        if type(row.get('approved')) is not bool or type(row.get('review_flag')) is not bool:
            raise ValueError(f'Approval and review_flag must be booleans: {rid}')
        if not row['approved']:
            continue
        if row['review_flag'] or row.get('review_reasons'):
            raise ValueError(f'Unresolved review flags: {rid}')
        if not isinstance(row.get('reviewer'),str) or not row['reviewer'].strip():
            raise ValueError(f'Missing reviewer: {rid}')
        try:
            timestamp = datetime.fromisoformat(row['reviewed_at'].replace('Z','+00:00'))
            if timestamp.utcoffset() is None:
                raise ValueError('Timezone required')
        except (ValueError,TypeError,KeyError,AttributeError):
            raise ValueError(f'Invalid timezone-aware review timestamp: {rid}') from None
        old = current.get(str(rid),{}).get('tags',[])
        if row.get('old_tags') != old:
            raise ValueError(f'Stale old_tags for {rid}')
        tags = row.get('new_tags')
        if not isinstance(tags,list) or any(not isinstance(t,str) for t in tags) or len(tags)!=len(set(tags)) or not set(tags)<=allowed:
            raise ValueError(f'Invalid taxonomy tags: {rid}')
        evidence = row.get('evidence')
        if not isinstance(evidence,dict) or set(evidence)!=set(tags):
            raise ValueError(f'Every tag requires evidence: {rid}')
        for tag,fact in evidence.items():
            field = fact.get('field')
            if field not in ('description','restrictions','hours') or tag.startswith('need:') and field!='description':
                raise ValueError(f'Invalid evidence field: {rid}/{tag}')
            a,b = fact.get('start'),fact.get('end')
            if type(a) is not int or type(b) is not int or not 0<=a<b<=len(source[field]):
                raise ValueError(f'Invalid evidence span: {rid}/{tag}')
            if source[field][a:b]!=fact.get('snippet') or not fact.get('context') or fact['context'] not in source[field]:
                raise ValueError(f'Evidence does not match source: {rid}/{tag}')
            if fact.get('hard_filter_eligible') is not False:
                raise ValueError('Phase 1 sidecar cannot assert unscoped hard eligibility rules')
            if fact.get('scope') not in ('described_service','enrolled_clients_or_residents','program_or_location_unconfirmed','referral_or_partner_delivery_unconfirmed','program_scope_requires_confirmation','site_hours_not_program_intake'):
                raise ValueError(f'Unknown evidence scope: {rid}/{tag}')
        if row.get('confidence') not in ('high','medium','low'):
            raise ValueError(f'Invalid confidence: {rid}')
        current[str(rid)] = {'tags':tags,'evidence':evidence,
                             'confidence':row['confidence'],
                             'reviewer':row['reviewer'],'reviewed_at':row['reviewed_at'],
                             'record_sha256':source['record_sha256']}
        changed += 1
    if not changed:
        raise ValueError('No approved records; nothing to apply')
    return {'schema_version':1,'taxonomy_version':taxonomy['version'],
            'source_sha256':source_sha,'resources':current}, changed


def rollback_plan(backup, target, current_bytes):
    """Pure rollback validation. None means remove a newly created sidecar."""
    if backup.get('schema_version')!=1 or backup.get('target')!=str(Path(target).resolve()):
        raise ValueError('Rollback target/schema mismatch')
    if current_bytes is None or digest(current_bytes)!=backup.get('after_sha256'):
        raise ValueError('Current tags changed since migration; refusing rollback')
    encoded = backup.get('before_base64')
    before = None if encoded is None else base64.b64decode(encoded,validate=True)
    if (None if before is None else digest(before))!=backup.get('before_sha256'):
        raise ValueError('Corrupt rollback backup')
    return before


def atomic_write(path,data):
    fd, temp = tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


@contextmanager
def locked(target):
    lock = target.with_name(target.name+'.lock')
    fd = os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--review',type=Path)
    action.add_argument('--rollback',type=Path)
    parser.add_argument('--target',type=Path,default=DEFAULT_TARGET)
    parser.add_argument('--taxonomy',type=Path,default=DEFAULT_TAXONOMY)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply',action='store_true')
    mode.add_argument('--dry-run',action='store_true')
    parser.add_argument('--backup',type=Path)
    args = parser.parse_args()
    if args.target.is_symlink():
        raise ValueError('Refusing symlink target')
    target = args.target.resolve()
    protected = {MASTER.resolve(),args.taxonomy.resolve()}
    if args.review:
        protected.add(args.review.resolve())
    if args.rollback:
        protected.add(args.rollback.resolve())
    if target.suffix!='.json' or target in protected:
        raise ValueError('Target must be a separate JSON sidecar')
    before = target.read_bytes() if target.exists() else None
    if args.rollback:
        backup = parse_json(args.rollback.read_bytes())
        after = rollback_plan(backup,target,before)
        count = 'rollback'
    else:
        sha,sources = read_source()
        review = parse_json(args.review.read_bytes())
        taxonomy = parse_json(args.taxonomy.read_bytes())
        new,count = plan(review,taxonomy,sha,sources,None if before is None else parse_json(before))
        after = json_bytes(new)
    if not args.apply:
        print(json.dumps({'mode':'dry-run','target':str(target),'approved_records':count,
                          'before_sha256':None if before is None else digest(before),
                          'after_sha256':None if after is None else digest(after)}))
        return
    if not target.parent.exists():
        raise ValueError('Target directory must already exist')
    with locked(target):
        actual = target.read_bytes() if target.exists() else None
        if actual!=before:
            raise ValueError('Concurrent sidecar modification')
        if args.rollback:
            rollback_plan(backup,target,actual)
        else:
            if digest(MASTER.read_bytes())!=sha:
                raise ValueError('Workbook changed during approval validation')
            if args.backup is None:
                raise ValueError('--backup is required for --apply')
            backup_path = args.backup.resolve()
            if backup_path in protected|{target} or args.backup.is_symlink():
                raise ValueError('Backup must be a separate, new file')
            backup = {'schema_version':1,'target':str(target),
                      'created_at':datetime.now(timezone.utc).isoformat(),
                      'before_sha256':None if before is None else digest(before),
                      'after_sha256':digest(after),
                      'before_base64':None if before is None else base64.b64encode(before).decode('ascii')}
            # Exclusive creation prevents overwriting any prior rollback data.
            with backup_path.open('xb') as handle:
                handle.write(json_bytes(backup));handle.flush();os.fsync(handle.fileno())
        if after is None:
            target.unlink()
        else:
            atomic_write(target,after)
    print(json.dumps({'mode':'applied','target':str(target),'approved_records':count}))


if __name__=='__main__':
    main()
