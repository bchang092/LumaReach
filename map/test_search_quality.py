"""Regression checks for ranked search, tag grounding and audio boundaries."""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase, TestCase, Client
from django.core.cache import cache
from pydantic import ValidationError
from lifeline_core.repository import directory
from lifeline_core.extraction import offline_extract
from lifeline_core.ranking import rank
from lifeline_core.schemas import Extraction
from lifeline_core.service import find_resources
from lifeline_core.tag_validation import validate_tags
from scripts.resource_source import ROOT, read_source


class SearchQualityTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repo = directory()

    def test_ten_results_are_ordered_grounded_and_distinct(self):
        result = find_resources('food pantry groceries', use_llm=False)
        self.assertEqual(len(result['matches']), 10)
        scores = [m['match_score'] for m in result['matches']]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual([m['rank'] for m in result['matches']], list(range(1, 11)))
        self.assertEqual(len({m['resource']['resource_id'] for m in result['matches']}), 10)
        for m in result['matches']:
            self.assertAlmostEqual(m['match_score'], sum(m['score_breakdown'].values()), places=5)
            self.assertIn(m['reason'], m['resource']['description'])
            self.assertEqual(m['resource'], self.repo.get(m['resource']['resource_id']))

    def test_limit_and_input_bounds(self):
        self.assertEqual(len(find_resources('groceries', limit=3, use_llm=False)['matches']), 3)
        for value in [0, 11, True, '10', 2.5]:
            with self.subTest(limit=value), self.assertRaises(ValidationError):
                find_resources('groceries', limit=value, use_llm=False)
        with self.assertRaises(ValidationError):
            find_resources('   ', use_llm=False)

    def test_never_pad_unknown_eligibility(self):
        result = find_resources('groceries without ID', use_llm=False)
        self.assertEqual(result['route'], 'no_match')
        self.assertEqual(result['matches'], [])

    def test_negated_needs_and_adult_age(self):
        for text in ['I do not need groceries. I need a job.', "I don't want groceries but I need a job.", 'No necesito groceries. I need a job.']:
            result = offline_extract(text, self.repo.allowed_needs)
            self.assertNotIn('need:food.pantry', result.needs)
            self.assertIn('need:employment.training_search', result.needs)
        result = offline_extract('A 65 year old needs a doctor', self.repo.allowed_needs)
        self.assertFalse(any(c.kind == 'age' and c.value == 'child' for c in result.constraints))
        result = offline_extract('A 5 year old needs a doctor', self.repo.allowed_needs)
        self.assertTrue(any(c.kind == 'age' and c.value == 'child' for c in result.constraints))

    def test_negated_insurance_is_not_positive_coverage(self):
        result = offline_extract('I need therapy without Medicaid', self.repo.allowed_needs)
        self.assertEqual([c.value for c in result.constraints if c.kind == 'insurance'], ['uninsured'])

    def test_doctor_chip_and_nonclinical_false_positives(self):
        result = find_resources('I need help finding a doctor.', use_llm=False)
        self.assertEqual(result['route'], 'matches')
        ids = {m['resource']['resource_id'] for m in result['matches']}
        self.assertTrue(ids & {47, 49, 428, 1034, 1177, 1179, 1180})
        self.assertFalse(ids & {62, 346, 333, 345, 400, 470, 642, 799, 800, 951, 1041, 1047, 1339})
        for rid in [333, 400, 470, 642, 799, 800, 951, 1041, 1047]:
            self.assertNotIn('need:medical.general', self.repo.get(rid)['tags'])
        self.assertNotIn('need:mental_health.clinical', self.repo.get(1001)['tags'])

    def test_therapist_is_not_peer_support_or_pediatrics(self):
        result = find_resources('I want to talk with a therapist.', use_llm=False)
        self.assertEqual(len(result['matches']), 10)
        self.assertFalse({1001, 1029, 1068} & {m['resource']['resource_id'] for m in result['matches']})

    def test_general_shelter_is_not_domestic_violence_program(self):
        result = find_resources('I need a safe place to sleep tonight.', use_llm=False)
        self.assertNotIn(684, [m['resource']['resource_id'] for m in result['matches']])

    def test_doctor_diet_context_does_not_request_a_doctor(self):
        result = offline_extract('I need medically tailored meals for a diet from my doctor', self.repo.allowed_needs)
        self.assertNotIn('need:medical.general', result.needs)

    def test_zip_preserved_and_distance_origin_disclosed(self):
        extracted = offline_extract('I need groceries in Baltimore 21216', self.repo.allowed_needs)
        self.assertEqual(extracted.location, '21216')
        result = find_resources('groceries', location='21216', use_llm=False)
        self.assertTrue(all('ZIP 21216' in m['distance_origin'] for m in result['matches']))
        result = find_resources('groceries', use_llm=False)
        self.assertIn('precise location is unknown', result['matches'][0]['distance_origin'])

    def test_multineed_results_sorted_and_covered(self):
        result = find_resources('I need groceries and a job', use_llm=False)
        covered = {n for m in result['matches'] for n in m['matched_needs']}
        self.assertTrue({'need:food.pantry', 'need:employment.training_search'} <= covered)
        scores = [m['match_score'] for m in result['matches']]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_quality_preferences_and_missing_coordinates(self):
        from lifeline_core.schemas import Constraint
        a = copy.deepcopy(self.repo.get(87)); b = copy.deepcopy(a)
        a.update(resource_id=1, name='A', reliability_score=10)
        b.update(resource_id=2, name='B', reliability_score=90)
        repo = SimpleNamespace(active=[a,b], eligibility=[])
        repo.get = lambda rid: next(r for r in repo.active if r['resource_id'] == rid)
        e = Extraction(needs=['need:food.pantry'], urgency='routine', location=None,
                       constraints=[], safety='clear', language='en', follow_up=[], out_of_scope=False)
        result,_ = rank(repo,e,'groceries')
        self.assertEqual(result[0]['resource']['resource_id'],2)
        self.assertAlmostEqual(result[0]['score_breakdown']['source_reliability'], .45)
        a.update(latitude=39.2904, longitude=-76.6122)
        b.update(latitude=39.2904 + 31.5 / 69, longitude=-76.6122)
        result, _ = rank(repo, e, 'groceries')
        self.assertEqual(result[0]['resource']['resource_id'], 1)
        self.assertAlmostEqual(result[0]['score_breakdown']['location'], .5)
        # Restore equal distances before testing the preference separately.
        b['latitude'] = a['latitude']
        repo.eligibility=[{'resource_id':1,'need':'need:food.pantry','kind':'hours','value':'weekends','decision':'allows'}]
        e.constraints=[Constraint(kind='hours',value='weekends',hard=False)]
        result,_=rank(repo,e,'groceries')
        self.assertEqual(result[0]['resource']['resource_id'],1)
        a['latitude']=float('nan');b['latitude']=None
        self.assertEqual(rank(repo,e,'groceries')[0],[])


class ActiveTagValidationTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sidecar=json.loads((ROOT/'input_data/resource_tags.json').read_text())
        cls.taxonomy=json.loads((ROOT/'audits/phase1/taxonomy.json').read_text())
        _,cls.sources=read_source()

    def test_all_active_evidence_validates(self):
        validate_tags(self.sidecar,self.taxonomy,self.sources)

    def test_tampered_tags_evidence_scope_and_review_fail_closed(self):
        mutations=[lambda r:r['tags'].append('need:invented'),
                   lambda r:r['tags'].append(r['tags'][0]),
                   lambda r:r['evidence']['need:food.pantry'].update(snippet='invented'),
                   lambda r:r['evidence']['need:food.pantry'].update(context='invented'),
                   lambda r:r['evidence']['need:food.pantry'].update(scope='universal'),
                   lambda r:r['evidence']['need:food.pantry'].update(hard_filter_eligible=True),
                   lambda r:r.update(reviewer=''),lambda r:r.update(record_sha256='bad')]
        for mutate in mutations:
            changed=copy.deepcopy(self.sidecar);mutate(changed['resources']['87'])
            with self.assertRaises(ValueError):validate_tags(changed,self.taxonomy,self.sources)

    def test_corrections_preserve_sources_and_are_reproducible(self):
        report=json.loads((ROOT/'audits/phase1/nov08_service_corrections.json').read_text())
        self.assertEqual(len(report['changes']),30)
        archived=json.loads((ROOT/'input_data/archive/2026-09/resource_tags.json').read_text())
        for change in report['changes']:
            self.assertEqual(change['before']['record_sha256'],change['after']['record_sha256'])
            self.assertEqual(archived['resources'][str(change['resource_id'])],change['after'])


