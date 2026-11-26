"""Phase 1 tests. No migration CLI, live sidecar, SQL or workbook writes."""
import base64
import copy
import json
from pathlib import Path
import unittest

from resource_source import SEPTEMBER_MASTER as MASTER, ROOT, digest, json_bytes, read_source
from tag_audit_rules import propose, matches, NEEDS, CONSTRAINTS
from tag_migration import plan, parse_json, rollback_plan


class ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sha,cls.sources = read_source(MASTER)
        directory = ROOT/'audits/phase1'
        cls.review = parse_json((directory/'resource_tag_proposals.json').read_bytes())
        cls.taxonomy = parse_json((directory/'taxonomy.json').read_bytes())
        cls.rows = {r['resource_id']:r for r in cls.review['resources']}

    def test_complete_coverage_and_source_preservation(self):
        self.assertEqual(self.review['source_sha256'],self.sha)
        self.assertEqual(len(self.rows),1362)
        self.assertEqual(set(self.rows),set(range(1,1363)))
        for source in self.sources:
            with self.subTest(resource=source['resource_id']):
                row = self.rows[source['resource_id']]
                self.assertEqual(row['source'],source)
                self.assertFalse(row['approved'])
                self.assertEqual(row['old_tags'],[])
                self.assertEqual(propose(source,corrections=False),row)

    def test_current_proposals_preserve_reviewed_corrections(self):
        report=parse_json((ROOT/'audits/phase1/nov08_service_corrections.json').read_bytes())
        sources={s['resource_id']:s for s in self.sources}
        for change in report['changes']:
            proposed=propose(sources[change['resource_id']])
            removed=set(change['before']['tags'])-set(change['after']['tags'])
            self.assertFalse(removed & set(proposed['new_tags']))
            for tag,fact in change['after']['evidence'].items():
                before=change['before']['evidence'].get(tag)
                if before and fact['scope']!=before['scope']:
                    self.assertEqual(proposed['evidence'][tag]['scope'],fact['scope'])
        for rid in (487,581):
            self.assertNotIn('need:childcare.early_learning',propose(sources[rid])['new_tags'])

    def test_all_tags_have_exact_evidence_and_no_implicit_hard_constraints(self):
        observed = set()
        for row in self.rows.values():
            self.assertEqual(set(row['new_tags']),set(row['evidence']))
            self.assertEqual(len(row['new_tags']),len(set(row['new_tags'])))
            for tag,e in row['evidence'].items():
                observed.add(tag)
                with self.subTest(resource=row['resource_id'],tag=tag):
                    self.assertEqual(row['source'][e['field']][e['start']:e['end']],e['snippet'])
                    self.assertIn(e['context'],row['source'][e['field']])
                    self.assertIs(e['hard_filter_eligible'],False)
                    if tag.startswith('need:'):
                        self.assertEqual(e['field'],'description')
        self.assertEqual(observed,{t['tag'] for t in self.taxonomy['tags']})

    def test_every_unclassified_record_is_flagged_low_confidence(self):
        for row in self.rows.values():
            if not any(t.startswith('need:') for t in row['new_tags']):
                self.assertTrue(row['review_flag'])
                self.assertEqual(row['confidence'],'low')

    def test_food_specificity_real_records(self):
        expected = {
            35:({'need:food.delivery','need:food.medically_tailored'},{'need:food.pantry'}),
            41:({'need:food.pantry'},{'need:food.delivery'}),
            79:({'need:food.pantry','food.client_choice_reported'},set()),
            144:({'need:food.delivery','food.drive_through_reported'},set()),
            205:({'need:food.prepared_meals'},{'need:food.pantry'}),
            1083:({'need:food.delivery'},{'need:food.pantry'}),
            1110:({'need:food.delivery','need:food.medically_tailored','food.frozen_items_reported'},set()),
            1344:({'need:pets.food_veterinary'},{'need:food.pantry'}),
        }
        for rid,(required,excluded) in expected.items():
            with self.subTest(resource=rid):
                tags = set(self.rows[rid]['new_tags'])
                self.assertTrue(required<=tags,(rid,required-tags))
                self.assertFalse(excluded & tags)

    def test_resident_meals_and_transport_are_not_public_services(self):
        for rid in (221,223,229,300,324,741):
            with self.subTest(resource=rid):
                self.assertFalse(any(t.startswith('need:food.') for t in self.rows[rid]['new_tags']))
        self.assertEqual(self.rows[221]['evidence']['need:transportation.assistance']['scope'],'enrolled_clients_or_residents')
        self.assertEqual(self.rows[55]['evidence']['need:food.prepared_meals']['scope'],'enrolled_clients_or_residents')

    def test_distinct_care_financial_and_legal_services(self):
        self.assertIn('need:care.respite',self.rows[332]['new_tags'])
        self.assertNotIn('need:care.hospice_palliative',self.rows[332]['new_tags'])
        self.assertIn('need:care.hospice_palliative',self.rows[1341]['new_tags'])
        self.assertIn('need:financial.tax_help',self.rows[32]['new_tags'])
        self.assertNotIn('need:financial.tax_help',self.rows[781]['new_tags'])
        self.assertIn('need:legal.criminal_defense',self.rows[1127]['new_tags'])
        self.assertIn('need:legal.immigration',self.rows[1132]['new_tags'])
        self.assertNotIn('need:legal.criminal_defense',self.rows[1132]['new_tags'])

    def test_names_categories_and_related_words_do_not_imply_services(self):
        for rid in (1,73,90,181,269,311,541,776,1055,1173,1305,1307,1308):
            with self.subTest(resource=rid):
                self.assertEqual(self.rows[rid]['new_tags'],[])
        self.assertNotIn('need:medical.general',self.rows[809]['new_tags'])
        self.assertNotIn('language.spanish_reported',self.rows[30]['new_tags'])
        self.assertNotIn('cost.free_program_reported',self.rows[292]['new_tags'])
        self.assertNotIn('need:mental_health.clinical',self.rows[1127]['new_tags'])

    def test_crisis_sources_preserve_scraped_reliability(self):
        row = self.rows[3]
        self.assertIn('need:crisis.intervention',row['new_tags'])
        self.assertEqual(row['source']['protected_metadata']['Classification'],'Low Reliability')
        self.assertEqual(row['source']['protected_metadata']['Reliability Score'],46.87317256)

    def test_closed_sources_flagged(self):
        for rid in (217,298,303,328,652,1273):
            self.assertIn('needs_human_review:operating_status',self.rows[rid]['review_reasons'])

    def test_evaluation_cases_are_unique_and_use_supported_taxonomy(self):
        corpus=parse_json((ROOT/'evaluation/triage_cases.json').read_bytes())
        cases=corpus['cases']
        self.assertGreaterEqual(len(cases),40)
        self.assertEqual(len(cases),len({c['id'] for c in cases}))
        allowed={t['tag'] for t in self.taxonomy['tags']}
        for case in cases:
            self.assertTrue(set(case['expected_needs'])<=allowed,case['id'])
            if case['expected_route']=='crisis':
                self.assertIs(case['normal_matches_allowed'],False)

    def test_typo_proposals_match_original_text_without_changing_source(self):
        corrections=parse_json((ROOT/'audits/phase1/display_corrections.json').read_bytes())
        self.assertEqual(corrections['source_sha256'],self.sha)
        for correction in corrections['corrections']:
            desc=self.rows[correction['resource_id']]['source']['description']
            self.assertEqual(desc.count(correction['old_text']),1)
        self.assertEqual(digest(MASTER.read_bytes()),self.sha)

    def test_every_proposal_validates_in_pure_planner_after_simulated_review(self):
        # This only constructs a return value in memory; does not apply tags or
        # mark the on-disk proposal approved. Human approval is still required.
        approved = copy.deepcopy(self.review)
        for row in approved['resources']:
            row.update(approved=True,review_flag=False,review_reasons=[],
                       reviewer='TEST FIXTURE ONLY',reviewed_at='2026-10-24T12:00:00-04:00')
        sidecar,count = plan(approved,self.taxonomy,self.sha,self.sources)
        self.assertEqual(count,1362)
        self.assertEqual(len(sidecar['resources']),1362)
        self.assertEqual(digest(MASTER.read_bytes()),self.sha)


