"""Conservative, evidence-producing proposal rules; NOT the runtime matcher.

Only source prose is inspected. Organization names and old categories are never
classification inputs. All resulting proposals require approval before use.
"""
import re


def norm(text):
    # Preserve character offsets: every substituted character has length one.
    return ''.join('-' if c in '‐‑‒–—−' else "'" if c in '‘’' else c
                   for c in str(text or '')).lower()


# Keys are the proposed stable taxonomy. Patterns are audited service phrases,
# not arbitrary occurrences of food, health, children, transportation, or free.
NEEDS = {
    'food.pantry': r'\b(?:food[- /]pantr(?:y|ies)|community pantry|choice pantry|pantry (?:program|bags|items|distributions)|food[- ]distribution|grocery[- ](?:distribution|pickup|assistance)|grocer(?:y|ies)[- ](?:boxes|packages)|food bank|food-bag/pantry|pantry/food distribution)\b',
    'food.prepared_meals': r'\b(?:soup kitchen|hot (?:meals?|breakfast|lunch)|prepared meals|community (?:meals|dinners|breakfast|café|cafe)|(?:meal|meals)[- ](?:service|distribution|program|support)|(?:serves|serving|provides|providing|distributes|offering|offers) (?:free |daily |regular |evening |onsite |on-site )*(?:meals|breakfast|lunch)|lunch/feeding program|food kitchen|community soup kitchen)\b',
    'food.delivery': r'\b(?:meal delivery|(?:prepares and )?delivers (?:nutritious |medically tailored )?meals|home[- ]deliver(?:ed|ies|y)|grocery (?:pickup and delivery|delivery)|delivery for homebound seniors)\b',
    'food.medically_tailored': r'\bmedically tailored (?:meals|food)\b',
    'food.general_assistance': r'\b(?:food (?:assistance|support|access|distributions)|hunger-prevention|emergency food support|distributes free food|food and material assistance|(?:provides|offering|offers) (?:basic-need support, including |basic physical-needs support \()?food|distributes (?:food|meals) and (?:basic|other)|donates it to children)\b',
    'housing.emergency_shelter': r'\b(?:(?:emergency|overnight|day|seasonal emergency|homeless|family) shelters?|shelter services|shelter and housing assistance|shelter or rapid|including shelter|programs and shelter|residential recovery/shelter|temporary shelter|safe housing)\b',
    'housing.supportive_transitional': r'\b(?:(?:supportive|transitional|subsidized|recovery|bridge|maternity|safe, sober) housing|community housing|housing with wrap-around|residential group home|community living|residential/community living|residential (?:services|arrangements)|residential support|supported living|group homes?)\b',
    'housing.rental': r'\b(?:(?:rental|rent-assisted|rent-subsidized|affordable|low-income|senior|independent[- ]living|subsidized) (?:rental |senior |apartment )?(?:housing|apartments?|units|homes|residences|residential units)|apartment (?:building|community|complex)|rental (?:units|housing|apartments|homes)|senior[- ]housing|senior apartment|independent living|rental homes|leased housing)\b',
    'housing.rent_eviction_help': r'\b(?:(?:eviction|foreclosure)[- ](?:prevention|intervention|assistance)|rent/utility assistance|rental assistance|rent assistance|rental eviction|financial (?:help|assistance) (?:for |to prevent |to clients facing )(?:rental |rent, |eviction)|housing and utility financial help)\b',
    'housing.counseling_navigation': r'\b(?:housing[- ](?:counseling|assistance|support|placement|focused referrals)|housing-related (?:support|case-management|services|programs)|housing/tenant intervention|housing-focused case management|housing stability|housing and homelessness assistance)\b',
    'housing.homeownership_repairs': r'\b(?:homebuy(?:er|ing)|homeownership|down[ -]?payment|home repairs?|home weatherization|housing rehabilitation|home improvements|residential remodeling)\b',
    'housing.medical_lodging': r'\b(?:hospital housing|respite housing|lodging near a hospital)\b',
    'utilities.bill_assistance': r'\b(?:utility (?:payments|and eviction|and eviction-prevention|bills|financial help|help|turnoffs|shutoffs)|utilities, prescriptions|energy[- /](?:utility assistance|assistance)|rent/utilit(?:y|ies) assistance|utility and eviction prevention|utility \(bge\) bills|bge utility turnoffs)\b',
    'medical.general': r'\b(?:primary (?:medical |health)?care|primary healthcare|medical (?:clinic|care)|general (?:medical|hospital)|hospital (?:care|services)|acute[- ]care hospital|clinical services|family (?:medicine|medical center)|health care services|healthcare services|public health services|in-person health services|health services to residents|community health services)\b',
    'medical.emergency': r'\b(?:emergency (?:department|medical care|care|services|medicine)|trauma/emergency care|trauma center|emergency \(er\))\b',
    'medical.dental': r'\b(?:dental (?:care|services|clinic)|on-site dental|orthodontic (?:care|braces)|emergency dental)\b',
    'medical.rehabilitation': r'\b(?:physical (?:and occupational )?therapy|rehabilitation (?:and related medical care|therapies|therapy|services|programs)|rehabilitative (?:therapy|care|services)|on-site therapies|speech[- ](?:language )?therapy|occupational therapy|post-acute rehabilitation|sub-acute rehabilitation|rehabilitation/therapy|rehabilitative/therapy)\b',
    'medical.equipment': r'\b(?:medical (?:equipment|supply|supplies)|mobility (?:aids|equipment)|adaptive mobility equipment|assistive[- ]technology|stairlifts|stair lifts|ramps|hearing aids|cpap (?:devices|equipment))\b',
    'medical.sexual_reproductive': r'\b(?:sexual (?:and reproductive health|health)|reproductive (?:and sexual health|health)|hiv (?:and std testing|services)|ob[- /]?gyn|obstetrics|gynecology|prenatal|gender-affirming care)\b',
    'medical.prescriptions': r'\b(?:prescription (?:assistance|help|medications|delivery)|pharmac(?:y|ies)|mail-order pharmacy|home-delivery pharmacy|affordable medications|brand-name medications)\b',
    'medical.cost_assistance': r'\b(?:co-pay(?:ment)? (?:relief|assistance)|financial (?:and co-payment assistance|support to help eligible patients cover medical|help for uninsured)|medical copays|grants to help underinsured|caregiving costs|financial assistance programs|financial grants and equipment support)\b',
    'mental_health.clinical': r'\b(?:mental[- /]health (?:care|services|therapy|counseling|treatment|clinic|center|private practice|practice|support)|behavioral[- ]health (?:care|services|counseling|clinic|provider|treatment|program|support|offerings)|psychiatr(?:y|ic (?:care|services|evaluation|rehabilitation|medication|hospital|triage|units|treatment))|psychotherapy|psychotherapists|counseling (?:practice|services)|licensed (?:christian )?counselors|outpatient therapy|family counseling|individual counseling|mental and behavioral health care|integrated mental health)\b',
    'mental_health.peer_support': r'\b(?:peer[- ](?:led |based )?(?:support|mentorship)|support groups|grief (?:support|resources)|psychosocial support|emotional (?:and practical )?support|recovery coaching)\b',
    'crisis.intervention': r'\b(?:crisis[- ](?:helpline|hotline|line|intervention|stabilization|support|response|services|admission)|crisis (?:helpline/text line|appointments)|urgent psychiatric (?:care|triage)|emergency mental-health support|24-hour crisis response)\b',
    'substance_use.treatment': r'\b(?:addiction[- ](?:treatment|counseling|recovery)|substance[- ](?:use|abuse)[- /](?:(?:disorder|recovery) )?(?:treatment|services|counseling|recovery|programs|intervention)|alcohol and drug (?:dependence|use)|opioid[- ](?:use |use disorder )?treatment|residential recovery programs|drug & alcohol education|substance-abuse outpatient|substance use disorders|recovery services|recovery programs)\b',
    'substance_use.medications': r'\b(?:medication[- ]assisted (?:treatment|therapy)|methadone|suboxone|buprenorphine|medications for opioid use disorder)\b',
    'substance_use.detox': r'\b(?:detox|withdrawal management)\b',
    'substance_use.harm_reduction': r'\b(?:harm[- ]reduction|syringe exchange|naloxone|safer drug-use supplies)\b',
    'legal.assistance': r'\b(?:legal (?:assistance|aid|services|help|representation)|public[- ]defen[cs]e|criminal[- ]defen[cs]e|elder[- ]law|estate[- ]planning|attorney consultations|law firm providing|post-dispositional representation|legal defense|lawyer referral)\b',
    'legal.identity_documents': r'\b(?:identification and document help|help (?:obtaining|establishing) (?:ids|a mailing address)|ids or birth certificates|id(?:entification)? (?:assistance|help)|passport services)\b',
    'immigration.support': r'\b(?:immigration(?:[- ]related)? (?:legal|assistance|documentation|social services)|immigrant (?:assistance|support|communities)|immigrant-focused community support|refugee (?:support|resettlement|and immigrant)|resettlement (?:assistance|and integration)|asylum seekers|forced migrants|citizenship and immigration|immigrant health support)\b',
    'benefits.enrollment_navigation': r'\b(?:benefits? (?:enrollment|access|paperwork|programs|and services|marketplace|office|and related services)|(?:snap|unemployment|va|veterans|social security) (?:assistance|application help|benefits|services|claims)|food benefits|insurance (?:help|enrollment|navigation)|help access benefits|help obtaining ids and public benefits|assists? with eligibility|health benefits marketplace|plan choices|claims assistance)\b',
    'employment.training_search': r'\b(?:employment (?:support|services|training|coaching|and training|and career|connections|opportunities|or vocational|related|agency)|job[- ](?:search|readiness|training|coaching|placement|leads|help|and-career|career|support)|career[- ](?:training|counseling|resources|guidance|preparation|support)|workforce[- ](?:development|training|services)|vocational (?:training|services|and supported employment|coaching|transition|on- and off-campus)|supported employment|employment-related|career/goal planning|job and career assistance|job/career assistance)\b',
    'education.learning': r'\b(?:special[- ]education|educational (?:programs|and vocational training)|academic instruction|adult (?:basic |continuing-)?education|education (?:school|programs)|school for ages|autism.*education|learning programs|tutoring|homework help|ged|esl classes|english and job-readiness|library services|public library|education for (?:children|individuals)|individualized education)\b',
    'transportation.assistance': r'\b(?:transportation (?:assistance|services|program|support|to|for)|(?:medical|air|accessible|door-to-door|curb-to-curb|coordinated|emergency|on-site) transportation|free rides|gas cards|sedan service|vehicle awards|volunteer-piloted flights)\b',
    'essentials.clothing_supplies': r'\b(?:clothing (?:and|distribution|assistance|bank|pantry)|hygiene (?:supplies|and household|items|services)|diaper (?:pantry|hub)|baby[- ](?:item|supplies)|household (?:goods|supplies|items|essentials)|basic supplies|food and clothing|food, clothing|personal care items|school supplies|donated furniture|furniture assistance|free clothing|showers|laundry|thrift (?:shop|store)|donated items)\b',
    'childcare.early_learning': r'\b(?:child[- ]?care|daycare|head start|early (?:childhood|learning)|child development center|before[- /]and after-school care)\b',
    'family.youth_parenting': r'\b(?:youth (?:programming|programs|development|support|employment|empowerment|education|and family|services)|family[- ](?:support|focused services|resource navigation)|parenting (?:education|classes|help)|foster care|after-school|summer (?:programming|camp)|pregnancy support|mentoring program|mentorship programs|family support services)\b',
    'safety.survivor_support': r'\b(?:domestic (?:violence|abuse)|intimate partner violence|violence survivor support|victims of crime|crime victims?|victim[- ](?:rights|case management)|sexual assault|interpersonal violence|survivor support)\b',
    'safety.child_protection': r'\b(?:child protective services|child[- ]protection|child abuse|child sexual abuse|missing (?:or exploited|children)|exploited children)\b',
    'disability.independent_living': r'\b(?:disability[- ](?:services|support|focused|related supports)|(?:supports|services) for (?:people|adults|children and adults|individuals) with (?:intellectual|developmental|disabilities)|independent[- ]living (?:supports|and mobility training|skills)|day habilitation|personal supports|autism-related resources|autism-specific information|programs and services for people who are blind|blind community|supports for adults with intellectual)\b',
    'care.assisted_living': r'\bassisted[- ]living\b',
    'care.skilled_nursing': r'\b(?:skilled[- ]nursing|nursing home|nursing-home|long-term (?:residential |health |nursing )?care|long-term skilled nursing)\b',
    'care.adult_day': r'\b(?:adult (?:medical |day health |day medical |day/)?day[- ]?(?:care|program|services|center)|adult medical day|adult day|daytime (?:care|supervised care|program for adults)|day program for adults|medical adult day|day-program services)\b',
    'care.home': r'\b(?:in[- ]home (?:health |healthcare |medical |non-medical |personal |nursing |private-duty |senior |skilled )?(?:care|caregiving|support|services)|home[- ]health|home[- ]care|at-home (?:personal care|care|caregiving)|health care services delivered in patients|homecare|home-based care)\b',
    'care.memory': r'\b(?:memory[- /](?:care|dementia care)|dementia[- ](?:care|support|focused|specific)|alzheimer.s/dementia care|specialized dementia support)\b',
    'care.respite_hospice': r'\b(?:respite (?:care|stays|support|services)|hospice|palliative|end-of-life support)\b',
    'navigation.case_management': r'\b(?:case[- ]management|case managers|care coordination|resource navigation|information (?:and |& )?(?:referral|assistance)|referral (?:help|services)|referrals to other (?:agencies|services|local services)|connects? (?:people|residents|clients|families)|resource referrals|information and resources|public health.*information|aging-related information)\b',
    'financial.counseling_tax': r'\b(?:tax[- ]preparation|tax (?:preparation|credits?)|debt[- ](?:relief|counseling)|financial (?:education|coaching|literacy)|budget(?:ing| counseling)|financial-management training)\b',
    'financial.emergency_assistance': r'\b(?:emergency financial|cash\) assistance|monetary \(cash|financial assistance|financial support|financial grants|emergency help|benevolence fund|financial help)\b',
    'community.social_recreation': r'\b(?:senior (?:citizen )?center|community fitness|fitness (?:facility|classes)|recreational (?:programs|programming)|social (?:programs|and recreational programming|and peer support)|community center serving older adults|youth-program provider|therapeutic horseback riding|adaptive riding|therapy pet visits|social activities|social and recreational activities|social and enrichment activities)\b',
    'digital.computers_internet': r'\b(?:public computers|computer(?:s)? (?:and (?:internet|printers|printing)|access)|internet access|free wi[- ]?fi|free internet access|access to (?:public )?computers|computer literacy)\b',
    'pets.food_veterinary': r'\b(?:pet food pantry|pet pantry|veterinary clinics|spay/neuter|animal shelter|animal-care services)\b',
    'language.interpretation': r'\b(?:language interpretation|translation services|multilingual translation|language services|asl interpreting|translation, and referrals)\b',
}

