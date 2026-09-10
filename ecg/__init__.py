"""ECG interpretation from five interval measurements.

Standalone: no patient record is read or written, nothing is stored, and
nothing here is imported by the scoring engine or the clinical API. The model
artefact and its thresholds belong to the data science team; this package wraps
them in an endpoint and a form and does not alter their behaviour.
"""
