from datetime import datetime, timedelta, timezone
from database import notifications_collection, EncounterRepository
from pymongo import ReturnDocument
import os

import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv
load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))


class NotificationService:  
    def __init__(self, repository=None):
        if repository is None:
            repository = EncounterRepository()
        self.repository = repository
    
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
        all_patients = self.repository.get_all_patients()
        for patient_id in all_patients:
            history = self.repository.get_patient_history(patient_id)
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
        
    def save_notification(self, patient_id, notifications):
        notification_ids=[]
        for notification in notifications:
            document={
                "patient_id": patient_id,
                "type": notification["type"],
                "priority": notification["priority"],
                "title":notification["title"],
                "message": notification["message"],
                "created_at": notification.get("timestamp", datetime.now(timezone.utc)),
                 "delivery": {
                    "email": {
                        "status": "pending",
                        "sent_at": None,
                        "error": None
                    },
                    "push": {
                        "status": "pending",
                        "sent_at": None,
                        "error": None
                    }
                },
                 "read": False
            }
            result = notifications_collection.insert_one(document)
            notification_ids.append(result.inserted_id)
        return notification_ids
    
    def get_notification(self,notification_id):
        return notifications_collection.find_one({"_id": notification_id})
    
    def update_notification_status(self, notification_id, channel, status, error=None):
        notifications_collection.update_one(
            {"_id": notification_id},
            {
                "$set": {
                    f"delivery.{channel}.status": status,
                    f"delivery.{channel}.sent_at": datetime.now(timezone.utc),
                    f"delivery.{channel}.error": error
                }
            }
        )
        
    def get_pending_notifications(self):
        return list(notifications_collection.find({"delivery.email.status": "pending",}))
        
    def process_assessment(self, patient_id):
        history = self.repository.get_patient_history(patient_id)
        notifications = self.generate_notifications(history)
        if len(notifications)==0:
            return
        
        notification_ids = self.save_notification(patient_id, notifications)
        self.dispatch_notifications(notification_ids)
        
    def process_reminders(self):
        reminders = self.generate_reminders()
        if len(reminders)==0:
            return
        for reminder in reminders:
            ids=self.save_notification(reminder["patient_id"], [reminder])
            self.dispatch_notifications(ids)
            
    def dispatch_notifications(self, notification_ids):
        if len(notification_ids)==0:
            return
        notifications=[]
        
        for notification_id in notification_ids:
            notification=self.get_notification(notification_id)
            if notification:
                notifications.append(notification)
        if len(notifications)==0:
            return
        
        patient=self.repository.get_patient(notifications[0]["patient_id"])
        if patient is None:
            return
        
        preferences=patient.get("notification_preferences",{})
        email_success=False
        if preferences.get("email", False):
            email_success = self.send_email(
                recipient=patient["contact"]["email"],
                subject=self.build_email_subject(notifications),
                body=self.build_email_body(
                    notifications,
                    patient,
                )
            )
        
        has_critical = any(
            notification["type"] == "critical"
            for notification in notifications
        )

        if has_critical:
            emergency = patient.get( "emergency_contact", {})
            emergency_email = emergency.get("contact",  {}).get("email" )

            if emergency_email:
                self.send_email(
                    recipient=emergency_email,
                    subject="Critical Heart Health Alert",
                    body=self.build_emergency_email(patient)
                )
                
        for notification_id in notification_ids:
            if email_success:
                self.update_notification_status(notification_id, channel="email", status="sent")
            else:
                self.update_notification_status(notification_id, channel="email", status="failed", error="Email sending failed.")
                
        if preferences.get("push", False):
            for notification in notifications:
                self.send_push_notification(notification)
                
    def build_email_subject(self, notifications):
        """
        Build a single subject for the assessment summary email.
        """
        notification_types = {n["type"] for n in notifications}
        if "critical" in notification_types:
            return "Heart Health Assessment Alert"
        return "Heart Health Assessment Update"
    
    def build_email_body(self, notifications, patient):
        """
        Builds a single assessment summary email.
        """
        patient_name = patient.get("name", "Patient")
        lines = []
        lines.append(f"Dear {patient_name},")
        lines.append("")
        lines.append("Your latest Heart Health Score assessment has been completed.")
        lines.append("")
        lines.append("Summary")
        lines.append("")
        notification_types = {n["type"] for n in notifications}
        if "assessment_complete" in notification_types:
            lines.append("• Assessment completed successfully.")

        if "positive" in notification_types:
            lines.append(
                "• Your Heart Health Score has improved since your previous visit."
            )

        if "critical" in notification_types:
            lines.append(
                "• Your assessment detected findings that require medical review."
            )
            lines.append("")
            lines.append("Please consult your healthcare provider.")

        lines.append("")
        lines.append("Regards,")
        lines.append("")
        lines.append("Heart Health Score Team")

        return "\n".join(lines)
    
    def build_emergency_email(self, patient):
        """
        Email sent only to the emergency contact.
        """

        patient_name = patient.get("name", "the patient")

        lines = [
            f"Dear {patient['emergency_contact']['name']},",
            "",
            f"You are listed as the emergency contact for {patient_name}.",
            "",
            "The latest Heart Health Score assessment has generated a critical alert.",
            "",
            "Please contact the patient and encourage them to seek medical attention.",
            "",
            "Regards,",
            "",
            "Heart Health Score Team"
        ]

        return "\n".join(lines)
    
    def send_email(self, recipient, subject, body):
        """
        Sends an email using Gmail SMTP.
        Returns True if successful, otherwise False.
        """
        message=EmailMessage()
        message["Subject"]=subject
        message["From"]=EMAIL_ADDRESS
        message["To"]=recipient
        message.set_content(body)

        try:
            with smtplib.SMTP(SMTP_SERVER,SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.send_message(message)
            return True
        except Exception as e:
            print(f"Email Error: {e}")
            return False

    def send_push_notification(self, notification):
        return True  # Placeholder for actual push notification logic
    
    def send_sms(self, recipient, message):
        pass