# Additional service phrases found in the complete description review.
NEEDS['food.pantry'] = NEEDS['food.pantry'].replace('|food[- ]distribution', '')
NEEDS['food.general_assistance'] += r'|\b(?:food[- ]distribution|access to healthy food|food services|food program)\b'
NEEDS['food.medically_tailored'] = r'\bmedically tailored(?:, home-delivered)?(?: frozen)? (?:meals|food)\b'
NEEDS['food.pantry'] += r'|\bfood/hygiene pantry\b'
NEEDS['food.pantry'] += r'|\b(?:food and (?:diaper|clothing) (?:pantry|distribution)|food distribution/pantry|food-distribution/pantry|emergency groceries|grocery-style shopping)\b'
NEEDS['food.prepared_meals'] += r'|\b(?:meal services|community meal programs|meal outreach|meal/food distribution|hot breakfast program|regular lunch|Friday night dinners)\b'
NEEDS['housing.emergency_shelter'] += r'|\b(?:temporary emergency housing|housing and shelter organization)\b'
NEEDS['housing.rental'] += r'|\b(?:townhome rental community|residential rental property|rented townhome units|senior-focused housing community|housing for older adults|apartments for adults|public housing programs|retirement home|housing community described as affordable|on-campus residential living)\b'
NEEDS['care.residential_unspecified'] = r'\b(?:residential care facility|housing for residents|housing with care services)\b'
NEEDS['medical.general'] += r'|\b(?:physician office|hospital facility|clinic-based health care|patient care through its faculty|neurology clinic|neurological care|comprehensive medical and surgical services|in-home wound care)\b'
NEEDS['medical.general'] += r'|\bhospital-based transitional care\b'
NEEDS['care.home'] += r'|\bin-home wound care\b'
NEEDS['mental_health.clinical'] += r'|\b(?:mental health programs|mental health service provider|mental health and therapy services|mental-health and wellness services|counseling and therapy for mental health|counseling and therapy services|free therapy|anxiety disorders and ocd|individual, couples, and group counseling|counseling center)\b'
NEEDS['mental_health.peer_support'] += r'|\b(?:peer-led recovery support|grief and bereavement support)\b'
NEEDS['crisis.intervention'] += r'|\bcrisis-management\b'
NEEDS['education.learning'] += r'|\b(?:research library|educational program|school serving (?:grades|students)|music and dance education|family engagement and enrollment)\b'
NEEDS['disability.independent_living'] += r'|\b(?:supports and advocacy for people with intellectual and developmental disabilities|support for individuals with intellectual and developmental disabilities|autism diagnostic testing|aba therapy)\b'
NEEDS['community.social_recreation'] += r'|\b(?:community center for seniors|recreation programs)\b'
NEEDS['benefits.enrollment_navigation'] += r'|\bssa services\b'
NEEDS['medical.patient_support'] = r'\b(?:treatment-support services|patient resources|education, awareness, advocacy, and hands-on support|cancer information|patient advocacy|education for patients)\b'
NEEDS['legal.advocacy_information'] = r'\b(?:legal resources|fair housing|legal advocacy|disability-rights advocacy|know your rights)\b'
NEEDS['financial.disaster_grants'] = r'\bgrants designed to help artists\b'
NEEDS['housing.accessibility_modifications'] = r'\b(?:home-accessibility evaluations|home accessibility needs|accessibility-related services|mobility accessibility equipment|fall-risk assessments)\b'
NEEDS['disaster.preparedness'] = r'\b(?:disaster preparedness|risk-reduction guidance|readiness education)\b'
del NEEDS['care.respite_hospice']
NEEDS['care.respite'] = r'\b(?:respite (?:care|stays|support|services)|short-term respite)\b'
NEEDS['care.hospice_palliative'] = r'\b(?:hospice|palliative|end-of-life support)\b'
del NEEDS['financial.counseling_tax']
NEEDS['financial.tax_help'] = r'\b(?:tax[- ]preparation|tax (?:preparation|credits?)|vita/aarp)\b'
NEEDS['financial.counseling'] = r'\b(?:debt[- ](?:relief|counseling)|financial (?:education|coaching|literacy)|budget(?:ing| counseling)|financial-management training)\b'
NEEDS['legal.criminal_defense'] = r'\b(?:criminal[- ]defen[cs]e|public[- ]defen[cs]e|legal defense|criminal charges|indigent clients in criminal)\b'
NEEDS['legal.civil_aid'] = r'\bcivil legal (?:assistance|aid|help)\b'
NEEDS['legal.immigration'] = r'\b(?:immigration[- ](?:related )?legal|immigration legal clinic)\b'
NEEDS['legal.housing_disputes'] = r'\b(?:landlord/tenant matters|tenant legal|housing/tenant intervention)\b'
NEEDS['legal.expungement'] = r'\b(?:expungement|warrant-recall)\b'
NEEDS['legal.elder_estate'] = r'\b(?:elder[- ]law|estate[- ]planning|estate administration|guardianship matters|probate/estate administration)\b'

