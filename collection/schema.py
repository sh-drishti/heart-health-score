"""Field definitions for the additional-parameter collection form.

Standalone and temporary: nothing else in the codebase imports this, and
removing the programme removes this file with it.

Ported from Data_Collection_UI_V2.py, a Tkinter desktop tool, then reworked for
the people who actually fill it in — employees, not clinicians reading off a
chart. What that rework changed, and why:

* Identity is a single code, mailed to the participant. The desktop tool asked
  for a full name and an employee code; a form that collects health answers
  should ask for as little identifying detail as it can get away with, and one
  code is enough to attach a correction to the right record.

* Sections carry `info`, `accent` and `optional`, and fields carry
  `description` and `placeholder`. The original showed bare labels like
  "Diet Quality [MEPA-16 score]" to people who have never heard of MEPA-16, all
  in one undifferentiated column.

* The three `report` sections are optional. Eleven of these values come off a
  lab or scan report, and requiring an explicit "Unknown" for each one made a
  person who simply has not had those tests work through eleven refusals. Left
  blank, they are stored exactly as Unknown was — so the data means the same
  thing, and only the number of clicks changed.

* Cigarettes per day and years smoked replace pack-years, which is jargon
  nobody applies to themselves. Pack-years is computed on submit at twenty
  cigarettes to the pack. Height and weight likewise replace BMI, and hip is
  asked so waist-hip ratio can be derived.

* `depends_on` disables a field when an earlier answer makes it meaningless.

* Order runs easiest first. The original opened with NT-proBNP.

Numeric fields carry min/max. The desktop tool checked only that a value parsed
as a float, so a BMI of 900 was accepted.

Alcohol is volume plus what is drunk, because volume alone cannot be
interpreted — 500 ml of beer and 500 ml of spirits are roughly 25 g and 160 g
of alcohol — and nobody can report grams of ethanol about themselves.
"""

SECTION_META = [   {   'section': 'Body Measurements',
        'group': 'self',
        'accent': 'sky',
        'info': 'Measure yourself at home. A tape measure and a weighing scale are all you '
                'need.',
        'optional': False},
    {   'section': 'Tobacco',
        'group': 'self',
        'accent': 'amber',
        'info': 'If you have never smoked, answer the first question and the rest will be '
                'skipped automatically.',
        'optional': False},
    {   'section': 'Daily Life',
        'group': 'self',
        'accent': 'emerald',
        'info': 'Roughly is fine. A typical week is more useful than an exact one.',
        'optional': False},
    {   'section': 'Health Background',
        'group': 'self',
        'accent': 'violet',
        'info': 'Only what a doctor has actually told you. If you are unsure, choose '
                'Unknown.',
        'optional': False},
    {   'section': 'Blood Tests',
        'group': 'report',
        'accent': 'rose',
        'info': 'All optional. Copy any you have from a recent blood report and leave the '
                'rest blank.',
        'optional': True},
    {   'section': 'Heart Scans',
        'group': 'report',
        'accent': 'indigo',
        'info': 'All optional. Only if you have had these scans — most people have not.',
        'optional': True},
    {   'section': 'Other Tests & Scores',
        'group': 'report',
        'accent': 'teal',
        'info': 'All optional. These come from specialist tests or questionnaires.',
        'optional': True}]