class RuleRegressionTests(unittest.TestCase):
    def test_2000_negation_case_punctuation_variants(self):
        # 2,000 rule assertions, not 2,000 independently authored need prompts.
        phrases = ['food pantry','food distribution','primary care','mental health services','legal assistance']
        for i in range(2000):
            phrase = phrases[i%len(phrases)]
            prefix = ['No ','Does not provide ','We do not offer ','No documented '][(i//5)%4]
            text = prefix+phrase+['.',';','\n','!'][(i//20)%4]
            if i%2:
                text=text.upper()
            rx = next(pattern for pattern in NEEDS.values() if matches(phrase,pattern,'description'))
            with self.subTest(variant=i):
                self.assertEqual(matches(text,rx,'description'),[])

    def test_postposed_negation(self):
        self.assertEqual(matches('Food pantry is not available.',NEEDS['food.pantry'],'description'),[])

    def test_unknown_requirements_not_positive(self):
        for text in ('No referral required.','No photo ID required.','Medicaid is not accepted.'):
            for key in ('access.referral_required_reported','documents.requirements_reported','insurance.medicaid_reported'):
                self.assertEqual(matches(text,CONSTRAINTS[key],'restrictions'),[])

    def test_nonprofit_is_not_negation(self):
        self.assertTrue(matches('A not-for-profit clinic provides primary care.',NEEDS['medical.general'],'description'))

    def test_source_name_and_category_invariance(self):
        base={'resource_id':99999,'name':'Food Bank Emergency Clinic','old_category':'Food & Essential Needs',
              'description':'No specific services are documented.','restrictions':'','hours':''}
        self.assertEqual(propose(base)['new_tags'],[])
        base.update(name='Anything else',old_category='Physical & General Health Care')
        self.assertEqual(propose(base)['new_tags'],[])


class MigrationValidationTests(unittest.TestCase):
    def setUp(self):
        _,sources=read_source(MASTER)
        self.source=next(r for r in sources if r['resource_id']==41)
        self.row=copy.deepcopy(propose(self.source))
        self.row.update(approved=True,review_flag=False,review_reasons=[],reviewer='TEST ONLY',reviewed_at='2026-10-24T12:00:00-04:00')
        self.review={'schema_version':1,'source_sha256':'fixture','taxonomy_version':'test','resources':[self.row]}
        self.taxonomy={'version':'test','tags':[{'tag':t} for t in self.row['new_tags']]}

    def planning(self):
        return plan(self.review,self.taxonomy,'fixture',[self.source])

    def test_valid_plan_does_not_mutate_input(self):
        before=copy.deepcopy(self.review)
        sidecar,count=self.planning()
        self.assertEqual(count,1)
        self.assertEqual(self.review,before)
        self.assertEqual(sidecar['resources']['41']['tags'],self.row['new_tags'])

    def test_rejects_unapproved_flagged_stale_and_tampered_records(self):
        mutations=[
            lambda:self.row.update(approved=False),
            lambda:self.row.update(approved='true'),
            lambda:self.row.update(review_flag=True),
            lambda:self.row.update(review_reasons=['unresolved']),
            lambda:self.row.update(reviewer=''),
            lambda:self.row.update(reviewed_at='2026-10-24T12:00:00'),
            lambda:self.row.update(old_tags=['unknown']),
            lambda:self.review.update(source_sha256='stale'),
            lambda:self.review.update(taxonomy_version='stale'),
            lambda:self.row.update(name='fabricated'),
            lambda:self.row['source'].update(description='tampered'),
            lambda:self.row['new_tags'].append('need:invented'),
            lambda:self.row['new_tags'].append(self.row['new_tags'][0]),
            lambda:self.row['evidence'].clear(),
            lambda:self.review['resources'].append(copy.deepcopy(self.row)),
            lambda:self.review.update(resources=[]),
            lambda:self.row.update(resource_id=True),
        ]
        for mutation in mutations:
            self.setUp()
            mutation()
            with self.subTest(mutation=mutations.index(mutation)),self.assertRaises(ValueError):
                self.planning()

    def test_rejects_bad_evidence_and_hard_eligibility(self):
        for field,value in [('snippet','invented'),('start',-1),('end',999999),('field','name'),('scope','global'),('hard_filter_eligible',True)]:
            self.setUp()
            tag=self.row['new_tags'][0]
            self.row['evidence'][tag][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.planning()

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):parse_json('{"approved":false,"approved":true}')

    def test_stale_and_unknown_existing_sidecar_are_rejected(self):
        previous,_=self.planning()
        self.row['old_tags']=list(self.row['new_tags'])
        valid,count=plan(self.review,self.taxonomy,'fixture',[self.source],previous)
        self.assertEqual(valid,previous)
        self.assertEqual(count,1)
        for variant in ('id','hash','tag'):
            bad=copy.deepcopy(previous)
            if variant=='id':bad['resources']['999999']=bad['resources'].pop('41')
            elif variant=='hash':bad['resources']['41']['record_sha256']='stale'
            else:bad['resources']['41']['tags']=['need:invented']
            with self.subTest(variant=variant),self.assertRaises(ValueError):
                plan(self.review,self.taxonomy,'fixture',[self.source],bad)

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ValueError):parse_json('{"value":NaN}')

    def test_rollback_new_and_existing_sidecar(self):
        target=ROOT/'input_data/resource_tags.json'
        current=b'new tags'
        for old in (None,b'original tags'):
            backup={'schema_version':1,'target':str(target.resolve()),'after_sha256':digest(current),
                    'before_sha256':None if old is None else digest(old),
                    'before_base64':None if old is None else base64.b64encode(old).decode()}
            self.assertEqual(rollback_plan(backup,target,current),old)
            with self.assertRaises(ValueError):rollback_plan(backup,target,b'newer human edits')
            with self.assertRaises(ValueError):rollback_plan(backup,ROOT/'wrong.json',current)
            backup['before_sha256']='corrupt'
            with self.assertRaises(ValueError):rollback_plan(backup,target,current)


if __name__=='__main__':
    unittest.main(verbosity=2)
