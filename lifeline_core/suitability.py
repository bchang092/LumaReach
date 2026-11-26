"""Description-supported service qualifiers that broad tags cannot express.
These are relevance gates, not statements about eligibility. They intentionally
abstain when a specific requested service is absent from the description.
"""
import re
from functools import cache
from .safety import normalize


def query_matcher(query):
    # Only the returned function owns this cache. It expires with the search.
    @cache
    def matches(pattern):
        return bool(re.search(pattern, query))
    return matches


def suitable(record,need,text):
    return suitable_normalized(normalize(record['description']), need, query_matcher(normalize(text)))


def suitable_normalized(description, need, query_matches):
    # Special-purpose organizations cannot be presented as general-access programs.
    contexts=[(r'domestic (violence|abuse)',r'violence|abuse|survivor|unsafe|partner'),
              (r'for veterans|helps veterans|services.{0,15}veterans|\bva (?:outpatient|medical center)\b|department of veterans affairs|veteran-focused',r'\bvet\b|veteran|military'),
              (r'affected by cancer',r'cancer|chemo|oncology'),
              (r'cycles of violence|affected by violence',r'violence|abuse|survivor|unsafe|partner'),
              (r'for children, youth, and families',r'child|kid|family|teen|youth'),
              (r'(refugee|immigrant|resettlement)',r'refugee|immigra|inmigra|asylum|newcomer'),
              (r'(intellectual|developmental) disabilit|\bidd\b',r'disabilit|autism|developmental'),
              (r'survivors of|crime victims|intimate partner violence',r'abus|violence|survivor|victim|partner|unsafe'),
              (r'people experiencing homelessness',r'homeless|no place to|without housing'),
              (r'for returning citizens|for ex.offenders',r'prison|reentry|jail|returning citizen')]
    for offered,requested in contexts:
        if re.search(offered,description) and not query_matches(requested): return False
    if re.search(r'washington,? dc|dc area|capitol heights',description) and not query_matches(r'washington|\bdc\b|capitol heights'): return False
    if need=='need:housing.rent_eviction_help' and query_matches(r'evict|court|desalojo'):
        return bool(re.search(r'evict|rent arrears|emergency rent|rental assistance program',description))
    if need=='need:immigration.support' and query_matches(r'lawyer|asylum|legal|abogado'):
        return bool(re.search(r'legal|attorney|asylum|lawyer',description))
    if re.search(r'pediatric|for children and families|for children, youth',description) and not re.search(r'adults|all ages|across the lifespan',description):
        if not query_matches(r'child|kid|baby|son|daughter|teen|youth|pediatric'): return False
    if need=='need:medical.general' and query_matches(r'doctor|primary care|medico'):
        if re.search(r'primary care for people living with hiv', description) and not query_matches('hiv'):
            return False
        return bool(re.search(r'primary (medical |health)?care|family medicine|general practitioner|medical clinic|physician office',description))
    if need=='need:mental_health.clinical' and query_matches(r'therap|counsel|terapeuta'):
        return bool(re.search(r'therap|counsel',description))
    if need=='need:food.pantry':
        # Public pantry already required by the evidence scope in ranking.
        return True
    if need=='need:pets.food_veterinary' and query_matches(r'food|comida'):
        return bool(re.search(r'pet food|food pantry|pet supplies',description))
    if need=='need:benefits.enrollment_navigation':
        if query_matches(r'snap|food stamp'): return bool(re.search(r'snap|food stamp',description))
        if query_matches(r'health insurance|medicaid|medicare'): return bool(re.search(r'health (benefit|insurance)|medicaid|medicare|health coverage',description))
    if need in {'need:legal.assistance', 'need:legal.housing_disputes', 'need:legal.immigration'}:
        if query_matches(r'evict|rent|desalojo'): return bool(re.search(r'evict|tenant|housing|landlord|foreclos',description))
        if query_matches(r'immigra|inmigra|asylum'): return bool(re.search(r'immigra|asylum',description))
    if need=='need:housing.emergency_shelter':
        return bool(re.search(r'emergency shelter|overnight|temporary shelter|shelter services|provides shelter|including shelter',description))
    if need=='need:housing.supportive_transitional':
        if query_matches(r'sober|recovery'): return bool(re.search(r'sober|recovery hous|transitional hous',description))
    if need=='need:transportation.assistance':
        if query_matches(r'interview|\bjob\b|bus'):
            return bool(re.search(r'bus pass|bus token|transit pass|employment.{0,30}transport|transport.{0,30}employment',description))
        if query_matches(r'chemo|medical|doctor|hospital'):
            return bool(re.search(r'medical transport|patient transport|transport.{0,30}appointment|ride.{0,30}cancer',description))
    if need=='need:care.home' and query_matches(r'nurse|nursing'):
        return bool(re.search(r'skilled nursing|nurse.led|nursing care',description))
    if need=='need:mental_health.peer_support' and query_matches(r'grief|bereavement'):
        return bool(re.search(r'grief|bereavement',description))
    if need=='need:substance_use.medications' and query_matches(r'suboxone|buprenorphine'):
        return bool(re.search(r'suboxone|buprenorphine',description))
    if need=='need:essentials.clothing_supplies' and query_matches(r'diaper|panales'):
        return bool(re.search(r'diaper|infant supplies|baby supplies',description))
    if need=='need:childcare.early_learning':
        return bool(re.search(r'childcare|child care|early (learning|childhood)|day ?care|head start',description)) and not bool(re.search(r'gym|fitness|while.*workout|adult (medical )?day ?care',description))
    return True
