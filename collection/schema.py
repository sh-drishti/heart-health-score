"""Field definitions for the additional-parameter collection form.

Ported from Data_Collection_UI_V2.py, a Tkinter desktop tool that wrote to a
local CSV. The parameter labels are the canonical HHS R37 terminology and are
reproduced verbatim; `key` is added here because the CSV was keyed by label and
a JSON API needs a stable identifier that does not change when a label is
reworded.

Two things differ from the desktop original, both deliberate:

* Numeric fields carry `min` and `max`. The desktop tool validated only that a
  value parsed as a float, so a BMI of 900 was accepted.
* Every field keeps its "must be answered" rule: a value, or an explicit
  Unknown. There are no healthy defaults and no silent blanks — see
  validate_submission.

This package is self-contained on purpose. The programme it serves is
temporary; removing it is `rm -rf collection/` plus one line in backend/main.py.
"""

FIELDS = [   {   'key': 'lvh',
        'label': 'LVH',
        'section': 'Direct Cardiovascular Evidence',
        'kind': 'choice',
        'unit': '',
        'choices': ['No', 'Yes', 'Unknown']},
    {   'key': 'smoking_status',
        'label': 'Smoking Status',
        'section': 'Tobacco Exposure',
        'kind': 'choice',
        'unit': '',
        'choices': ['Never', 'Former', 'Current', 'Unknown']},
    {   'key': 'pack_years',
        'label': 'Pack-Years',
        'section': 'Tobacco Exposure',
        'kind': 'number',
        'unit': 'pack-years',
        'min': 0,
        'max': 200},
    {   'key': 'quit_duration',
        'label': 'Quit Duration',
        'section': 'Tobacco Exposure',
        'kind': 'number',
        'unit': 'years',
        'min': 0,
        'max': 80},
    {   'key': 'diabetes_status',
        'label': 'Diabetes Status',
        'section': 'Glycemic / Diabetes State',
        'kind': 'choice',
        'unit': '',
        'choices': ['None', 'Prediabetes', 'Diabetes', 'Unknown']},
    {   'key': 'fasting_glucose',
        'label': 'Fasting Glucose',
        'section': 'Glycemic / Diabetes State',
        'kind': 'number',
        'unit': 'mg/dL',
        'min': 20,
        'max': 600},
    {   'key': 'bmi',
        'label': 'BMI',
        'section': 'Adiposity',
        'kind': 'number',
        'unit': 'kg/m²',
        'min': 10,
        'max': 70},
    {   'key': 'waist_circumference',
        'label': 'Waist Circumference',
        'section': 'Adiposity',
        'kind': 'number',
        'unit': 'cm',
        'min': 30,
        'max': 200},
    {   'key': 'whr',
        'label': 'WHR',
        'section': 'Adiposity',
        'kind': 'number',
        'unit': 'ratio',
        'min': 0.4,
        'max': 2.0},
    {   'key': 'family_history_of_premature_cvd',
        'label': 'Family History of Premature CVD',
        'section': 'Context / Predisposition',
        'kind': 'choice',
        'unit': '',
        'choices': ['No', 'Yes', 'Unknown']},
    {   'key': 'genetic_risk',
        'label': 'Genetic Risk',
        'section': 'Context / Predisposition',
        'kind': 'number',
        'unit': 'score / percentile',
        'min': 0,
        'max': 100},
    {   'key': 'egfr_creatinine',
        'label': 'eGFR / Creatinine',
        'section': 'Kidney State',
        'kind': 'number',
        'unit': 'value',
        'min': 0,
        'max': 200},
    {   'key': 'uacr_microalbuminuria',
        'label': 'UACR / Microalbuminuria',
        'section': 'Kidney State',
        'kind': 'number',
        'unit': 'mg/g',
        'min': 0,
        'max': 5000},
    {   'key': 'physical_activity',
        'label': 'Physical Activity',
        'section': 'Physical Activity',
        'kind': 'number',
        'unit': 'moderate-equivalent min/week',
        'min': 0,
        'max': 2000},
    {   'key': 'diet_quality',
        'label': 'Diet Quality',
        'section': 'Diet Quality',
        'kind': 'number',
        'unit': 'MEPA-16 score',
        'min': 0,
        'max': 16},
    {   'key': 'alcohol',
        'label': 'Alcohol',
        'section': 'Alcohol Exposure',
        'kind': 'number',
        'unit': 'g ethanol/day',
        'min': 0,
        'max': 500},
    {   'key': 'sleep',
        'label': 'Sleep',
        'section': 'Sleep Health',
        'kind': 'number',
        'unit': 'hours/night',
        'min': 0,
        'max': 24},
    {   'key': 'stress_psychosocial',
        'label': 'Stress / Psychosocial',
        'section': 'Context / Predisposition',
        'kind': 'text',
        'unit': 'score / context'},
    {   'key': 'nt_probnp_bnp',
        'label': 'NT-proBNP / BNP',
        'section': 'Direct Cardiovascular Evidence',
        'kind': 'number',
        'unit': 'pg/mL',
        'min': 0,
        'max': 35000},
    {   'key': 'hs_troponin',
        'label': 'hs-Troponin',
        'section': 'Direct Cardiovascular Evidence',
        'kind': 'number',
        'unit': 'assay value',
        'min': 0,
        'max': 100000},
    {   'key': 'cac',
        'label': 'CAC',
        'section': 'Direct Cardiovascular Evidence',
        'kind': 'number',
        'unit': 'Agatston score',
        'min': 0,
        'max': 5000},
    {   'key': 'carotid_plaque',
        'label': 'Carotid Plaque',
        'section': 'Direct Cardiovascular Evidence',
        'kind': 'choice',
        'unit': '',
        'choices': ['No', 'Yes', 'Unknown']},
    {   'key': 'abi',
        'label': 'ABI',
        'section': 'Direct Cardiovascular Evidence',
        'kind': 'number',
        'unit': 'ratio',
        'min': 0,
        'max': 2.0},
    {   'key': 'cardiorespiratory_fitness',
        'label': 'Cardiorespiratory Fitness',
        'section': 'Cardiorespiratory Functional State',
        'kind': 'number',
        'unit': 'MET',
        'min': 0,
        'max': 25},
    {   'key': 'heart_rate_recovery',
        'label': 'Heart Rate Recovery',
        'section': 'Cardiorespiratory Functional State',
        'kind': 'number',
        'unit': 'bpm',
        'min': 0,
        'max': 100}]


FIELDS_BY_KEY = {field["key"]: field for field in FIELDS}

# Section order is the order fields are declared, which is the order the desktop
# form presented them. Clinicians filling this in are used to that sequence.
SECTIONS: list[str] = []
for _field in FIELDS:
    if _field["section"] not in SECTIONS:
        SECTIONS.append(_field["section"])


def schema() -> dict:
    """The form definition the browser renders. Sections in presentation order."""

    return {
        "sections": [
            {
                "section": section,
                "fields": [f for f in FIELDS if f["section"] == section],
            }
            for section in SECTIONS
        ],
        "field_count": len(FIELDS),
    }