CONSTRAINTS = {
    # These describe an available program, not universal eligibility promises.
    'cost.free_program_reported': r'\b(?:free (?:meals|groceries|food|therapy|civil legal|legal|programs|peer|mental health|cancer-focused|community|financial education)|no[- ]cost|no[- ]charge|at no cost|free of charge|at no charge|no charge|pro bono)\b',
    'cost.sliding_scale_reported': r'\bsliding[- ](?:fee|scale)\b',
    'cost.low_cost_reported': r'\b(?:low[- ]cost (?:care|psychotherapy)|affordable (?:medications|prescription medications)|low costs|free or low-cost care)\b',
    'cost.private_pay_reported': r'\b(?:private[- ]pay|self[- ]pay|fee-for-service)\b',
    'insurance.medicaid_reported': r'\b(?:accepts? (?:maryland )?medicaid|medicaid (?:acceptance|accepted)|medicaid-based care|through medicaid|with medicaid|medicaid/homecare|medicaid/.*approved|medicare/medicaid[- ]approved|coverage for medical assistance|primarily serves maryland waiver, medicaid)\b',
    'insurance.medicare_reported': r'\b(?:medicare (?:is )?accepted|accepts? (?:medicaid, )?medicare|medicare part b|medicare/medicaid[- ]approved)\b',
    'insurance.carefirst_reported': r'\bcarefirst bluecross blueshield\b',
    'age.children_served': r'\b(?:children|pediatric(?:s)?|school-aged|school-age|kids)\b',
    'age.youth_served': r'\b(?:youth|adolescents?|teens?|young people)\b',
    'age.adults_served': r'\badults\b',
    'age.older_adults_served': r'\b(?:older adults|seniors|elderly|senior housing|senior living|senior center)\b',
    'age.all_ages_reported': r'\b(?:all ages|across the lifespan|all age groups)\b',
    'population.veterans_served': r'\b(?:veterans|service members|soldiers|airmen|guardians|army families)\b',
    'population.disabilities_served': r'\b(?:people with disabilities|adults with disabilities|developmental disabilities|intellectual disabilities|children with disabilities|disabled adults|adults with cognitive or physical impairments)\b',
    'population.homelessness_served': r'\b(?:people experiencing homelessness|homeless and displaced youth|homeless women|homeless men|homeless people|people transitioning from homelessness)\b',
    'population.immigrants_served': r'\b(?:immigrants|refugees|asylum seekers|forced migrants)\b',
    'language.spanish_reported': r'\b(?:spanish-language service|services? (?:in|offered in) spanish|spanish[- ]speaking staff)\b',
    'language.english_reported': r'\benglish-language service\b',
    'language.asl_reported': r'\b(?:asl interpreting|asl-accessible|american sign language)\b',
    'access.walk_in_reported': r'\b(?:walk-ins? (?:are )?(?:accepted|welcome)|walk-in (?:access|intake|and same-day)|drop-in center|drop-in location)\b',
    'access.appointment_reported': r'\b(?:by appointment|appointment[- ]based|appointments? (?:are |is )?(?:recommended|and/or required|required)|appointment required|appointments required)\b',
    'access.referral_required_reported': r'\b(?:agency referral typically required|referral (?:is )?required|requires? (?:an? )?(?:agency |physician )?referral|referral-only)\b',
    'access.telehealth_reported': r'\b(?:telehealth|telemedicine|teletherapy|telepsychiatry|tele-psychiatry|tele-therapy|virtual visits|online therapy|video telehealth)\b',
    'documents.requirements_reported': r'\b(?:(?:requires?|required to (?:bring|provide)) (?:an? )?(?:photo id|identification|proof of|id)|(?:photo id|proof of (?:income|residency|address)|identification) (?:is |are )?required)\b',
    'accessibility.wheelchair_entrance_reported': r'\bwheelchair[- ]accessible (?:entrance|entry)\b',
    'accessibility.wheelchair_parking_reported': r'\bwheelchair[- ]accessible parking\b',
    'accessibility.wheelchair_transport_reported': r'\b(?:wheelchair[- ]accessible transportation|accessible transportation)\b',
    'accessibility.accessible_units_reported': r'\b(?:ada[- ]compliant (?:studio|units)|accessible (?:apartments|units)|accessible \(ada-compliant\) units)\b',
    'food.client_choice_reported': r'\b(?:client-choice|choice-based|choice pantry|choose (?:among|their own)|clients select items|tailors food to clients. preferences)\b',
    'food.fresh_produce_reported': r'\b(?:fresh produce|fresh-vegetable|fruit, vegetables)\b',
    'food.frozen_items_reported': r'\b(?:frozen (?:meat|items|meals))\b',
    'food.nonperishable_reported': r'\bnon[- ]?perishable\b',
    'food.drive_through_reported': r'\b(?:drive[- ](?:thru|through|up)|curbside (?:pickup|food bank))\b',
    'food.kosher_reported': r'\bkosher\b',
    'food.pet_food_reported': r'\bpet (?:food )?pantry\b',
}

