from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime, timezone

load_dotenv()

client=MongoClient(os.getenv("MONGODB_URI"))
db=client[os.getenv("DATABASE_NAME")]

patients_collection=db["patients"]
encounters_collection=db["encounters"]

class EncounterRepository:
    def __init__(self):
        pass
    
    def patient_exists(self,patient_id):
        return patients_collection.find_one({"patient_id":patient_id}) is not None

    def create_patient(self,patient_id):
        patients_collection.insert_one({
            "patient_id":patient_id,
            "created_at":datetime.now(timezone.utc),
            "active":True
        })

    def upsert_patient(self,patient_id):
        patients_collection.update_one(
            {"patient_id":patient_id},
            {
                "$set": {"active": True},
                "$setOnInsert": {"created_at": datetime.now(timezone.utc)}
            },
            upsert=True
        )

    def create_encounter(self,encounter):
        return encounters_collection.insert_one(encounter)
    
    def get_payload(self, patient_id, visit_id=None):
        
        if visit_id is None:
            encounter=self.get_latest_encounter(patient_id)
        else:
            encounter=encounters_collection.find_one(
                {"patient_id":patient_id,
                "visit_id":visit_id}
            )
        if encounter is None:
            return None
        return encounter["payload"]
        
    def get_latest_encounter(self, patient_id):
        return encounters_collection.find_one(
            {"patient_id": patient_id},
            sort=[("encounter_timestamp", -1)]
        )
    
    def get_all_patients(self):
        patients=patients_collection.find(
            {},
            {"_id":0, "patient_id":1}
        )
        return [patient["patient_id"] for patient in patients]
    
    def get_all_encounters(self, patient_id):
        return list(
            encounters_collection.find(
                {"patient_id":patient_id}
            ).sort("encounter_timestamp",-1)
        )
    
    def save_payload(self,payload, encounter_timestamp=None):
        visit=payload["visit"]
        patient_id=visit["patient_id"]
        self.upsert_patient(patient_id)
        timestamp=encounter_timestamp or datetime.now(timezone.utc)
        encounter={
            "patient_id":patient_id,
            "visit_id":visit["visit_id"],
            "encounter_timestamp":timestamp,
            "payload":payload
        }
        result=self.create_encounter(encounter)
        return str(result.inserted_id)
    
