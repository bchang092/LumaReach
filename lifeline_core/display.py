"""Small display-only typo fixes; evidence always refers to the original source."""
FIXES={1039:('It operate s the','It operates the'),1239:('Residential Services- Lebel 2','Residential Services- Level 2'),1309:('andPrint and online tools','and print and online tools')}

def description_for_display(resource_id,description):
    old,new=FIXES.get(int(resource_id),('', ''))
    return description.replace(old,new) if old else description
