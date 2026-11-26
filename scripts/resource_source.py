"""Read the authoritative workbook without saving or recalculating it."""
import hashlib
import json
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
SEPTEMBER_MASTER = ROOT / 'input_data/09092026_MASTER_SHEET.xlsx'
MASTER = ROOT / 'input_data/11242026_ReverificationMASTER_SHEET.xlsx'
SHEET = 'Sheet1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def read_source(path=MASTER):
    path = Path(path)
    before = digest(path.read_bytes())
    book = load_workbook(path, read_only=True, data_only=True)
    records = []
    try:
        values = book['Scraper-Verified' if path.name == SEPTEMBER_MASTER.name else SHEET].values
        headers = next(values)
        for sheet_row, values_row in enumerate(values, 2):
            if not any(v is not None for v in values_row):
                continue
            row = dict(zip(headers, values_row))
            raw_id = row['ID']
            if isinstance(raw_id, bool) or float(raw_id) != int(raw_id):
                raise ValueError(f'Non-integer resource ID at row {sheet_row}')
            record = {'resource_id':int(raw_id),'sheet_row':sheet_row,
                      'name':str(row['Name of Service'] or '').strip(),
                      'description':str(row['Description'] or '').strip(),
                      'restrictions':str(row['Restrictions of Service'] or '').strip(),
                      'hours':str(row['Days of Service'] or '').strip(),
                      'old_category':str(row['Cateogry of Help'] or '').strip(),
                      'address':row['Address'], 'latitude':row['Latitude'],
                      'longitude':row['Longitude'], 'phone':row['Phone Number'],
                      'website':row['link to site'],
                      'protected_metadata':{k:row[k] for k in (
                          'Reliability Description','Reliability Score','Confidence',
                          'Confidence Details','Date Verified','Classification')}}
            if 'Call experience' in row:
                record['call_experience'] = row['Call experience']
            record['record_sha256'] = digest(json_bytes(record))
            records.append(record)
    finally:
        book.close()
    if digest(path.read_bytes()) != before:
        raise ValueError('Workbook changed while reading; rerun audit against one snapshot')
    ids = [r['resource_id'] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate resource IDs')
    return before, records
