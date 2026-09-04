"""Field definitions for the additional-parameter collection form.

Standalone and temporary: nothing else in the codebase imports this, and
removing the programme removes this file with it.

Ported from Data_Collection_UI_V2.py, a Tkinter desktop tool, then reworked for
the people who actually fill it in — employees, not clinicians reading off a
chart. That rework is the reason for five departures from the original:

* `description` on every field, in plain language. The original showed bare
  labels like "Diet Quality [MEPA-16 score]" to people who have never heard of
  MEPA-16.
* `group` splits the form in two, and every section belongs wholly to one.
  "self" is what anyone can answer from their own knowledge; "report" is copied
  off a lab or scan result. Eleven of these are report values, and mixing them
  in with "how many hours do you sleep" makes an ordinary person feel they are
  failing the form rather than simply not having had the test.
* Order runs easiest first. The original opened with NT-proBNP; this opens with
  height and weight, so nobody abandons it on the first question.
* Height and weight replace BMI; hip is added so waist-hip ratio can be
  computed. Nobody knows their own BMI or WHR; everybody can read a scale and a
  tape measure. Both are derived on submit and stored alongside the inputs.
* `depends_on` disables a field when an earlier answer makes it meaningless —
  pack-years for someone who has never smoked, drink type for someone who
  drinks nothing.

Numeric fields carry min/max. The desktop tool checked only that a value parsed
as a float, so a BMI of 900 was accepted.

Alcohol is volume plus what was drunk. Volume alone cannot be interpreted —
500 ml of beer and 500 ml of spirits are roughly 25 g and 160 g of alcohol —
and asking for grams of ethanol is something nobody can answer about
themselves. Two easy questions, and the conversion stays possible later.
"""

