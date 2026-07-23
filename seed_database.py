import json
from database import EncounterRepository

repo=EncounterRepository()
with open("data\hhs_encounter_payload.json","r") as f:
    payload=json.load(f)
    
repo.save_payload(payload)

print("Encounter successfully inserted.")   