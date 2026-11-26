"""Grounded service gates followed by an explainable, deterministic ranking.

Scores compare candidates for this request; they are not quality probabilities.
Only public descriptions are indexed. Intake text is never retained in the index.
"""
from functools import lru_cache
import math
import re
from statistics import median

from .safety import normalize
from .suitability import query_matcher, suitable_normalized


def eligible(record, need, constraints, facts):
    unknown = []
    for c in constraints:
        if not c.hard:
            continue
        scoped = [f for f in facts if f['resource_id'] == record['resource_id'] and
                  f['need'] == need and f['kind'] == c.kind and f['value'].casefold() == c.value.casefold()]
        if any(f['decision'] == 'excludes' for f in scoped):
            return False, []
        if not any(f['decision'] == 'allows' for f in scoped):
            unknown.append(c.kind + ': ' + c.value)
    return not unknown, unknown


def coordinates(record):
    try:
        lat, lon = float(record['latitude']), float(record['longitude'])
        if math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    except (TypeError, ValueError, KeyError):
        pass
    return None


def miles(point, origin):
    return math.hypot((point[0] - origin[0]) * 69, (point[1] - origin[1]) * 53.4)


def origin_for(directory, location):
    # A directory-address midpoint is only an approximation, never GPS/travel time.
    zip_match = re.search(r'\b21\d{3}\b', location or '')
    if zip_match:
        points = [coordinates(r) for r in directory.active if
                  re.search(r'\b' + zip_match[0] + r'\b', str(r.get('address', '')))]
        points = [p for p in points if p and miles(p, (39.2904, -76.6122)) <= 35]
        if points:
            return (median(p[0] for p in points), median(p[1] for p in points)), 'Approximate directory midpoint for ZIP ' + zip_match[0]
    return (39.2904, -76.6122), 'Central Baltimore (your precise location is unknown)'


def number(value):
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else 0
    except (TypeError, ValueError):
        return 0


# Only public workbook descriptions enter this bounded cache.
normalized_description = lru_cache(maxsize=2048)(normalize)


def proximity_and_rating(distance, record):
    return (0.5 * max(0, 1 - distance / 35),
            0.5 * min(1, max(0, number(record.get('reliability_score')) / 100)))


def provider_location(record):
    return tuple(re.sub(r'\W+', '', str(record.get(k, '')).casefold()) for k in ('name', 'address'))


def rank(directory, extraction, text, limit=10, constraint_scopes=None, priority_lists=None):
    query = query_matcher(normalize(text.replace('’', "'")))
    origin, origin_label = origin_for(directory, extraction.location)
    constraint_scopes = constraint_scopes or {}
    requirements = {
        need: [c for c in extraction.constraints
               if need in constraint_scopes.get((c.kind, c.value), {need})]
        for need in extraction.needs
    }
    candidates = []
    leads = {need: [] for need in requirements}
    for r in directory.active:
        point = coordinates(r)
        if point is None or miles(point, (39.2904, -76.6122)) > 35:
            continue

        supported = []
        for need in requirements:
            fact = r['evidence'].get(need)
            if not fact or fact['scope'] != 'described_service':
                continue
            allowed, unknown = eligible(r, need, requirements[need], directory.eligibility)
            if not allowed and (priority_lists is None or not unknown):
                continue
            if not suitable_normalized(normalized_description(r["description"]), need, query):
                continue
            if allowed:
                supported.append(need)
            else:
                distance = miles(point, origin)
                score = proximity_and_rating(distance, r)
                leads[need].append((sum(score), r['resource_id'], distance, unknown))
        if not supported:
            continue
        distance = miles(point, origin)
        prefs = [c for c in extraction.constraints if not c.hard]
        supported_prefs = [c for c in prefs if any(
            eligible(r, need, [c.model_copy(update={'hard': True})], directory.eligibility)[0]
            for need in supported)]
        proximity, rating = proximity_and_rating(distance, r)
        factors = {
            'service_fit': len(supported) * 3.0,
            'supported_preferences': len(supported_prefs) / max(1, len(prefs)),
            'location': proximity,
            'source_reliability': rating,
        }
        factors = {k: round(v, 6) for k, v in factors.items()}
        candidates.append({'score': round(sum(factors.values()), 6), 'record': r,
                           'needs': supported, 'factors': factors, 'distance': distance})
    candidates.sort(key=lambda c: (-c['score'], c['record']['resource_id']))
    # Deduplicate identical provider locations, not distinct services in one building.
    unique = []
    seen = set()
    for c in candidates:
        key = provider_location(c['record'])
        if key not in seen:
            seen.add(key)
            unique.append(c)
    if priority_lists is not None:
        # Deduplicate within each service. A provider may offer different
        # services at the same address in separate workbook records.
        seen_by_need = {need: set() for need in requirements}
        for candidate in candidates:
            record = candidate['record']
            for need in candidate['needs']:
                group = priority_lists[need]
                if len(group) >= limit:
                    continue
                key = provider_location(record)
                if key in seen_by_need[need]:
                    continue
                seen_by_need[need].add(key)
                group.append({
                    'resource_id': record['resource_id'],
                    'distance_miles_approx': round(candidate['distance'], 1),
                    'distance_origin': origin_label,
                    'match_score': candidate['score'],
                })
        # For a need with no confirmed match, show a few relevant contacts
        # separately, with the exact requirements the workbook cannot verify.
        for need, options in leads.items():
            if priority_lists[need]:
                continue
            for score, rid, distance, unknown in sorted(options, key=lambda row: (-row[0], row[1])):
                key = provider_location(directory.records[rid])
                if key in seen_by_need[need]:
                    continue
                seen_by_need[need].add(key)
                priority_lists[need].append({
                    'resource_id': rid, 'distance_miles_approx': round(distance, 1),
                    'distance_origin': origin_label, 'unverified_requirements': unknown,
                })
                if len(priority_lists[need]) >= min(3, limit):
                    break
    # Reserve coverage for multiple needs, then sort the chosen set by actual score.
    chosen = []
    covered = set()
    for need in extraction.needs:
        if need in covered or len(chosen) >= limit:
            continue
        item = next((c for c in unique if need in c['needs']), None)
        if item is not None and item not in chosen:
            chosen.append(item)
            covered.update(item['needs'])
    for item in unique:
        if len(chosen) >= limit:
            break
        if item not in chosen:
            chosen.append(item)
    chosen.sort(key=lambda c: (-c['score'], c['record']['resource_id']))
    results = []
    covered = set()
    for position, c in enumerate(chosen, 1):
        r, needs = c['record'], c['needs']
        covered.update(needs)
        evidence = r['evidence'][needs[0]]
        results.append({
            'resource': directory.get(r['resource_id']), 'rank': position,
            'match_score': c['score'], 'score_breakdown': c['factors'],
            'matched_needs': needs, 'reason': evidence['context'][:240],
            'evidence_snippet': evidence['snippet'],
            'distance_miles_approx': round(c['distance'], 1), 'distance_origin': origin_label,
            'eligibility': 'supported_by_scoped_source_evidence' if any(c.hard for need in needs for c in requirements[need]) else 'not_assessed',
            'next_step': 'Contact the provider to confirm intake, availability and program eligibility.',
        })
    return results, [n for n in extraction.needs if n not in covered]