CONSTRAINTS.update({
    'age.threshold_reported': r'\b(?:aged? |ages? |adults |residents |seniors |senior \(age |senior \()?\d{1,2}\s*(?:\+|and (?:older|over|up)|years and older)\b|\b\d{1,2}\+',
    'eligibility.income_condition_reported': r'\b(?:income[- ](?:restricted|qualified|limited|eligible|based)|income (?:limits|restrictions)|hud[- ](?:based )?income limits)\b',
    'service_area.baltimore_city_reported': r'\b(?:serv(?:es|ing) baltimore city|baltimore city residents|residents in baltimore city|for .*residents in baltimore city|serves baltimore city)\b',
    'service_area.baltimore_county_reported': r'\b(?:serv(?:es|ing) baltimore county|baltimore county residents|residents of baltimore county)\b',
    'service_area.maryland_reported': r'\b(?:maryland residents|serv(?:es|ing) maryland(?! waiver)|statewide coverage|statewide social-service programs|statewide, free legal services)\b',
    'service_area.nationwide_reported': r'\b(?:nationwide|all 50 states|across the united states)\b',
    'service_area.local_restriction_reported': r'\b(?:residents in catchment area|specified .*zip codes|residents of the greater catonsville area|serves baltimore city, baltimore county, and harford county)\b',
})
CONSTRAINTS['insurance.medicaid_reported'] += r'|\b(?:accepts? (?:maryland )?medicare, medicaid|medicaid and medicare accepted)\b'
CONSTRAINTS['insurance.medicare_reported'] += r'|\baccepts? maryland medicaid(?: \(maryland medical assistance\))?, medicare\b'

