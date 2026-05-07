import requests
import json
import uuid
import datetime

class FirebaseAPI:
    API_KEY = "AIzaSyAps_XRnofsuusFDXD6cxDWTnk0bJ0kUaE"
    PROJECT_ID = "generatormail-e478c"
    FIRESTORE_BASE = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"
    RTDB_BASE = f"https://{PROJECT_ID}-default-rtdb.firebaseio.com"

    @staticmethod
    def create_license(days=30):
        key_str = str(uuid.uuid4()).upper()
        url = f"{FirebaseAPI.FIRESTORE_BASE}/keys?documentId={key_str}&key={FirebaseAPI.API_KEY}"
        doc_data = {
            "fields": {
                "duration_days": {"integerValue": days},
                "is_active": {"booleanValue": True},
                "hwid": {"nullValue": None},
                "created_at": {"timestampValue": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
            }
        }
        resp = requests.post(url, json=doc_data)
        return resp.status_code == 200, key_str if resp.status_code == 200 else resp.text

    @staticmethod
    def reset_hwid(key):
        url = f"{FirebaseAPI.FIRESTORE_BASE}/keys/{key}?key={FirebaseAPI.API_KEY}&updateMask.fieldPaths=hwid"
        data = {"fields": {"hwid": {"nullValue": None}}}
        resp = requests.patch(url, json=data)
        return resp.status_code == 200

    @staticmethod
    def extend_license(key, days=30):
        # Simplified: just update duration_days if not activated, or expires_at if activated
        # For simplicity, we'll try to get the current expires_at first
        get_url = f"{FirebaseAPI.FIRESTORE_BASE}/keys/{key}?key={FirebaseAPI.API_KEY}"
        resp = requests.get(get_url)
        if resp.status_code != 200: return False, "Key not found"
        
        fields = resp.json().get("fields", {})
        expires_at = fields.get("expires_at", {}).get("stringValue")
        
        if expires_at:
            try:
                dt = datetime.datetime.fromisoformat(expires_at.replace('Z', ''))
                new_dt = dt + datetime.timedelta(days=days)
                new_expire = new_dt.isoformat() + "Z"
                url = f"{FirebaseAPI.FIRESTORE_BASE}/keys/{key}?key={FirebaseAPI.API_KEY}&updateMask.fieldPaths=expires_at"
                data = {"fields": {"expires_at": {"stringValue": new_expire}}}
                requests.patch(url, json=data)
                return True, new_expire
            except:
                return False, "Invalid date format"
        else:
            old_dur = int(fields.get("duration_days", {}).get("integerValue", 0))
            new_dur = old_dur + days
            url = f"{FirebaseAPI.FIRESTORE_BASE}/keys/{key}?key={FirebaseAPI.API_KEY}&updateMask.fieldPaths=duration_days"
            data = {"fields": {"duration_days": {"integerValue": new_dur}}}
            requests.patch(url, json=data)
            return True, f"{new_dur} days"

    @staticmethod
    def get_sms(callback):
        # Long-polling for RTDB
        # In a real app, this should be in a separate thread
        url = f"{FirebaseAPI.RTDB_BASE}/sms.json?auth={FirebaseAPI.API_KEY}"
        try:
            resp = requests.get(url, stream=True, headers={'Accept': 'text/event-stream'})
            for line in resp.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data:'):
                        data = json.loads(decoded_line[5:])
                        if data: callback(data)
        except Exception as e:
            print(f"SMS error: {e}")

    @staticmethod
    def archive_sms(sms_id, data):
        url = f"{FirebaseAPI.RTDB_BASE}/archive/{sms_id}.json?auth={FirebaseAPI.API_KEY}"
        requests.put(url, json=data)
        # Delete from main list
        del_url = f"{FirebaseAPI.RTDB_BASE}/sms/{sms_id}.json?auth={FirebaseAPI.API_KEY}"
        requests.delete(del_url)