FIELDS = [   {   'key': 'height_cm',
        'label': 'Height',
        'section': 'Body Measurements',
        'kind': 'number',
        'unit': 'cm',
        'description': 'Without shoes. 5 feet 6 inches is about 168 cm.',
        'placeholder': '170',
        'min': 120,
        'max': 220},
    {   'key': 'weight_kg',
        'label': 'Weight',
        'section': 'Body Measurements',
        'kind': 'number',
        'unit': 'kg',
        'description': 'Your current weight.',
        'placeholder': '72',
        'min': 25,
        'max': 250},
    {   'key': 'waist_circumference',
        'label': 'Waist',
        'section': 'Body Measurements',
        'kind': 'number',
        'unit': 'cm',
        'description': 'At the navel, standing, after breathing out. Do not pull the tape '
                       'tight.',
        'placeholder': '88',
        'min': 40,
        'max': 200},
    {   'key': 'hip_circumference',
        'label': 'Hip',
        'section': 'Body Measurements',
        'kind': 'number',
        'unit': 'cm',
        'description': 'Around the widest part of the hips.',
        'placeholder': '98',
        'min': 50,
        'max': 200},
    {   'key': 'smoking_status',
        'label': 'Smoking Status',
        'section': 'Tobacco',
        'kind': 'choice',
        'unit': '',
        'description': 'Cigarettes, bidis, cigars or pipe. Never means you have never smoked '
                       'regularly.',
        'placeholder': '',
        'choices': ['Never', 'Former', 'Current', 'Unknown']},
    {   'key': 'cigarettes_per_day',
        'label': 'Cigarettes per Day',
        'section': 'Tobacco',
        'kind': 'number',
        'unit': 'cigarettes',
        'description': 'On a typical day when you smoked. Count bidis the same as '
                       'cigarettes.',
        'placeholder': '10',
        'min': 0,
        'max': 100,
        'depends_on': {   'field': 'smoking_status',
                          'disabled_when': ['Never'],
                          'value_when_disabled': 0}},
    {   'key': 'years_smoked',
        'label': 'Years Smoked',
        'section': 'Tobacco',
        'kind': 'number',
        'unit': 'years',
        'description': 'Total number of years you have smoked, all together.',
        'placeholder': '12',
        'min': 0,
        'max': 80,
        'depends_on': {   'field': 'smoking_status',
                          'disabled_when': ['Never'],
                          'value_when_disabled': 0}},
    {   'key': 'quit_duration',
        'label': 'Years Since Quitting',
        'section': 'Tobacco',
        'kind': 'number',
        'unit': 'years',
        'description': 'How long ago you stopped smoking.',
        'placeholder': '6',
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
        'placeholder': '150',
        'min': 0,
        'max': 2000},
    {   'key': 'sleep',
        'label': 'Sleep',
        'section': 'Daily Life',
        'kind': 'number',
        'unit': 'hours per night',
        'description': 'Typical hours on a work night, not a weekend.',
        'placeholder': '7',
        'min': 0,
        'max': 24},
    {   'key': 'alcohol_ml',
        'label': 'Alcohol',
        'section': 'Daily Life',
        'kind': 'number',
        'unit': 'ml per week',
        'description': 'How much you drink in a typical week, by volume. A bottle of beer is '
                       'about 650 ml, a peg is 30 ml, a glass of wine about 150 ml. Enter 0 '
                       'if you do not drink.',
        'placeholder': '0',
        'min': 0,
        'max': 10000},
    {   'key': 'alcohol_type',
        'label': 'Usual Drink',
        'section': 'Daily Life',
        'kind': 'choice',
        'unit': '',
        'description': 'What that volume is mostly made up of. The same volume of beer and '
                       'spirits are very different amounts of alcohol.',
        'placeholder': '',
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
        'placeholder': 'Long hours, poor sleep on weeknights'},
    {   'key': 'diabetes_status',
        'label': 'Diabetes Status',
        'section': 'Health Background',
        'kind': 'choice',
        'unit': '',
        'description': 'As diagnosed by a doctor.',
        'placeholder': '',
        'choices': ['None', 'Prediabetes', 'Diabetes', 'Unknown']},
    {   'key': 'family_history_of_premature_cvd',
        'label': 'Family History of Early Heart Disease',
        'section': 'Health Background',
        'kind': 'choice',
        'unit': '',
        'description': 'A parent, brother or sister who had a heart attack, stroke or bypass '
                       'before 55 (men) or 65 (women).',
        'placeholder': '',
        'choices': ['No', 'Yes', 'Unknown']},
    {   'key': 'fasting_glucose',
        'label': 'Fasting Glucose',
        'section': 'Blood Tests',
        'kind': 'number',
        'unit': 'mg/dL',
        'description': 'Blood sugar after 8 hours without food. On a report as “Fasting '
                       'Blood Sugar” or “FBS”.',
        'placeholder': '95',
        'min': 20,
        'max': 600},
    {   'key': 'egfr_creatinine',
        'label': 'eGFR / Creatinine',
        'section': 'Blood Tests',
        'kind': 'number',
        'unit': 'value',
        'description': 'Kidney function. Enter whichever of the two your report shows.',
        'placeholder': '90',
        'min': 0,
        'max': 200},
    {   'key': 'uacr_microalbuminuria',
        'label': 'UACR / Microalbumin',
        'section': 'Blood Tests',
        'kind': 'number',
        'unit': 'mg/g',
        'description': 'Protein in urine. On a report as “urine albumin-creatinine ratio” or '
                       '“microalbumin”.',
        'placeholder': '12',
        'min': 0,
        'max': 5000},
    {   'key': 'nt_probnp_bnp',
        'label': 'NT-proBNP / BNP',
        'section': 'Blood Tests',
        'kind': 'number',
        'unit': 'pg/mL',
        'description': 'A blood test for strain on the heart. Not part of a routine '
                       'check-up.',
        'placeholder': '40',
        'min': 0,
        'max': 35000},
    {   'key': 'hs_troponin',
        'label': 'hs-Troponin',
        'section': 'Blood Tests',
        'kind': 'number',
        'unit': 'assay value',
        'description': 'A blood test for heart muscle damage. Not routine.',
        'placeholder': '3',
        'min': 0,
        'max': 100000},
    {   'key': 'lvh',
        'label': 'LVH',
        'section': 'Heart Scans',
        'kind': 'choice',
        'unit': '',
        'description': "Thickening of the heart's main pumping chamber. An ECG or echo "
                       'report would say “LVH”.',
        'placeholder': '',
        'choices': ['No', 'Yes', 'Unknown']},
    {   'key': 'cac',
        'label': 'Coronary Calcium Score',
        'section': 'Heart Scans',
        'kind': 'number',
        'unit': 'Agatston score',
        'description': 'From a heart CT scan.',
        'placeholder': '0',
        'min': 0,
        'max': 5000},
    {   'key': 'carotid_plaque',
        'label': 'Carotid Plaque',
        'section': 'Heart Scans',
        'kind': 'choice',
        'unit': '',
        'description': 'Fatty build-up in the neck arteries, seen on a carotid ultrasound.',
        'placeholder': '',
        'choices': ['No', 'Yes', 'Unknown']},
    {   'key': 'abi',
        'label': 'ABI',
        'section': 'Heart Scans',
        'kind': 'number',
        'unit': 'ratio',
        'description': 'Ankle-brachial index — ankle blood pressure compared with the arm. '
                       'Usually around 1.0.',
        'placeholder': '1.05',
        'min': 0,
        'max': 2.0},
    {   'key': 'cardiorespiratory_fitness',
        'label': 'Cardiorespiratory Fitness',
        'section': 'Other Tests & Scores',
        'kind': 'number',
        'unit': 'METs',
        'description': 'From a treadmill or exercise stress test.',
        'placeholder': '9',
        'min': 0,
        'max': 25},
    {   'key': 'heart_rate_recovery',
        'label': 'Heart Rate Recovery',
        'section': 'Other Tests & Scores',
        'kind': 'number',
        'unit': 'bpm',
        'description': 'How far your heart rate falls one minute after stopping an exercise '
                       'test.',
        'placeholder': '18',
        'min': 0,
        'max': 100},
    {   'key': 'diet_quality',
        'label': 'Diet Quality (MEPA-16)',
        'section': 'Other Tests & Scores',
        'kind': 'number',
        'unit': 'score',
        'description': 'Your score from the MEPA-16 diet questionnaire.',
        'placeholder': '9',
        'min': 0,
        'max': 16},
    {   'key': 'genetic_risk',
        'label': 'Genetic Risk Score',
        'section': 'Other Tests & Scores',
        'kind': 'number',
        'unit': 'score or percentile',
        'description': 'From a genetic risk report.',
        'placeholder': '50',
        'min': 0,
        'max': 100}]


FIELDS_BY_KEY = {field["key"]: field for field in FIELDS}
SECTION_BY_NAME = {s["section"]: s for s in SECTION_META}

#: Keys the participant may leave blank. Stored as Unknown when they do.
OPTIONAL_KEYS = {
    field["key"]
    for field in FIELDS
    if SECTION_BY_NAME[field["section"]]["optional"]
}

GROUP_NOTES = {
    "self": "Answer these from what you already know. No report needed.",
    "report": (
        "All optional. Copy across anything you have from a recent health "
        "check-up and leave the rest blank."
    ),
}


def schema() -> dict:
    """The form definition the browser renders."""

    return {
        "sections": [
            {**meta, "fields": [f for f in FIELDS if f["section"] == meta["section"]]}
            for meta in SECTION_META
        ],
        "groups": GROUP_NOTES,
        "field_count": len(FIELDS),
        "required_count": len(FIELDS) - len(OPTIONAL_KEYS),
    }
