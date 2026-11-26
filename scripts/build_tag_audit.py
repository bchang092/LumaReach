"""Generate review artifacts only. Does not edit the workbook or active tags."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path

from resource_source import SEPTEMBER_MASTER as MASTER, ROOT, json_bytes, read_source
from tag_audit_rules import propose

VERSION = '2026-10-24.v1'
AUDITED_SOURCE_SHA256 = 'd36da671b9ec19ef8b94aa6512682bbcefb987b82567f07775cc084baa138d41'


def build():
    sha, sources = read_source(MASTER)
    if sha != AUDITED_SOURCE_SHA256:
        raise ValueError('Workbook differs from the individually reviewed snapshot. Re-audit before reusing ID-specific decisions.')
    proposals = [propose(source) for source in sources]
    counts = Counter(tag for r in proposals for tag in r['new_tags'])
    taxonomy = {'version':VERSION, 'layers':{
        'need':'Need category and specific service subtype. No service inferred from organization name or old category.',
        'constraint':'Reported access, population, cost, insurance, food format, and site-hour facts. Not universal eligibility.'},
        'unknown_policy':'Missing evidence is unknown, never false or unrestricted.',
        'scope_policy':'All constraints require program-scope confirmation before hard eligibility filtering. Population served is not an exclusion rule. Office hours are not program intake hours.',
        'tags':[{'tag':tag,'layer':'need' if tag.startswith('need:') else 'constraint',
                 'category':tag.split(':')[-1].split('.')[0],
                 'label':tag.replace('need:','').replace('_',' ').replace('.',' / '),
                 'resource_count':count} for tag,count in sorted(counts.items())]}
    audit = {'schema_version':1,'taxonomy_version':VERSION,
             'status':'proposal_only','created_date':'2026-10-24',
             'source_workbook':str(MASTER.relative_to(ROOT)), 'source_sheet':'Scraper-Verified',
             'source_sha256':sha, 'method':{
                 'description_coverage':'All 1362 descriptions inspected individually; conservative phrase rules produce reproducible evidence spans.',
                 'constraint_evidence':'Descriptions, restrictions, and posted site hours. Names and old categories excluded from inference.',
                 'approval':'No resource is approved. Human review flags require resolution before migration.',
                 'confidence':'Confidence in proposed tagging only; distinct from scraped reliability/confidence, which are preserved.'},
             'resources':proposals}
    mapping = defaultdict(Counter)
    old_counts = Counter()
    for r in proposals:
        old_counts[r['old_category']] += 1
        mapping[r['old_category']].update(t for t in r['new_tags'] if t.startswith('need:'))
    old_mapping = {'old_resource_tags':{},
                   'explanation':'Source has no resource tags. Broad categories map to multiple proposed service tags; do not apply a global replacement.',
                   'categories':[{'old_category':cat,'resource_count':old_counts[cat],
                                  'proposed_need_tag_counts':dict(sorted(counts.items()))}
                                 for cat,counts in sorted(mapping.items())]}
    summary = {'resource_count':len(proposals),'approved_count':0,
               'proposed_changed_count':sum(r['old_tags']!=r['new_tags'] for r in proposals),
               'no_supported_need_count':sum(not any(t.startswith('need:') for t in r['new_tags']) for r in proposals),
               'flagged_count':sum(r['review_flag'] for r in proposals),
               'confidence_counts':dict(Counter(r['confidence'] for r in proposals)),
               'review_reason_counts':dict(Counter(f for r in proposals for f in r['review_reasons'])),
               'tag_counts':dict(sorted(counts.items())),
               'source_sha256':sha}
    summary['need_category_count'] = len({t.split(':')[1].split('.')[0] for t in counts if t.startswith('need:')})
    summary['need_subtype_count'] = sum(t.startswith('need:') for t in counts)
    summary['constraint_tag_count'] = sum(not t.startswith('need:') for t in counts)
    return {'resource_tag_proposals.json':audit,'taxonomy.json':taxonomy,
            'old_to_new_tags.json':old_mapping,'summary.json':summary}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'audits/phase1')
    args = parser.parse_args()
    artifacts = build()
    args.output.mkdir(parents=True,exist_ok=True)
    for name,value in artifacts.items():
        (args.output/name).write_bytes(json_bytes(value))
    summary = artifacts['summary.json']
    print({k:v for k,v in summary.items() if k not in ('tag_counts','review_reason_counts')})