FIELDS = [   {   'key': 'height_cm',
        'label': 'Height',
        'section': 'Body Measurements',
        'kind': 'number',
        'unit': 'cm',
        'description': 'Without shoes. 5 feet 6 inches is about 168 cm.',
        'group': 'self',
        'min': 120,
        'max': 220},
    {   'key': 'weight_kg',
        'label': 'Weight',
        'section': 'Body Measurements',
        'kind': 'number',
        'unit': 'kg',
        'description': 'Your current weight.',
        'group': 'self',
        'min': 25,
        'max': 250},
    {   'key': 'waist_circumference',
        'label': 'Waist',
        'section': 'Body Measurements',
        'kind': 'number',
        'unit': 'cm',
        'description': 'At the navel, standing, after breathing out. Do not pull the tape '
                       'tight.',
        'group': 'self',
        'min': 40,
        'max': 200},
    {   'key': 'hip_circumference',
        'label': 'Hip',
        'section': 'Body Measurements',
        'kind': 'number',
        'unit': 'cm',
        'description': 'Around the widest part of the hips.',
        'group': 'self',
        'min': 50,
        'max': 200},
    {   'key': 'smoking_status',
        'label': 'Smoking Status',
        'section': 'Tobacco',
        'kind': 'choice',
        'unit': '',
        'description': 'Cigarettes, bidis, cigars or pipe. Never means you have never smoked '
                       'regularly.',
        'group': 'self',
        'choices': ['Never', 'Former', 'Current', 'Unknown']},
    {   'key': 'pack_years',
        'label': 'Pack-Years',
        'section': 'Tobacco',
        'kind': 'number',
        'unit': 'pack-years',
        'description': 'Packs a day multiplied by years smoked. Half a pack a day for 20 '
                       'years is 10.',
        'group': 'self',
        'min': 0,
        'max': 200,
        'depends_on': {   'field': 'smoking_status',
                          'disabled_when': ['Never'],
                          'value_when_disabled': 0}},
    {   'key': 'quit_duration',
        'label': 'Years Since Quitting',
        'section': 'Tobacco',
        'kind': 'number',
        'unit': 'years',
        'description': 'How long ago you stopped smoking.',
        'group': 'self',
        'min': 0,
        'max': 80,
        'depends_on': {   'field': 'smoking_status',
                          'disabled_when': ['Never', 'Current'],
                          'value_when_disabled': 0}},
    {   'key': 'physical_activity',
        'label': 'Physical Activity',
        'section': 'Daily Life',
        'kind': 'number',
        'unit': 'minutes per week',
        'description': 'Minutes a week of activity that leaves you breathing harder — brisk '
                       'walking, cycling, gym, sport. Thirty minutes on five days is 150.',
        'group': 'self',
        'min': 0,
        'max': 2000},
    {   'key': 'sleep',
        'label': 'Sleep',
        'section': 'Daily Life',
        'kind': 'number',
        'unit': 'hours per night',
        'description': 'Typical hours on a work night, not a weekend.',
        'group': 'self',
        'min': 0,
        'max': 24},
    {   'key': 'alcohol_ml',
        'label': 'Alcohol',
        'section': 'Daily Life',
        'kind': 'number',
        'unit': 'ml per week',
        'description': 'Roughly how much you drink in a typical week, by volume. A bottle of '
                       'beer is about 650 ml, a peg is 30 ml, a glass of wine about 150 ml. '
                       'Enter 0 if you do not drink.',
        'group': 'self',
        'min': 0,
        'max': 10000},
    {   'key': 'alcohol_type',
        'label': 'Usual Drink',
        'section': 'Daily Life',
        'kind': 'choice',
        'unit': '',
        'description': 'What the volume above is mostly made up of. The same volume of beer '
                       'and spirits are very different, so this is needed to make sense of '
                       'it.',
        'group': 'self',
        'choices': ['Does not drink', 'Beer', 'Wine', 'Spirits', 'Mixed', 'Unknown'],
        'depends_on': {   'field': 'alcohol_ml',
                          'disabled_when': ['0'],
                          'value_when_disabled': 'Does not drink'}},
    {   'key': 'stress_psychosocial',
        'label': 'Stress',
        'section': 'Daily Life',
        'kind': 'text',
        'unit': '',
        'description': 'In your own words — work pressure, money worries, caring for family, '
                       'anything weighing on you.',
        'group': 'self'},
    {   'key': 'diabetes_status',
        'label': 'Diabetes Status',
        'section': 'Health Background',
        'kind': 'choice',
        'unit': '',
        'description': 'As diagnosed by a doctor.',
        'group': 'self',
        'choices': ['None', 'Prediabetes', 'Diabetes', 'Unknown']},
    {   'key': 'family_history_of_premature_cvd',
        'label': 'Family History of Early Heart Disease',
        'section': 'Health Background',
        'kind': 'choice',
        'unit': '',
        'description': 'A parent, brother or sister who had a heart attack, stroke or bypass '
                       'before 55 (men) or 65 (women).',
        'group': 'self',
        'choices': ['No', 'Yes', 'Unknown']},
    {   'key': 'fasting_glucose',
        'label': 'Fasting Glucose',
        'section': 'Blood Tests',
        'kind': 'number',
        'unit': 'mg/dL',
        'description': 'Blood sugar after 8 hours without food. On a report as “Fasting '
                       'Blood Sugar” or “FBS”.',
        'group': 'report',
        'min': 20,
        'max': 600},
    {   'key': 'egfr_creatinine',
        'label': 'eGFR / Creatinine',
        'section': 'Blood Tests',
        'kind': 'number',
        'unit': 'value',
        'description': 'Kidney function. Enter whichever of the two your report shows.',
        'group': 'report',
        'min': 0,
        'max': 200},
    {   'key': 'uacr_microalbuminuria',
        'label': 'UACR / Microalbumin',
        'section': 'Blood Tests',
        'kind': 'number',
        'unit': 'mg/g',
        'description': 'Protein in urine. On a report as “urine albumin-creatinine ratio” or '
                       '“microalbumin”.',
        'group': 'report',
        'min': 0,
        'max': 5000},
    {   'key': 'nt_probnp_bnp',
        'label': 'NT-proBNP / BNP',
        'section': 'Blood Tests',
        'kind': 'number',
        'unit': 'pg/mL',
        'description': 'A blood test for strain on the heart. Not part of a routine check-up '
                       '— mark Unknown unless you have had it.',
        'group': 'report',
        'min': 0,
        'max': 35000},
    {   'key': 'hs_troponin',
        'label': 'hs-Troponin',
        'section': 'Blood Tests',
        'kind': 'number',
        'unit': 'assay value',
        'description': 'A blood test for heart muscle damage. Not routine — mark Unknown '
                       'unless you have had it.',
        'group': 'report',
        'min': 0,
        'max': 100000},
    {   'key': 'lvh',
        'label': 'LVH',
        'section': 'Heart Scans',
        'kind': 'choice',
        'unit': '',
        'description': "Thickening of the heart's main pumping chamber. An ECG or echo "
                       'report would say “LVH” or “left ventricular hypertrophy”.',
        'group': 'report',
        'choices': ['No', 'Yes', 'Unknown']},
    {   'key': 'cac',
        'label': 'Coronary Calcium Score',
        'section': 'Heart Scans',
        'kind': 'number',
        'unit': 'Agatston score',
        'description': 'From a heart CT scan. Mark Unknown unless you have had that scan.',
        'group': 'report',
        'min': 0,
        'max': 5000},
    {   'key': 'carotid_plaque',
        'label': 'Carotid Plaque',
        'section': 'Heart Scans',
        'kind': 'choice',
        'unit': '',
        'description': 'Fatty build-up in the neck arteries, seen on a carotid ultrasound.',
        'group': 'report',
        'choices': ['No', 'Yes', 'Unknown']},
    {   'key': 'abi',
        'label': 'ABI',
        'section': 'Heart Scans',
        'kind': 'number',
        'unit': 'ratio',
        'description': 'Ankle-brachial index — blood pressure at the ankle compared with the '
                       'arm. Usually around 1.0.',
        'group': 'report',
        'min': 0,
        'max': 2.0},
    {   'key': 'cardiorespiratory_fitness',
        'label': 'Cardiorespiratory Fitness',
        'section': 'Other Tests & Scores',
        'kind': 'number',
        'unit': 'METs',
        'description': 'From a treadmill or exercise stress test. Mark Unknown unless you '
                       'have had one.',
        'group': 'report',
        'min': 0,
        'max': 25},
    {   'key': 'heart_rate_recovery',
        'label': 'Heart Rate Recovery',
        'section': 'Other Tests & Scores',
        'kind': 'number',
        'unit': 'bpm',
        'description': 'How far your heart rate falls one minute after stopping an exercise '
                       'test.',
        'group': 'report',
        'min': 0,
        'max': 100},
    {   'key': 'diet_quality',
        'label': 'Diet Quality (MEPA-16)',
        'section': 'Other Tests & Scores',
        'kind': 'number',
        'unit': 'score',
        'description': 'Your score from the MEPA-16 diet questionnaire. If you have not '
                       'filled one in, mark Unknown.',
        'group': 'report',
        'min': 0,
        'max': 16},
    {   'key': 'genetic_risk',
        'label': 'Genetic Risk Score',
        'section': 'Other Tests & Scores',
        'kind': 'number',
        'unit': 'score or percentile',
        'description': 'From a genetic risk report. Most people have never had one — mark '
                       'Unknown.',
        'group': 'report',
        'min': 0,
        'max': 100}]


FIELDS_BY_KEY = {field["key"]: field for field in FIELDS}

SECTIONS: list[str] = []
for _field in FIELDS:
    if _field["section"] not in SECTIONS:
        SECTIONS.append(_field["section"])

GROUP_NOTES = {
    "self": "Answer these from what you already know. No report needed.",
    "report": (
        "Copy these from a recent health check-up or lab report. If you have "
        "not had a test, mark it Unknown \u2014 that is expected, and most "
        "people will mark several."
    ),
}


def schema() -> dict:
    """The form definition the browser renders."""

    return {
        "sections": [
            {
                "section": section,
                "group": next(f["group"] for f in FIELDS if f["section"] == section),
                "fields": [f for f in FIELDS if f["section"] == section],
            }
            for section in SECTIONS
        ],
        "groups": GROUP_NOTES,
        "field_count": len(FIELDS),
    }
