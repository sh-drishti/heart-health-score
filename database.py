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

    def upsert_patient(self,patient_id, patient_profile=None):
        profile = patient_profile or {}
        update = {"active": True}

        if profile:
            update.update({
                "name": profile.get("name", ""),
                "contact": {
                    "email": profile.get("contact", {}).get("email", ""),
                    "phone": profile.get("contact", {}).get("phone", ""),
                },
                "notification_preferences": {
                    "email": bool(profile.get("notification_preferences", {}).get("email", False)),
                    "push": bool(profile.get("notification_preferences", {}).get("push", False)),
                },
                "emergency_contact": {
                    "name": profile.get("emergency_contact", {}).get("name", ""),
                    "relation": profile.get("emergency_contact", {}).get("relation", ""),
                    "contact": {
                        "email": profile.get("emergency_contact", {}).get("contact", {}).get("email", ""),
                        "phone": profile.get("emergency_contact", {}).get("contact", {}).get("phone", ""),
                    },
                },
            })

        patients_collection.update_one(
            {"patient_id":patient_id},
            {
                "$set": update,
                "$setOnInsert": {
                    "patient_id": patient_id,
                    "created_at": datetime.now(timezone.utc)
                }
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
        
    def get_patient_history(self,patient_id):
        encounters=self.get_all_encounters(patient_id)
        history=[]
        for encounter in reversed(encounters):
            assessment=encounter["payload"]["assessment"]
            domain_burdens={}
            for row in assessment["domain_rows"]:
                domain_burdens[row["Domain"]]=row["Total domain contribution"]
            
            history.append({
                "date": encounter["encounter_timestamp"],
                "visit_id": encounter["visit_id"],
                "hhs": assessment["hhs"],
                "confidence": assessment["data_confidence"],

                "total_burden": assessment["burden"]["total"],
                "main_burden": assessment["burden"]["main"],
                "treatment_burden": assessment["burden"]["treatment"],
                "interaction_burden": assessment["burden"]["interaction"],

                "domain_burdens": domain_burdens,
                "red_flags": assessment["red_flags"]
            })
        return history
    
    def get_monitoring_data(self, patient_id):
        history=self.get_patient_history(patient_id)
        if not history:
            return None
        hhs_trend=[]
        # Keyed by domain name, so this has to be a dict.
        domain_trends={}

        for encounter in history:
            hhs_trend.append({
                "date":encounter["date"],
                "visit_id":encounter["visit_id"],
                "hhs":encounter["hhs"],
                "confidence":encounter["confidence"]
            })
            for domain, burden in encounter["domain_burdens"].items():

                if domain not in domain_trends:
                    domain_trends[domain] = []

                domain_trends[domain].append({
                    "date": encounter["date"],
                    "burden": burden
                })

        latest = history[-1]

        return {
            "visit_count": len(history),
            "history": {
                "hhs_trend": hhs_trend,
                "domain_trends": domain_trends
            },
            "current": {
                "burden_breakdown": {
                    "total": latest["total_burden"],
                    "main": latest["main_burden"],
                    "treatment": latest["treatment_burden"],
                    "interaction": latest["interaction_burden"]
                },
                "red_flags": latest["red_flags"]
            },
            "insights": self.generate_trend_insights(history)
        }
        
    def generate_trend_insights(self,history):
        attention_required=[]
        positive_progress=[]
        
        if len(history)<2:
            return {
            "attention_required": attention_required,
            "positive_progress": positive_progress
        }

        oldest = history[0]
        latest = history[-1]

        hhs_change = latest["hhs"] - oldest["hhs"]

        if hhs_change >= 5:
            positive_progress.append(
                f"Heart Health Score improved by {hhs_change:.1f} points."
            )

        elif hhs_change <= -5:
            attention_required.append(
                f"Heart Health Score declined by {abs(hhs_change):.1f} points."
            )

        for domain in latest["domain_burdens"]:

            previous = oldest["domain_burdens"].get(domain, 0)
            current = latest["domain_burdens"].get(domain, 0)

            change = current - previous

            # Burden increased
            if change >= 2:
                attention_required.append(
                    f"{domain} burden increased by {change:.1f}."
                )

            # Burden decreased
            elif change <= -2:
                positive_progress.append(
                    f"{domain} burden decreased by {abs(change):.1f}."
                )

        return {
            "attention_required": attention_required,
            "positive_progress": positive_progress
        }
        
    def generate_notifications(self,history):
        notifications = []
        if len(history) ==0:
            return notifications
        
        latest=history[-1]
        notifications.append({
            "type":"assessment_complete",
            "priority":"low",
            "title": "Assessment Complete",
            "message":
                "Your Heart Health Score assessment has been completed successfully. "
                "You can now review your latest results.",
            "timestamp": datetime.now(timezone.utc)
        })
        if len(latest["red_flags"])>0:
            notifications.append({
                "type": "critical",
                "priority": "high",
                "title": "Medical Attention Recommended",
                "message":
                    "Your latest assessment identified findings that may require "
                    "prompt medical review. Please consult your healthcare provider.",
                "timestamp": datetime.now(timezone.utc)
            })
        
        elif len(history)>=2:
            previous=history[-2]
            hhs_change=previous["hhs"]-latest["hhs"]
            if hhs_change>=10:
                notifications.append({
                    "type": "critical",
                    "priority": "high",
                    "title": "Heart Health Score Decreased",
                    "message":
                        "Your Heart Health Score has decreased significantly since "
                        "your previous assessment. Please consult your healthcare provider.",
                    "timestamp": datetime.now(timezone.utc)
                })
                
        if len(history) >= 2:
            previous = history[-2]
            improvement = latest["hhs"] - previous["hhs"]
            if improvement >= 5:
                notifications.append({
                    "type": "positive",
                    "priority": "low",
                    "title": "Great Progress!",
                    "message":
                        "Your Heart Health Score has improved since your previous "
                        "assessment. Keep maintaining your healthy lifestyle.",
                    "timestamp": datetime.now(timezone.utc)
                })

        return notifications
    
    def generate_reminders(self):
        reminders = []
        all_patients = self.get_all_patients()
        for patient_id in all_patients:
            history = self.get_patient_history(patient_id)
            if len(history)==0:
                continue
            latest=history[-1]
            last_visit=latest["date"]
            days=(datetime.now(timezone.utc)-last_visit).days
            if days>=30:
                reminders.append({
                    "patient_id": patient_id,
                    "type": "reminder",
                    "priority": "medium",
                    "title": "Assessment Due",
                    "message":
                        "It has been over 30 days since your last Heart Health "
                        "assessment. Schedule your next assessment to continue "
                        "monitoring your cardiovascular health.",
                    "timestamp": datetime.now(timezone.utc)
                })
        return reminders
    
    def save_payload(self,payload, encounter_timestamp=None, patient_profile=None):
        visit=payload["visit"]
        patient_id=visit["patient_id"]
        self.upsert_patient(patient_id, patient_profile)
        timestamp=encounter_timestamp or datetime.now(timezone.utc)
        encounter={
            "patient_id":patient_id,
            "visit_id":visit["visit_id"],
            "encounter_timestamp":timestamp,
            "payload":payload
        }
        result=self.create_encounter(encounter)
        return str(result.inserted_id)
