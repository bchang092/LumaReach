"""Rebuild September's reviewed tags against the November workbook's current evidence."""
import json
import re


from resource_source import MASTER, SEPTEMBER_MASTER, ROOT, json_bytes, read_source
from tag_audit_rules import matches, norm, propose
from sys import path
path.insert(0, str(ROOT))
from lifeline_core.tag_validation import validate_tags

ARCHIVE = ROOT / 'input_data/archive/2026-09'
# These eight ID/name changes were compared in the two fixed workbook snapshots.
RENAMED = {12, 235, 316, 322, 583, 671, 925, 1211}
REVIEWED_PHRASES = {
    (48, 'need:medical.general'): 'delivering medical and related health services',
    (89, 'need:food.pantry'): 'food distribution center',
    (166, 'need:food.pantry'): 'food distribution center',
    (183, 'need:food.pantry'): 'food distribution center',
    (299, 'need:care.assisted_living'): 'daily living assistance',
    (338, 'need:housing.rental'): 'rental townhomes',
    (409, 'need:education.learning'): 'providing individualized instruction',
    (451, 'need:care.adult_day'): 'daytime-care facility serving adults',
    (569, 'need:care.assisted_living'): 'assistance with activities of daily living',
    (623, 'need:education.learning'): 'provides specialized instruction',
    (624, 'need:education.learning'): 'offering education and early intervention',
    (797, 'need:employment.training_search'): 'training programs to help people become auto mechanics',
    (826, 'need:medical.general'): 'comprehensive medical and surgical care',
    (862, 'need:mental_health.clinical'): 'counseling/therapy',
    (908, 'need:mental_health.clinical'): 'Outpatient mental health and substance-use counseling',
    (956, 'need:mental_health.clinical'): 'provides individual, couple, family, and group therapy',
    (980, 'need:mental_health.clinical'): 'therapy (individual and group)',
    (1032, 'need:mental_health.clinical'): 'Licensed mental health counselors',
    (1095, 'need:food.general_assistance'): 'distributes groceries',
    (1121, 'need:disaster.preparedness'): 'prepare for emergencies',
    (1140, 'need:legal.advocacy_information'): 'provides legal information and attorney referrals',
    (1145, 'need:immigration.support'): 'immigration services',
    (1250, 'need:care.home'): 'home healthcare and companion care',
    (1261, 'need:medical.rehabilitation'): 'provides short-stay rehabilitation',
    (1293, 'need:community.social_recreation'): 'provides recreational and fitness programs',

    (1041, 'need:housing.medical_lodging'): 'temporary home for families with a hospitalized child',
    (1132, 'need:legal.assistance'): 'individual consultations',
    (979, 'insurance.medicaid_reported'): 'Medicaid is accepted',
}
# Program-level eligibility requires explicit evidence beyond a general service tag.
ELIGIBILITY = {
    (79, 'saturday'): ('restrictions', 'Saturday distribution supported by volunteers'),
    (79, 'weekends'): ('restrictions', 'Saturday distribution supported by volunteers'),
    (913, 'child'): ('description', 'therapy for adults and children'),
    (979, 'child'): ('description', 'for children, adolescents, and adults, including therapy'),
    (979, 'medicaid'): ('restrictions', 'Medicaid is accepted'),
    (1041, 'child'): ('description', 'temporary home for families with a hospitalized child'),
    (1362, 'free'): ('description', 'free adaptive mobility equipment to children with disabilities'),
    (1362, 'child'): ('description', 'free adaptive mobility equipment to children with disabilities'),
    (1132, 'free'): ('restrictions', 'In-person consultations are $90; Zoom consultations are $100'),
}


