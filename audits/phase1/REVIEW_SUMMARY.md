# Phase 1 review summary

The source workbook and reliability metadata are unchanged. No proposed tag is approved or active.

| Measure | Count |
|---|---:|
| Resources | 1,362 |
| Proposed tag changes | 1,262 |
| Flagged for review | 725 |
| No supported need assigned | 100 |
| Need categories | 26 |
| Service subtypes | 68 |
| Constraint/access tags | 44 |

Flag reasons can overlap. Confidence is about tag evidence, not the scraped reliability score. High: 637; medium: 625; low: 100.

## Need taxonomy

Each subtype below has at least one supporting source description. Counts overlap across services.

| Category | Subtypes and resource counts |
|---|---|
| benefits | enrollment navigation (20) |
| care | adult day (50), assisted living (146), home (66), hospice palliative (13), memory (46), residential unspecified (11), respite (30), skilled nursing (83) |
| childcare | early learning (15) |
| community | social recreation (66) |
| crisis | intervention (28) |
| digital | computers internet (34) |
| disability | independent living (36) |
| disaster | preparedness (2) |
| education | learning (64) |
| employment | training search (90) |
| essentials | clothing supplies (49) |
| family | youth parenting (43) |
| financial | counseling (7), disaster grants (1), emergency assistance (20), tax help (6) |
| food | delivery (8), general assistance (31), medically tailored (4), pantry (115), prepared meals (32) |
| housing | accessibility modifications (4), counseling navigation (36), emergency shelter (18), homeownership repairs (14), medical lodging (2), rent eviction help (15), rental (172), supportive transitional (41) |
| immigration | support (11) |
| language | interpretation (7) |
| legal | advocacy information (9), assistance (41), civil aid (2), criminal defense (13), elder estate (2), expungement (1), housing disputes (2), identity documents (6), immigration (4) |
| medical | cost assistance (6), dental (11), emergency (29), equipment (17), general (109), patient support (6), prescriptions (21), rehabilitation (75), sexual reproductive (22) |
| mental health | clinical (238), peer support (24) |
| navigation | case management (92) |
| pets | food veterinary (4) |
| safety | child protection (5), survivor support (16) |
| substance use | detox (6), harm reduction (4), medications (14), treatment (90) |
| transportation | assistance (42) |
| utilities | bill assistance (15) |

## Constraint taxonomy

All are reported, program-scoped facts requiring confirmation before hard eligibility filtering. Site hours are not program hours.

| Tag | Resources |
|---|---:|
| `access.appointment_reported` | 158 |
| `access.referral_required_reported` | 6 |
| `access.telehealth_reported` | 57 |
| `access.walk_in_reported` | 14 |
| `accessibility.accessible_units_reported` | 5 |
| `accessibility.wheelchair_entrance_reported` | 118 |
| `accessibility.wheelchair_parking_reported` | 49 |
| `accessibility.wheelchair_transport_reported` | 3 |
| `age.adults_served` | 257 |
| `age.all_ages_reported` | 30 |
| `age.children_served` | 148 |
| `age.older_adults_served` | 231 |
| `age.threshold_reported` | 109 |
| `age.youth_served` | 124 |
| `cost.free_program_reported` | 46 |
| `cost.low_cost_reported` | 4 |
| `cost.private_pay_reported` | 29 |
| `cost.sliding_scale_reported` | 19 |
| `documents.requirements_reported` | 2 |
| `eligibility.income_condition_reported` | 31 |
| `food.client_choice_reported` | 7 |
| `food.drive_through_reported` | 7 |
| `food.fresh_produce_reported` | 5 |
| `food.frozen_items_reported` | 4 |
| `food.nonperishable_reported` | 6 |
| `food.pet_food_reported` | 2 |
| `hours.continuous_site_hours_reported` | 203 |
| `hours.evening_site_hours_reported` | 224 |
| `hours.weekend_site_hours_reported` | 452 |
| `insurance.carefirst_reported` | 3 |
| `insurance.medicaid_reported` | 35 |
| `insurance.medicare_reported` | 13 |
| `language.asl_reported` | 5 |
| `language.english_reported` | 1 |
| `language.spanish_reported` | 1 |
| `population.disabilities_served` | 64 |
| `population.homelessness_served` | 13 |
| `population.immigrants_served` | 5 |
| `population.veterans_served` | 35 |
| `service_area.baltimore_city_reported` | 11 |
| `service_area.baltimore_county_reported` | 2 |
| `service_area.local_restriction_reported` | 6 |
| `service_area.maryland_reported` | 16 |
| `service_area.nationwide_reported` | 6 |

## Verification

24 test methods passed, including 2,000 generated rule variants and 4,928 source-evidence checks. 64 independently written evaluation inputs (10 crisis cases) are prepared but have not been run against a matching engine. No MCP server or website changes were implemented during this proposal phase.

See README.md for review and migration instructions, and ../../docs/TRIAGE_DESIGN.md for the pipeline, interface, privacy and curation design.