UNCERTAIN = re.compile(r'\b(?:appears? to|suggesting|reviewers? (?:report|describe|accounts)|reviewer reports|reported by users|according to .*reviews|limited (?:publicly available |available )?(?:information|detail)|no (?:verified|verifiable|detailed|specific|explicit|public) (?:official |service |description of )?(?:services|programs|description|details|website)|not (?:documented|specified)|insufficient|does not (?:provide|include|describe)|do not (?:provide|describe)|could not|no independent)\b')
NEGATIVE = re.compile(r'\b(?:no|not|without|doesn.t|don.t|cannot|closed|unavailable|unverified|could not)\b')
RESIDENTIAL = re.compile(r'\b(?:assisted[- ]living|nursing home|skilled[- ]nursing|senior living|senior apartment|senior-housing|rental community|retirement community|adult (?:medical )?day|home[- ]care|home[- ]health|in[- ]home (?:care|health|non-medical|senior care)|residential (?:care|assisted|facility)|memory[- ]care|apartment community)\b')


def sentences(text):
    """Yield original spans; split semicolons too so a negation stays local."""
    for m in re.finditer(r'[^.;\n]+(?:[.;]|$)', str(text or '')):
        yield m.start(), m.end(), m.group()


def matches(text, pattern, field):
    rx = re.compile(pattern)
    results = []
    for start, end, sentence in sentences(text):
        normalized = norm(sentence)
        for m in rx.finditer(normalized):
            # A short cue is kept alongside full sentence context. Negated
            # mentions never become positive evidence without manual review.
            prefix = normalized[max(0, m.start()-100):m.start()]
            prefix = re.sub(r'\b(?:no[- ]cost|no[- ]charge|no charge|no cost|non-medical|not-for-profit)\b','',prefix)
            suffix = normalized[m.end():]
            if NEGATIVE.search(prefix) or re.match(r'\s+(?:is|are)\s+(?:not|unavailable|closed)',suffix):
                continue
            a, b = start+m.start(), start+m.end()
            results.append({'field': field, 'snippet': str(text)[a:b],
                            'start': a, 'end': b,
                            'context': str(text)[start:end].strip()})
    return results


