import os
import time
import json
import logging
import hashlib
from datetime import datetime

logger = logging.getLogger("SATURDAY.Health.GoogleFit")

GOOGLE_FIT_SCOPES = [
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/fitness.heart_rate.read",
    "https://www.googleapis.com/auth/fitness.body.read",
    "https://www.googleapis.com/auth/fitness.location.read",
]

DATA_STORE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "google_fit_cache.json")


class GoogleFitClient:
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.credentials = None
        self.service = None
        self.connected = False
        self.last_sync = None
        self._data_cache = {}
        self._load_cache()

    def _load_cache(self):
        try:
            if os.path.exists(DATA_STORE_FILE):
                with open(DATA_STORE_FILE, "r") as f:
                    self._data_cache = json.load(f)
        except Exception:
            self._data_cache = {}

    def _save_cache(self):
        try:
            os.makedirs(os.path.dirname(DATA_STORE_FILE), exist_ok=True)
            with open(DATA_STORE_FILE, "w") as f:
                json.dump(self._data_cache, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save Google Fit cache: %s", e)

    def authenticate(self, credentials_file=None):
        credentials_file = credentials_file or os.getenv("GOOGLE_FIT_CREDENTIALS", "data/google_credentials.json")
        token_file = os.path.join(os.path.dirname(credentials_file), "google_fit_token.json")

        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow

            creds = None
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, GOOGLE_FIT_SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    from google.auth.transport.requests import Request
                    creds.refresh(Request())
                else:
                    if not os.path.exists(credentials_file):
                        logger.warning("Google credentials file not found at %s", credentials_file)
                        return False
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, GOOGLE_FIT_SCOPES)
                    creds = flow.run_local_server(port=0)

                with open(token_file, "w") as token:
                    token.write(creds.to_json())

            self.credentials = creds
            from googleapiclient.discovery import build
            self.service = build("fitness", "v1", credentials=self.credentials)
            self.connected = True
            logger.info("Google Fit authenticated successfully")
            return True

        except ImportError:
            logger.warning("Google API client libraries not installed. Install google-api-python-client google-auth-oauthlib")
            return False
        except Exception as e:
            logger.warning("Google Fit authentication failed: %s", e)
            return False

    def sync(self):
        if not self.connected or not self.service:
            self._sync_offline_data()
            return self._build_response("offline")

        try:
            now = datetime.now()
            start_of_day = datetime(now.year, now.month, now.day)
            start_ms = int(start_of_day.timestamp() * 1000)
            end_ms = int(now.timestamp() * 1000)

            data_sources = {}
            data_sources["steps"] = self._fetch_dataset("com.google.step_count.delta", start_ms, end_ms)
            data_sources["heart_rate"] = self._fetch_dataset("com.google.heart_rate.bpm", start_ms, end_ms)
            data_sources["calories"] = self._fetch_dataset("com.google.calories.expended", start_ms, end_ms)
            data_sources["distance"] = self._fetch_dataset("com.google.distance.delta", start_ms, end_ms)
            data_sources["active_minutes"] = self._fetch_dataset("com.google.active_minutes", start_ms, end_ms)

            self._data_cache = data_sources
            self.last_sync = time.time()
            self._save_cache()

            if self.event_bus:
                self.event_bus.publish("health_data_sync", {
                    "source": "google_fit",
                    "data": data_sources,
                    "timestamp": self.last_sync,
                })

            return self._build_response("online")

        except Exception as e:
            logger.warning("Google Fit sync failed: %s", e)
            return self._build_response("error", str(e))

    def _fetch_dataset(self, data_type, start_ms, end_ms):
        try:
            response = self.service.users().dataset().list(
                userId="me",
                aggregateBy=[{"dataTypeName": data_type}],
                bucketByTime={"durationMillis": 86400000},
                startTimeMillis=start_ms,
                endTimeMillis=end_ms,
            ).execute()

            values = []
            for bucket in response.get("bucket", []):
                for dataset in bucket.get("dataset", []):
                    for point in dataset.get("point", []):
                        for val in point.get("value", []):
                            if "fpVal" in val:
                                values.append(val["fpVal"])
                            elif "intVal" in val:
                                values.append(val["intVal"])

            return {"value": sum(values) if values else 0, "unit": self._get_unit(data_type), "data_points": len(values)}

        except Exception as e:
            logger.debug("Failed to fetch %s: %s", data_type, e)
            return {"value": 0, "unit": self._get_unit(data_type), "data_points": 0}

    def _get_unit(self, data_type):
        units = {
            "com.google.step_count.delta": "steps",
            "com.google.heart_rate.bpm": "bpm",
            "com.google.calories.expended": "kcal",
            "com.google.distance.delta": "meters",
            "com.google.active_minutes": "minutes",
        }
        return units.get(data_type, "unknown")

    def _sync_offline_data(self):
        self._data_cache["offline_mode"] = True
        self._data_cache["last_attempt"] = time.time()

    def _build_response(self, mode, error=None):
        response = {
            "mode": mode,
            "connected": self.connected,
            "last_sync": self.last_sync,
            "timestamp": time.time(),
        }
        if error:
            response["error"] = error
        if self._data_cache:
            response["cached_data"] = self._data_cache
        return response

    def get_steps_today(self):
        steps = self._data_cache.get("steps", {})
        return steps.get("value", 0) if isinstance(steps, dict) else 0

    def get_heart_rate(self):
        hr = self._data_cache.get("heart_rate", {})
        return hr.get("value", 0) if isinstance(hr, dict) else 0

    def get_calories(self):
        cal = self._data_cache.get("calories", {})
        return cal.get("value", 0) if isinstance(cal, dict) else 0

    def get_distance(self):
        dist = self._data_cache.get("distance", {})
        return dist.get("value", 0) if isinstance(dist, dict) else 0

    def get_summary(self):
        return {
            "steps": self.get_steps_today(),
            "heart_rate": self.get_heart_rate(),
            "calories": self.get_calories(),
            "distance_meters": self.get_distance(),
            "active_minutes": self._data_cache.get("active_minutes", {}).get("value", 0) if isinstance(self._data_cache.get("active_minutes"), dict) else 0,
            "connected": self.connected,
            "last_sync": self.last_sync,
        }
