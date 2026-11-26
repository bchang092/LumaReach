"""Conservative, multilingual first pass. No keyword system covers all crises.
Present danger always wins over a historical/negated clause elsewhere.
"""
import re
import unicodedata


def normalize(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()
    text = re.sub(r"[’']", '', text)
    return re.sub(r'\s+', ' ', text).strip()


DANGER = [
    r'\b(end(?:ing)?|tak(?:e|ing)) (my|your|his|her|their) (own )?life\b',
    r'\b(hurt(?:ing)?|harm(?:ing)?|cut(?:ting)?) (myself|herself|himself|themselves)\b',
    r'\b(choking|strangl\w*|heart attack|seizure|face drooping)\b',
    r'\b(touching|touches|molesting|sexually abusing) me\b',
    r'\b(kill|murder|hurt) (me|my child|my son|my daughter)\b',
    r'\b(stalk\w*)\b.{0,80}\b(scared|afraid|outside|following)\b',
    r'\b(cant|cannot|do not|dont) (feel|stay|be|keep myself) safe\b',
    r'\b(took|swallowed) (too many|a lot of|all (of )?(my|the)) (pills|tablets)\b',
    r'\b(jump(?:ing)? off|jump from)\b.{0,40}\b(bridge|building|roof|ledge)\b',
    r'\b(child|baby|kid)\b.{0,50}\b(locked|left|alone)\b.{0,35}\b(hot car|car)\b',
    r'\b(no quiero (seguir )?viviendo|me estoy cortando|tome demasiadas pastillas)\b',

    r'\b(want to die|going to end my life|not safe right now|in immediate danger)\b',
    r'\b(kill|hurt|harm|cut|cutting|shoot|hang|end) (myself|my life)\b',
    r'\b(suicid\w*|self harm\w*|self-harm\w*|overdos\w*)\b',
    r'\b(dont|do not|no longer) want to (live|be alive)\b',
    r'\b(wish i (was|were) dead|better off (dead|without me)|end it all)\b',
    r'\b(took|swallowed|taking) (a |the |all (of )?the )?(bottle|pills|tablets)\b',
    r'\b(cant|cannot|can not|struggling to|stopped) breath\w*\b',
    r'\b(chest (pain|hurts)|bleeding (a lot|heavily)|unconscious|wont wake up|not breathing|stroke)\b',
    r'\b(weapon|gun|knife)\b.{0,70}\b(threat|kill|hurt|outside)',
    r'\b(threat\w*|partner|husband|wife|ex)\b.{0,80}\b(weapon|gun|knife|hitting|beating|attacking|choking|strangl\w*)\b',
    r'\b(domestic violence|being abused|being hurt|abusing me|child abuse|unsafe at home)\b',
    r'\b(child|kid|baby|son|daughter)\b.{0,60}\b(hurt|abused|danger|neglect)\b',
    r'\b(suicidarme|matarme|no quiero vivir|hacerme dano|cortandome|sobredosis)\b',
    r'\b(no puedo respirar|dolor (en el |de )pecho|no despierta|sangrando mucho)\b',
    r'\b(pareja|esposo|esposa)\b.{0,60}\b(golpeando|amenaza|arma|pegando|maltrata)\b',
    r'\b(nino|nina|hijo|hija|bebe)\b.{0,50}\b(abuso|peligro|lastimando)\b',
]
PATTERNS = [re.compile(x) for x in DANGER]


def safety_status(text):
    text = normalize(text.replace('’', "'")).replace('sucidal', 'suicidal').replace('suicdal', 'suicidal')
    # Evaluate clauses separately: "not suicidal, but my partner has a gun" is danger.
    clauses = re.split(r'[.!?;\n]|\bbut\b|\bpero\b', text)
    ambiguous = False
    for clause in clauses:
        for pattern in PATTERNS:
            for match in pattern.finditer(clause):
                prefix = clause[max(0, match.start()-45):match.start()]
                suffix = clause[match.end():match.end()+40]
                negated = re.search(r'\b(not|never|no longer|dont|do not|without)\s+(?:feeling |currently |having |thinking of |want to )?$', prefix)
                historical = re.search(r'\b(years ago|last year|in the past|previously|used to)\b', prefix + ' ' + suffix)
                informational = re.search(r'\b(training|research|essay|class|volunteer)\b', clause)
                if negated or informational:
                    continue
                if historical:
                    ambiguous = True
                    continue
                return 'crisis'
    if ambiguous and not re.search(r'\b(safe now|safe right now|not in danger|no current|not suicidal)\b', text):
        return 'uncertain'
    return 'clear'