# Specific records whose wording needs conservative treatment after the full
# description review. These do not override source facts or reliability scores.
REVIEW_NOTES = {
    1: 'Description explicitly lacks attributable program details.',
    21: 'Learning programs are only described tentatively; curriculum and access unknown.',
    33: 'Food bank coordinates partners; do not assume public pickup at the office.',
    45: 'Worship and religious education only; no actionable assistance established.',
    73: 'No explicit service description and linked website reportedly fails.',
    77: 'General help is too vague to establish service capability.',
    84: 'Market availability is described, but free food assistance is not established.',
    90: 'Description explicitly does not establish food pantry services.',
    92: 'No specific social programs documented.',
    95: 'Worship location and amenities do not establish assistance services.',
    114: 'Physical listing and accessibility only; service capability unknown.',
    146: 'No service description.',
    158: 'On-site market is not evidence of free food assistance.',
    181: 'Accepting donations does not establish distribution to clients.',
    185: 'No specific services documented.',
    214: 'Men’s Welcome Center is closed; other described programs may continue.',
    217: 'Listing reports temporary closure; confirm current operations.',
    259: 'Organization listing and accessible building only.',
    269: 'Housing office named but specific programs are not documented.',
    297: 'No service description.',
    298: 'Listing reports permanent closure.',
    303: 'Listing reports permanent closure and website 404.',
    311: 'Career-center name is not evidence of specific services.',
    328: 'Branch reports temporary closure for maintenance.',
    343: 'Cemetery/burial business; funeral financial assistance is not established.',
    391: 'No service description.',
    405: 'No descriptive service information.',
    431: 'Academic building only; patient-facing services not established.',
    473: 'Library services temporarily relocated; confirm usable destination.',
    541: 'Assisted-living phrase is explicitly only a listing title, not verified service detail.',
    558: 'No programs described.',
    567: 'Craft shop, not documented financial or social assistance.',
    583: 'No specific services documented.',
    593: 'No verifiable service description.',
    645: 'Explicitly does not provide ambulatory or personal hygiene care.',
    652: 'Branch reports temporary closure for facility improvements.',
    671: 'Generic listing tags are not service evidence.',
    675: 'No specific programs described.',
    723: 'Government office name only; no described service.',
    726: 'Generic social services resources; specific support unknown.',
    756: 'Health consultant listing alone does not establish medical care.',
    770: 'Nonprofit classification does not establish services.',
    776: 'Utility supplier, not described utility-bill financial assistance.',
    783: 'Veteran support without specified services; do not infer housing or cash assistance.',
    801: 'Patient resources and navigation, not evidence of directly operated clinical care.',
    805: 'Services vary by member location and funding; confirm actual provider.',
    845: 'Description reports conflicting addresses; verify location before routing.',
    914: 'Domestic-violence groups do not establish an emergency survivor hotline.',
    962: 'Georgetown campus is outpatient only; network inpatient services not site-specific.',
    1011: 'General social support is not a specific actionable service.',
    1012: 'Treatment involvement is suggested only by reviewer text.',
    1048: 'Generic resources and support; specific service unknown.',
    1050: 'Commercial insurance agency; benefits enrollment assistance not established.',
    1055: 'Pharmaceutical company; no patient assistance program documented here.',
    1112: 'State’s Attorney office is not a public defender.',
    1114: 'Mission statement; specific local assistance needs confirmation.',
    1115: 'Veterans organization listing alone does not establish benefits help.',
    1117: 'Unspecified veteran programs; no inference from name.',
    1124: 'Rights education and advocacy; direct case representation not established.',
    1126: 'Professional association; individual representation not established.',
    1129: 'Rights information; direct legal representation not established.',
    1135: 'Law-school clinics are mentioned without public intake details.',
    1136: 'Law-school education is not evidence of public immigration representation.',
    1150: 'Explicitly does not represent individual cases; legal coordination only.',
    1161: 'Office listing only; no inference from Public Defender name.',
    1164: 'Office listing explicitly lacks detailed services.',
    1165: 'Attorney listing only; verify services.',
    1173: 'Organization name only; do not infer a crisis service from RAINN.',
    1178: 'No programs or services detailed.',
    1181: 'Dentist professional association; patient dental treatment not established.',
    1192: 'Education and advocacy do not establish clinical mental-health treatment.',
    1200: 'Community development office only; no specific assistance described.',
    1211: 'Agency office listing only.',
    1219: 'Explicitly no direct support or case management; navigation network only.',
    1220: 'Chapter listing only; no specific services described.',
    1230: 'Old category repeated in description; no actual program details.',
    1262: 'Exact offerings undocumented.',
    1273: 'Temporarily closed; anticipated reopening is not confirmation.',
    1275: 'Renovation in progress; confirm branch availability.',
    1305: 'Environmental regulation is not utility bill assistance.',
    1307: 'Food/drug regulator is not food or prescription assistance.',
    1308: 'Natural-resource administration is not food or utility bill assistance.',
    1342: 'Pollinator education in Pacific Northwest; relevance/service area needs review.',
}

# Suppress false service readings identified during row-by-row description review.
NO_NEEDS = {1,45,73,77,90,92,95,103,104,106,114,117,132,133,142,146,149,176,181,185,203,209,215,216,259,269,297,311,318,343,370,391,405,425,431,541,558,567,583,593,671,675,677,723,726,756,770,776,783,919,992,1011,1048,1050,1055,1058,1059,1062,1063,1067,1070,1077,1080,1081,1082,1087,1088,1090,1093,1094,1096,1097,1103,1105,1107,1108,1112,1114,1115,1117,1124,1126,1129,1135,1136,1161,1164,1165,1167,1173,1178,1181,1192,1200,1211,1220,1230,1262,1305,1307,1308,1342}