class VoiceApiTests(TestCase):
    audio=b'\x1aE\xdf\xa3'+b'fake synthetic test bytes'
    def setUp(self):
        cache.clear();self.client=Client(HTTP_HOST='localhost')
        env=patch.dict(os.environ,{'OPENAI_API_KEY':'test-only','VOICE_USE_API':'true'});env.start();self.addCleanup(env.stop)
    def post(self,data=None,**kwargs):
        return self.client.post('/api/transcribe/?language=en',self.audio if data is None else data,content_type='audio/webm',**kwargs)
    def test_transcription_contract_and_no_storage(self):
        with patch('openai.OpenAI') as client:
            api=client.return_value.__enter__.return_value.audio.transcriptions.create
            api.return_value=SimpleNamespace(text='I need groceries')
            response=self.post()
        self.assertEqual(response.status_code,200);self.assertEqual(response.json(),{'text':'I need groceries'})
        self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(api.call_args.kwargs['file'],('speech.webm',self.audio,'audio/webm'))
        self.assertEqual(api.call_args.kwargs['extra_body'],{'languages':['en']})
        from .models import RecommendationFeedback,ResourceTagReview
        self.assertEqual(RecommendationFeedback.objects.count()+ResourceTagReview.objects.count(),0)
    def test_disabled_without_key(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':''}),patch('openai.OpenAI') as client:
            self.assertEqual(self.post().status_code,503);client.assert_not_called()
    def test_csrf_methods_size_and_format(self):
        self.assertEqual(self.client.get('/api/transcribe/').status_code,405)
        self.assertEqual(Client(enforce_csrf_checks=True,HTTP_HOST='localhost').post('/api/transcribe/',self.audio,content_type='audio/webm').status_code,403)
        with patch('openai.OpenAI') as client:
            self.assertEqual(self.post(b'x'*2_000_001).status_code,413)
            self.assertEqual(self.post(b'not valid audio content').status_code,400)
            self.assertEqual(self.client.post('/api/transcribe/?language=bad',self.audio,content_type='audio/webm').status_code,400)
            client.assert_not_called()
    def test_outage_timeout_and_empty_transcript(self):
        with patch('openai.OpenAI',side_effect=RuntimeError('private content')):
            response=self.post();self.assertEqual(response.status_code,503);self.assertNotIn(b'private content',response.content)
        with patch('openai.OpenAI') as client:
            api=client.return_value.__enter__.return_value.audio.transcriptions.create
            for value in ['', 'x'*10001]:
                api.return_value=SimpleNamespace(text=value)
                self.assertEqual(self.post().status_code,422)
    def test_voice_rate_limit(self):
        with patch('openai.OpenAI') as client:
            client.return_value.__enter__.return_value.audio.transcriptions.create.return_value=SimpleNamespace(text='groceries')
            for _ in range(10):self.assertEqual(self.post().status_code,200)
            self.assertEqual(self.post().status_code,429)
    def test_web_limit_and_blank_validation(self):
        with patch.dict(os.environ,{'TRIAGE_USE_LLM':'false'}):
            response=self.client.post('/api/triage/',{'need_text':'groceries','limit':2},content_type='application/json')
            self.assertEqual(len(response.json()['matches']),2)
            for body in [{'need_text':'   '},{'need_text':'groceries','limit':11}]:
                self.assertEqual(self.client.post('/api/triage/',body,content_type='application/json').status_code,400)
