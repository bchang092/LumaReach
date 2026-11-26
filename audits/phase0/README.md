# Original stack and questionnaire

Django 5.2.6 / Python 3.13, Django templates, vanilla JavaScript, Leaflet/OpenStreetMap. Django SQLite locally; DATABASE_URL selects PostgreSQL in deployment. Public resource records come directly from the 17-column Excel sheet, not SQL. SQLite originally stored public community feedback and rate-limit state.

`map/views.py:_load_resources_from_xlsx` reads `input_data/09092026_MASTER_SHEET.xlsx`, worksheet `Scraper-Verified`. It supported Tag_List / Tag_01–25, but this workbook has none. All 1,362 resources had zero actual tags; zero had one tag. Broad category labels are exported separately from tags.

The original questionnaire is `templates/questionnaire.html`, handled by `map/views.py:questionnaire_page`, and ranked through `map/triage.py`. It collects optional GPS coordinates, travel mode, health-support and document-help selections, and the questions below. Missing answers originally received defaults, including negative crisis answers; the new free-text pipeline does not infer missing answers. The fallback questionnaire remains available.

- travel_access: Travel access
- immediate_danger: Immediate danger
- mental_health_crisis: Mental health crisis
- unsafe_home: Unsafe home
- safe_place_tonight: Safe place to sleep tonight
- food_today: Enough food for today
- housing_risk: Housing risk
- utilities_help: Utilities or bills help
- transportation_needed: Transportation needed
- essential_supplies: Essential supplies needed
- employment_help: Employment help
- family_support: Child or family support
- senior_support: Senior support
- disability_support: Disability or accessibility support
- resource_navigation: General resource navigation

`recon.json` contains full zero-tag inventory, counts and five complete original records (all 17 columns). This export was written after Phase 0, using the unchanged workbook.