NO_NEEDS -= {1124,1129,1192}
NO_NEEDS -= {318}
MANUAL_ADDITIONS = {
    3:{'navigation.case_management':'system navigation'},
    8:{'mental_health.clinical':'behavioral health'},
    19:{'mental_health.clinical':'therapy'},
    22:{'food.prepared_meals':'meals'},
    40:{'essentials.clothing_supplies':'clothing'},
    51:{'medical.general':'medical and dental','medical.dental':'medical and dental','employment.training_search':'employment and education supports'},
    55:{'substance_use.treatment':'therapeutic residential treatment'},
    68:{'housing.counseling_navigation':'housing assistance'},
    71:{'food.pantry':'food and diaper pantry'},
    101:{'food.general_assistance':'distributions of food'},
    109:{'mental_health.clinical':'individual, couples, and group counseling'},
    162:{'food.general_assistance':'food program'},
    265:{'care.memory':'memory/Alzheimer’s care','care.respite':'short-term respite'},
    291:{'housing.rental':'residential living options'},
    418:{'community.social_recreation':'wellness program','transportation.assistance':'pickup/driver services'},
    449:{'food.general_assistance':'community market stocked with free food'},
    528:{'medical.general':'physician office'},
    554:{'care.residential_unspecified':'Personal Assistance Program'},
    621:{'disability.independent_living':'people with developmental disabilities'},
    703:{'housing.supportive_transitional':'housing program','medical.general':'Outpatient Clinic'},
    795:{'medical.patient_support':'treatment-support services'},
    898:{'disability.independent_living':'ABA therapy'},
    957:{'mental_health.peer_support':'welcoming space focused on wellness, recovery, and growth'},
    1033:{'medical.equipment':'equipment support'},
    1099:{'essentials.clothing_supplies':'distributing items to people in need'},
    1086:{'food.general_assistance':'basic physical-needs support (food, clothing, shelter)'},
    1101:{'food.general_assistance':'including food, clothing, shelter'},
    1131:{'legal.assistance':'legal services and trainings to community organizations'},
    1140:{'legal.advocacy_information':'legal resources and connections for the public'},
    1150:{'legal.advocacy_information':'pro bono legal resources'},
    1192:{'mental_health.peer_support':'advocacy, education, and public outreach around mental health'},
    1219:{'navigation.case_management':'connect people with local resources'},
}
MANUAL_REMOVALS = {
    35:{'food.pantry'}, 55:{'food.pantry'}, 809:{'medical.general'},
    1150:{'legal.assistance'},
    1219:{'care.memory','navigation.case_management'},
}
REVIEW_NOTES.update({
    1131:'Legal services target organizations and nonprofit groups; not general individual representation.',
    31:'Programs for children and families are not described specifically enough to assign a service subtype.',
    57:'Peer recovery support is documented; do not present as clinical addiction treatment.',
    1073:'Provides information about a pantry; operation/intake at this location needs confirmation.',
})


# Source-bound corrections from the November 8 top-ten review. Keep regeneration
# from reintroducing disproved clinical tags; full before/after evidence is in
# audits/phase1/nov08_service_corrections.json.
CORRECTED_REMOVALS = {rid:set(tags) for rid,tags in MANUAL_REMOVALS.items()}
for _rid in (333,400,470,642,799,800,951,1041,1047):
    CORRECTED_REMOVALS.setdefault(_rid,set()).add('medical.general')
CORRECTED_REMOVALS.setdefault(1001,set()).add('mental_health.clinical')
for _rid in (487,581):
    CORRECTED_REMOVALS.setdefault(_rid,set()).add('childcare.early_learning')
MEDICAL_SCOPED = {261,337,581,601,629,638,703,1029,1205,1236,1238,
                  1249,1255,1259,1269,1321,1324,1329,1335}