def main():
    old_sha, old_rows = read_source(SEPTEMBER_MASTER)
    sha, rows = read_source()
    if sha != 'e7bd62fdcd50bfd08648a12df9c0a374771e4a1949823611d85b7e9e47b52f41':
        raise ValueError('This transfer was reviewed for the November 24 snapshot only')
    prior = json.loads((ARCHIVE / 'resource_tags.json').read_text())
    validate_tags(prior, json.loads((ROOT/'audits/phase1/taxonomy.json').read_text()), old_rows)
    assert old_sha == prior['source_sha256']
    old = {r['resource_id']:r for r in old_rows}
    active = {}
    omitted = {}
    for row in rows:
        rid = row['resource_id']
        previous = prior['resources'].get(str(rid))
        if not previous:
            continue
        if row['name'] != old[rid]['name'] and rid not in RENAMED:
            raise ValueError(f'Unreviewed identity change at {rid}')
        proposal = propose(row)
        evidence = {}
        for tag, original in previous['evidence'].items():
            fact = proposal['evidence'].get(tag)
            if not fact:
                field = original['field']
                snippet = REVIEWED_PHRASES.get((rid, tag), original['snippet'])
                found = matches(row[field], re.escape(norm(snippet)), field)
                if found:
                    fact = {**original, **found[0]}
            if fact and 'needs_human_review:operating_status' not in proposal['review_reasons']:
                if original['scope'] != 'described_service':
                    fact['scope'] = original['scope']
                if rid == 1076 and tag == 'need:food.general_assistance':
                    fact['scope'] = 'referral_or_partner_delivery_unconfirmed'
                evidence[tag] = fact
        if not any(t.startswith('need:') for t in evidence):
            evidence.clear()
        if evidence:
            active[str(rid)] = dict(previous, tags=sorted(evidence), evidence=evidence,
                                    record_sha256=row['record_sha256'], confidence='medium',
                                    reviewer='November workbook evidence transfer', reviewed_at='2026-11-25T00:00:00-05:00')
        missing = sorted(set(previous['tags']) - evidence.keys())
        if missing:
            omitted[str(rid)] = missing
    transferred = sum(len(record['tags']) for record in active.values())
    automatically_tagged = 0
    for row in rows:
        rid = str(row['resource_id'])
        if rid in active:
            continue
        proposal = propose(row)
        if ('needs_human_review:operating_status' in proposal['review_reasons']
                or not any(tag.startswith('need:') for tag in proposal['new_tags'])):
            continue
        active[rid] = {
            'tags': proposal['new_tags'], 'evidence': proposal['evidence'],
            'record_sha256': row['record_sha256'], 'confidence': proposal['confidence'],
            'reviewer': 'November automated phrase matching (operator accepted)',
            'assignment_method': 'automatic', 'reviewed_at': '2026-11-26T00:00:00-05:00',
        }
        automatically_tagged += 1
    tags = dict(prior, source_sha256=sha, resources=active)
    validate_tags(tags, json.loads((ROOT/'audits/phase1/taxonomy.json').read_text()), rows)
    by_id = {r['resource_id']:r for r in rows}
    facts = json.loads((ARCHIVE/'eligibility_facts.json').read_text())
    retained = []
    for fact in facts['facts']:
        rid = fact['resource_id']
        phrase = ELIGIBILITY.get((rid, fact['value']))
        if not phrase:
            continue
        field, snippet = phrase
        row = by_id[rid]
        assert snippet in row[field] and fact['need'] in active[str(rid)]['tags']
        retained.append(dict(fact, evidence=snippet, evidence_field=field, source_url=row['website'],
                             record_sha256=row['record_sha256'], verified_at='2026-11-25',
                             reviewer='Codex, November workbook evidence review'))
    facts['facts'] = retained
    report = {'source_sha256':sha, 'workbook_records':len(rows), 'tagged_records':len(active),
              'transferred_tags':transferred, 'automatically_tagged_records':automatically_tagged,
              'removed_resource_ids':sorted(old.keys()-by_id.keys()), 'withheld_tags_by_resource':omitted}
    for target, data in [('input_data/resource_tags.json',tags),('input_data/eligibility_facts.json',facts),
                         ('audits/november_transfer.json',report)]:
        (ROOT/target).write_bytes(json_bytes(data))
    print({k:v for k,v in report.items() if not isinstance(v,(list,dict))})


if __name__ == '__main__':
    main()
