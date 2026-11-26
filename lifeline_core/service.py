import os
import re
from .schemas import Intake
from .safety import safety_status
from .repository import directory, SafetyDirectory
from .extraction import extract, local_constraint_scopes
from .ranking import rank

QUESTIONS={
 'need':('What would you most like help with?','¿Con qué necesita más ayuda?'),
 'food_type':('Do you need groceries to cook, ready-to-eat meals, or food delivery?','¿Necesita alimentos para cocinar, comidas preparadas o entrega de comida?'),
 'location':('What ZIP code or neighborhood do you need help in?','¿En qué código postal o vecindario necesita ayuda?'),
 'diet':('What food requirements should we look for?','¿Qué requisitos alimentarios debemos buscar?'),
 'safety':('Are you or someone else in danger right now?','¿Usted u otra persona está en peligro ahora?'),
 'eligibility':('Which program requirement matters most for you?','¿Qué requisito del programa es más importante para usted?'),
}


def crisis_result(repo):
    return {'route':'crisis','matches':[],'crisis_resources':repo.safety_records(), 'fallback_resources':[],
      'questions':[], 'needs':[], 'unmet_needs':[], 'extraction_mode':'safety_first',
      'message':'If there is immediate danger or a medical emergency, contact emergency services now. These crisis contacts can help. / Si hay peligro inmediato o una emergencia médica, contacte a emergencias ahora.','language':'en'}


def find_resources(need_text="", location=None, constraints=None, *, selected_needs=None, limit=10, use_llm=None, repo=None):
    request=Intake(need_text=need_text,location=location,constraints=constraints or [],selected_needs=selected_needs or [],limit=limit)
    # Check all text fields before any model call or normal retrieval.
    safety_text=request.need_text+' '+(request.location or '')+' '+' '.join(c.value for c in request.constraints)
    status=safety_status(safety_text)
    if status=='crisis': return crisis_result(repo or SafetyDirectory())
    repo=repo or directory()
    use_llm = os.environ.get('TRIAGE_USE_LLM', 'true').lower() == 'true' and use_llm is not False
    extraction, mode = extract(request.need_text, repo.allowed_needs, use_llm=bool(request.need_text and use_llm))
    if request.selected_needs:
        extraction.needs = list(dict.fromkeys([*request.selected_needs, *extraction.needs]))
        answered = {'need'}
        if set(request.selected_needs) & {'need:food.pantry', 'need:food.prepared_meals'}:
            answered.add('food_type')
            if 'need:food.general_assistance' in extraction.needs:
                extraction.needs.remove('need:food.general_assistance')
        extraction.follow_up = [q for q in extraction.follow_up if q not in answered]
        if not request.need_text:
            mode = 'structured'
    if extraction.safety=='crisis': return crisis_result(repo)
    if request.location: extraction.location=request.location
    # Explicit constraints are authoritative; an LLM cannot loosen them.
    merged={(c.kind,c.value.casefold()):c for c in extraction.constraints}
    merged.update({(c.kind,c.value.casefold()):c for c in request.constraints})
    extraction.constraints=list(merged.values())
    base={'route':'no_match','matches':[], 'crisis_resources':[], 'fallback_resources':repo.safety_records(False),
          'questions':[], 'needs':extraction.needs,'unmet_needs':extraction.needs,'extraction_mode':mode,
          'language':extraction.language,'message':''}
    if status=='uncertain' or extraction.safety=='uncertain':
        base.update(route='follow_up',questions=[QUESTIONS['safety'][extraction.language=='es']],crisis_resources=repo.safety_records(),message='Please check immediate safety first. / Primero confirme su seguridad.')
        return base
    # Outside-region requests do not become false local matches. Unknown location
    # names are retained only in memory; ask the user to confirm the service region.
    location=extraction.location or ''
    local=not location or bool(re.search(r'(?i)baltimore|maryland|\bmd\b|\b21\d{3}\b',location))
    if not local:
        base.update(route='follow_up',questions=['Do you need services in Baltimore City or Baltimore County?'],message='This directory covers the Baltimore area.')
        if re.search(r'(?i)tokyo|london|california|new york|outside maryland',location):
            base.update(route='no_match',questions=[],message='This directory cannot confirm services in that area.')
        return base
    if extraction.out_of_scope:
        base['message']='This directory cannot help with that request. A caseworker can help identify an appropriate service.'
        return base
    if extraction.follow_up or not extraction.needs:
        base.update(route='follow_up',questions=[QUESTIONS[q][extraction.language=='es'] for q in (extraction.follow_up or ['need'])][:2],message='A little more detail will help narrow this down.' if extraction.language=='en' else 'Un poco más de información ayudará a encontrar recursos.')
        return base
    scopes = {}
    if mode in {'local', 'local_fallback'}:
        scopes = local_constraint_scopes(extraction)
        for constraint in request.constraints:
            scopes.pop((constraint.kind, constraint.value), None)
    # Start with selected services, then immediate shelter and meals, followed
    # by the remaining needs in extraction order. Empty groups remain visible.
    order = dict.fromkeys([*request.selected_needs, 'need:housing.emergency_shelter',
                           'need:food.prepared_meals', *extraction.needs])
    priorities = {need: [] for need in order if need in extraction.needs}
    matches,unmet=rank(repo,extraction,request.need_text,limit=request.limit, constraint_scopes=scopes, priority_lists=priorities)
    # Existing matches already carry their provider record. Send each extra
    # public-facing record only once, even if it serves several priorities.
    existing = {item['resource']['resource_id'] for item in matches}
    sources = {}
    for need, entries in priorities.items():
        for entry in entries:
            rid = entry['resource_id']
            record = repo.records[rid]
            entry['reason'] = record['evidence'][need]['context'][:240]
            if rid not in existing and str(rid) not in sources:
                sources[str(rid)] = {field: record.get(field) for field in (
                    'resource_id', 'name', 'address', 'phone', 'phone_link', 'website',
                    'display_description', 'description', 'restrictions', 'hours',
                    'reliability_score', 'classification', 'verified_date')}
    base.update(priorities=[{'need': need, 'sources': entries} for need, entries in priorities.items()],
                additional_sources=sources)
    base.update(matches=matches,unmet_needs=unmet,
        result_limit=request.limit,
        ranking_policy='Service fit and supported preferences first. Source reliability and approximate proximity carry equal weight. Scores are relative, not eligibility probabilities.',
        directory_coverage={'active_records':len(repo.active),
                            'pending_review':0,
                            'without_service_tags':sum(r.get('tag_status')=='no_active_service_tags' for r in repo.records.values())})
    if matches:
        base.update(route='matches',message='These descriptions match your needs. Confirm program eligibility and availability with the provider.' if extraction.language=='en' else 'Estas descripciones coinciden con sus necesidades. Confirme los requisitos y la disponibilidad con el proveedor.')
    else:
        base['message']='I could not confirm a resource that fits your needs and requirements. A caseworker or 211 can help check options.' if extraction.language=='en' else 'No pude confirmar un recurso que cumpla sus necesidades y requisitos. Un trabajador social o 211 puede ayudar.'
    return base