def propose(source, *, corrections=True):
    removals = CORRECTED_REMOVALS if corrections else MANUAL_REMOVALS
    rid = source['resource_id']
    desc = source['description']
    text = norm(desc)
    flags = []
    notes = []
    facts = {}
    residential = bool(RESIDENTIAL.search(text))
    food_explicit = bool(re.search(r'food[- ]pantry|food distribution|community pantry|community meals|public.*meals', text))
    for suffix, pattern in NEEDS.items():
        if rid in NO_NEEDS:
            break
        found = matches(desc, pattern, 'description')
        # Prevent clinical legal divisions and business names from being treated
        # as treatment. Needs are also not derived from restrictions alone.
        if suffix.startswith(('mental_health.', 'medical.', 'substance_use.')) and re.search(r'public defender|public defense|legal defense|law firm', text):
            continue
        if suffix.startswith('food.') and residential and not food_explicit:
            continue
        if suffix.startswith('food.') and suffix != 'food.delivery' and 'pet food pantry' in text and not re.search(r'community pantry|food distribution|groceries', text):
            continue
        if suffix == 'food.delivery' and not re.search(r'\b(?:food|grocer|meal)', text):
            continue
        if suffix == 'essentials.clothing_supplies' and residential:
            continue
        if suffix == 'housing.rental' and 'independent living skills' in text and not re.search(r'apartment|rental|housing', text):
            continue
        if suffix == 'utilities.bill_assistance' and not re.search(r'assistance|help|payments|financial|prevention', text):
            continue
        if found:
            scope = 'program_or_location_unconfirmed' if re.search(r'across multiple|network|multiple locations|broader .*network|vary by site|across .*locations', text) else 'described_service'
            if residential and suffix.startswith(('medical.','transportation.','digital.','community.')):
                scope = 'enrolled_clients_or_residents'
            evidence = found[0]
            local = norm(evidence['context'])
            if re.search(r'referrals? (?:to|for)|connects? .{0,45}(?:to|with)|referral center|partner-provided|through partner', local):
                scope = 'referral_or_partner_delivery_unconfirmed'
            if suffix in removals.get(rid,set()):
                continue
            if suffix.startswith('food.') and re.search(r'residential (?:treatment|recovery)|emergency shelter|housing for residents|senior housing',text):
                scope = 'enrolled_clients_or_residents'
            facts['need:'+suffix] = {**evidence, 'scope':scope, 'hard_filter_eligible':False}

    additions = MANUAL_ADDITIONS.get(rid, {})
    if corrections and rid == 48:
        additions = {**additions, 'medical.dental': 'dental', 'mental_health.clinical': 'behavioral health'}
    for suffix,snippet in additions.items():
        if snippet not in desc:
            continue
        start = desc.index(snippet)
        context = next((s.strip() for a,b,s in sentences(desc) if a<=start<b),desc)
        facts['need:'+suffix] = {'field':'description','snippet':snippet,'start':start,'end':start+len(snippet),'context':context,'scope':'described_service','hard_filter_eligible':False}
    for tag in list(facts):
        # House of Ruth publishes distinct services for each Baltimore office.
        # See audits/phase1/provider-review-2026-11-20.md.
        if corrections and rid in (678, 1169, 1171):
            if tag == 'need:childcare.early_learning':
                facts[tag]['scope'] = 'enrolled_clients_or_residents'
            elif tag == 'need:housing.emergency_shelter' or (rid == 1169 and tag in {
                'need:legal.assistance', 'need:safety.survivor_support'
            }):
                facts[tag]['scope'] = 'program_or_location_unconfirmed'
        if corrections and tag=='need:medical.general' and rid in MEDICAL_SCOPED:
            facts[tag]['scope']='enrolled_clients_or_residents' if rid in {261,337,581,601,629,703,1238} else 'program_scope_requires_confirmation'
        if corrections and rid==1068 and tag=='need:mental_health.clinical':
            facts[tag]['scope']='program_scope_requires_confirmation'
        if rid in (22,55,682,1041) and tag.startswith('need:food.'):
            facts[tag]['scope'] = 'enrolled_clients_or_residents'
        if rid in (33,778,991,1150,1219):
            facts[tag]['scope'] = 'referral_or_partner_delivery_unconfirmed'
        if rid==1131:
            facts[tag]['scope'] = 'program_or_location_unconfirmed'
        if rid==1073 and tag.startswith('need:food.'):
            facts[tag]['scope'] = 'referral_or_partner_delivery_unconfirmed'
        # A separately described public pantry is not limited to shelter clients
        # merely because the organization also operates a shelter.
        if rid in (186,212,1170) and tag.startswith('need:food.'):
            facts[tag]['scope'] = 'program_or_location_unconfirmed'
    if 'need:food.general_assistance' in facts and any(t.startswith('need:food.') and t!='need:food.general_assistance' for t in facts):
        del facts['need:food.general_assistance']

    if facts:
        for suffix, pattern in CONSTRAINTS.items():
            found = []
            for field in ('description','restrictions'):
                found += matches(source[field], pattern, field)
            if found:
                if rid==205 and suffix=='service_area.maryland_reported':
                    continue  # Charles County, Maryland residents != statewide access.
                if suffix.startswith('food.') and not any(t.startswith('need:food.') for t in facts) and suffix != 'food.pet_food_reported':
                    continue
                evidence = found[0]
                facts[suffix] = {**evidence,'scope':'program_scope_requires_confirmation','hard_filter_eligible':False}

        # Site office hours are informational. Never infer intake hours or that
        # a particular food program runs whenever its host organization is open.
        hours = source['hours']
        for day in ('Saturday','Sunday'):
            m = re.search(r'\b'+day+r'\s*:?\s*([^;\n]+)',hours,re.I)
            if m and not re.search(r'closed|unknown|not available|not listed',m.group(),re.I) and re.search(r'\d|open',m.group(),re.I):
                facts['hours.weekend_site_hours_reported'] = {'field':'hours','snippet':m.group(),'start':m.start(),'end':m.end(),'context':m.group(),'scope':'site_hours_not_program_intake','hard_filter_eligible':False}
                break
        m = re.search(r'\b(?:open 24 hours|24/7|24 hours)\b',hours,re.I)
        if m:
            facts['hours.continuous_site_hours_reported'] = {'field':'hours','snippet':m.group(),'start':m.start(),'end':m.end(),'context':hours,'scope':'site_hours_not_program_intake','hard_filter_eligible':False}
        else:
            m = re.search(r'(?:to|[-–])\s*(?:6|7|8|9|10|11)(?::[0-5][0-9])?\s*p\.?m\.?',hours,re.I)
            if m:
                facts['hours.evening_site_hours_reported'] = {'field':'hours','snippet':m.group(),'start':m.start(),'end':m.end(),'context':hours,'scope':'site_hours_not_program_intake','hard_filter_eligible':False}

    if not any(t.startswith('need:') for t in facts):
        flags.append('needs_human_review:no_supported_need')
    if UNCERTAIN.search(text):
        flags.append('needs_human_review:limited_or_indirect_evidence')
    if re.search(r'\b(?:permanently closed|temporarily closed|currently closed|renovation|relocated|currently undergoing)\b',text):
        flags.append('needs_human_review:operating_status')
    if re.search(r'no additional|not stated|not specified|not documented|unknown',norm(source['restrictions'])):
        notes.append('Unspecified requirements remain unknown; absence is not permission.')
    if rid in REVIEW_NOTES:
        notes.append(REVIEW_NOTES[rid])
        flags.append('needs_human_review:record_specific')
    if residential:
        notes.append('Meals, housekeeping, and transport may be bundled resident/client benefits; not general public assistance.')
    if any(e['scope'] in ('program_or_location_unconfirmed','referral_or_partner_delivery_unconfirmed') for e in facts.values()):
        flags.append('needs_human_review:service_delivery_scope')
    if re.search(r'no |not |only |except |must |required|requires|eligible|eligibility|income|sliding|medicaid|medicare|insurance|document|referral',norm(source['restrictions'])):
        flags.append('needs_human_review:eligibility_scope')
    if not source['restrictions'].strip():
        notes.append('Eligibility/restrictions not documented. Do not infer universal eligibility.')
    confidence = 'low' if not any(t.startswith('need:') for t in facts) else 'medium' if flags else 'high'
    return {'resource_id':rid,'name':source['name'],'old_tags':[],
            'old_category':source['old_category'],'new_tags':sorted(facts),
            'evidence':facts,'confidence':confidence,'review_flag':bool(flags),
            'review_reasons':sorted(set(flags)),'notes':notes,
            'approved':False,'reviewer':None,'reviewed_at':None,
            'source':source}
