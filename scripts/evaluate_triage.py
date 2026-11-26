"""Reproducible development-set evaluation. Never use real resident messages.
Offline variants measure robustness, not independent clinical validation.
"""
import argparse
import concurrent.futures
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lifeline_core.service import find_resources
from lifeline_core.repository import directory


def evaluate(case,live=False,text=None):
    started=time.monotonic()
    response=find_resources(text or case['text'],use_llm=live)
    expected=set(case['expected_needs']); actual=set(response['needs'])
    crisis=case['expected_route']=='crisis'
    matches=response['matches']; repo=directory()
    grounding=all(m['resource']==repo.get(m['resource']['resource_id']) and
                  m['reason'] in m['resource']['description'] for m in matches)
    grounding=grounding and all(repo.get(r['resource_id'])==r for r in response['crisis_resources']+response['fallback_resources'])
    # Specific service relevance, independently declared in authored cases.
    relevant=[bool(set(m['matched_needs']) & expected) for m in matches[:3]]
    relevant10=[bool(set(m['matched_needs']) & expected) for m in matches[:10]]
    scores=[m['match_score'] for m in matches]
    ranked=len(matches)<=10 and scores==sorted(scores,reverse=True) and [m['rank'] for m in matches]==list(range(1,len(matches)+1))
    return {'id':case['id'],'route':response['route'],'expected_route':case['expected_route'],
      'needs':response['needs'],'expected_needs':case['expected_needs'],
      'category_exact':actual==expected,'category_recall':len(actual&expected)/len(expected) if expected else float(not actual),
      'safe_crisis':not crisis or response['route']=='crisis' and not matches and len(response['crisis_resources'])>=2,
      'grounded':grounding,'mode':response['extraction_mode'],
      'top_ids':[m['resource']['resource_id'] for m in matches],
      'precision_at_3_service_proxy':sum(relevant)/len(relevant) if relevant else None,
      'precision_at_10_service_proxy':sum(relevant10)/len(relevant10) if relevant10 else None,
      'ranked_and_bounded':ranked,
      'elapsed_ms':round((time.monotonic()-started)*1000,1)}


def summarize(rows):
    relevant=[x['precision_at_3_service_proxy'] for x in rows if x['precision_at_3_service_proxy'] is not None]
    relevant10=[x['precision_at_10_service_proxy'] for x in rows if x['precision_at_10_service_proxy'] is not None]
    crisis=[x for x in rows if x['expected_route']=='crisis']
    return {'inputs':len(rows),'exact_category_accuracy':sum(x['category_exact'] for x in rows)/len(rows),
      'mean_category_recall':sum(x['category_recall'] for x in rows)/len(rows),
      'exact_route_accuracy':sum(x['route']==x['expected_route'] for x in rows)/len(rows),
      'crisis_inputs':len(crisis),'crisis_passed':sum(x['safe_crisis'] for x in crisis),
      'grounding_passed':sum(x['grounded'] for x in rows),
      'returned_matches':len(relevant),'mean_precision_at_3_service_proxy':sum(relevant)/len(relevant) if relevant else None,
      'mean_precision_at_10_service_proxy':sum(relevant10)/len(relevant10) if relevant10 else None,
      'ranked_and_bounded_passed':sum(x['ranked_and_bounded'] for x in rows),
      'abstentions':sum(x['route']=='no_match' for x in rows),
      'modes':{mode:sum(x['mode']==mode for x in rows) for mode in sorted(set(x['mode'] for x in rows))},
      'failures':[{'id':x['id'],'needs':x['needs'],'expected_needs':x['expected_needs'],'route':x['route'],'expected_route':x['expected_route']} for x in rows if not x['category_exact'] or not x['safe_crisis'] or not x['grounded'] or x['route']!=x['expected_route']]}


def variants(case):
    text=case['text']
    # 40 perturbations per authored case, generated reproducibly without changing intent.
    for prefix in ('','please help. ','hey, ','hello. ','can you help? '):
        for variant in (text,text.upper(),text.lower(),'  '+text+'  ',text.replace(' ','  '),text.replace("'",'’'),text+' please',text+'\nthanks'):
            yield prefix+variant


def main():
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--variants',action='store_true');p.add_argument('--cases',default='evaluation/triage_cases.json');p.add_argument('--output',required=True);args=p.parse_args()
    cases=json.loads((ROOT/args.cases).read_text())['cases']
    directory()
    # Warm semantic index before parallel extraction calls.
    find_resources('food pantry groceries',use_llm=False)
    tasks=[(c,t) for c in cases for t in (variants(c) if args.variants else [c['text']])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4 if args.live else 1) as pool:
        rows=list(pool.map(lambda item:evaluate(item[0],args.live,item[1]),tasks))
    live_validated=args.live and all(x['mode'] in ('llm','safety_first') for x in rows)
    report={'source_sha256':directory().source_sha256,'live_llm_requested':args.live,'live_model_validated':live_validated,
       'interpretation':'Service-tag precision is an automated proxy, not caseworker-adjudicated eligibility or successful referrals. No-match may be correct when hard constraints are unverified. Variants are not independent cases.',
       'summary':summarize(rows),'results':rows}
    (ROOT/args.output).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['summary'],indent=2))
    if args.live and not live_validated:sys.exit(2)
    if any(not x['safe_crisis'] or not x['grounded'] or not x['ranked_and_bounded'] for x in rows):sys.exit(1)

if __name__=='__main__':main()
