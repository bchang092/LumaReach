"""Apply/dry-run/rollback integration on temporary sidecars, never workbook writes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.resource_source import MASTER,digest,read_source

sha=digest(MASTER.read_bytes())
with tempfile.TemporaryDirectory() as temp:
    target=Path(temp)/'tags.json';backup=Path(temp)/'rollback.json'
    cmd=[sys.executable,str(ROOT/'scripts/tag_migration.py'),'--target',str(target)]
    # Exercise the CLI against the active workbook and its exact evidence.
    active=json.loads((ROOT/'input_data/resource_tags.json').read_text())
    rows=[]
    for source in read_source()[1]:
        rid=source['resource_id']
        record=active['resources'].get(str(rid))
        rows.append(dict(record or {}, source=source, resource_id=rid, name=source['name'],
                         old_category=source['old_category'], old_tags=[], approved=bool(record),
                         review_flag=not record, new_tags=record['tags'] if record else []))
    fixture=dict(schema_version=1, taxonomy_version=active['taxonomy_version'],
                 source_sha256=sha, resources=rows)
    review_path=Path(temp)/'november.json'
    review_path.write_text(json.dumps(fixture))
    review=['--review',str(review_path)]
    subprocess.run(cmd+review+['--dry-run'],check=True,stdout=subprocess.DEVNULL)
    assert not target.exists() and not backup.exists()
    subprocess.run(cmd+review+['--apply','--backup',str(backup)],check=True,stdout=subprocess.DEVNULL)
    assert len(json.loads(target.read_text())['resources'])==len(active['resources'])
    subprocess.run(cmd+['--rollback',str(backup),'--dry-run'],check=True,stdout=subprocess.DEVNULL)
    assert target.exists()
    subprocess.run(cmd+['--rollback',str(backup),'--apply'],check=True,stdout=subprocess.DEVNULL)
    assert not target.exists()
    # Existing files restore byte for byte, and post-migration edits reject rollback.
    original=(ROOT/'input_data/resource_tags.json').read_bytes();target.write_bytes(original)
    changed=fixture
    for r in changed['resources']:
        if r['approved']:
            current=json.loads(original)['resources'][str(r['resource_id'])]
            r['old_tags']=current['tags'];r['new_tags']=current['tags'];r['evidence']=current['evidence']
            r['reviewer']=current['reviewer'];r['reviewed_at']=current['reviewed_at']
    review_path=Path(temp)/'review.json';review_path.write_text(json.dumps(changed))
    backup2=Path(temp)/'rollback2.json'
    subprocess.run(cmd+['--review',str(review_path),'--apply','--backup',str(backup2)],check=True,stdout=subprocess.DEVNULL)
    applied=target.read_bytes()
    target.write_bytes(applied+b' ')
    rejected=subprocess.run(cmd+['--rollback',str(backup2),'--apply'],capture_output=True)
    assert rejected.returncode!=0
    target.write_bytes(applied)
    subprocess.run(cmd+['--rollback',str(backup2),'--apply'],check=True,stdout=subprocess.DEVNULL)
    assert target.read_bytes()==original
assert digest(MASTER.read_bytes())==sha
print('Migration IO: dry-run no-write, create, rollback deletion, byte-exact restoration, stale rollback rejection, unchanged workbook passed.')
