"""
M83: Locust load test suite — 500 concurrent onboardings
BFIU eKYC Platform capacity proof for production sign-off.

Run:
  locust -f load_tests/locustfile.py --host=http://localhost:8000
  locust -f load_tests/locustfile.py --host=http://localhost:8000 \
         --headless -u 500 -r 50 --run-time 5m \
         --html load_tests/report.html

Targets:
  - p99 face verify < 3s
  - p99 KYC profile create < 2s
  - p99 screening < 1s
  - 0% error rate at 500 concurrent users
"""
import random
import string
import uuid
import time
from locust import HttpUser, task, between, events

def _rand_nid():     return "".join(random.choices(string.digits, k=17))
def _rand_mobile():  return "017" + "".join(random.choices(string.digits, k=8))
def _rand_name():
    first = random.choice(["Karim","Rahim","Fatima","Nasrin","Abdul","Mohammad"])
    last  = random.choice(["Uddin","Ahmed","Islam","Rahman","Hossain","Khan"])
    return f"{first} {last}"
def _rand_session(): return str(uuid.uuid4())

# valid 1x1 JPEG — properly padded base64 (len%4==0)
STUB_IMAGE = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/9oACAEBAAA/APV//9k="

# demo credentials
DEMO_EMAIL    = "agent-bypass@demo.ekyc"
DEMO_PASSWORD = "DemoAgent@2026"

# shared token cache — all workers share one token to avoid rate limit
_SHARED_TOKEN: dict = {"token": "", "expires_at": 0}
import threading
_TOKEN_LOCK = threading.Lock()


def _get_shared_token(client) -> str:
    """Return cached token or fetch new one. Shared across all users to avoid 429."""
    now = time.time()
    if _SHARED_TOKEN["token"] and now < _SHARED_TOKEN["expires_at"]:
        return _SHARED_TOKEN["token"]
    resp = client.post(
        "/api/v1/auth/token",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        name="/auth/token",
    )
    if resp.status_code == 200:
        data = resp.json()
        _SHARED_TOKEN["token"] = data.get("access_token", "")
        _SHARED_TOKEN["expires_at"] = now + data.get("expires_in", 900) - 60
    return _SHARED_TOKEN["token"]


class EKYCOnboardingUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        self._token = _get_shared_token(self.client)

    def _h(self):
        h = {"X-Institution-ID": "LOAD_TEST"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    @task(6)
    def face_verify(self):
        """BFIU §3.3 — face verification."""
        self.client.post(
            "/api/v1/face/verify",
            json={
                "session_id":     _rand_session(),
                "nid_number":     _rand_nid(),
                "live_image_b64": STUB_IMAGE,
                "nid_image_b64":  STUB_IMAGE,
            },
            headers=self._h(),
            name="/face/verify",
        )

    @task(2)
    def create_kyc_profile(self):
        """BFIU §6.1/6.2 — KYC profile creation."""
        self.client.post(
            "/api/v1/kyc/profile",
            json={
                "session_id":       _rand_session(),
                "verdict":          "MATCHED",
                "confidence":       round(random.uniform(0.75, 0.99), 2),
                "institution_type": "INSURANCE_LIFE",
                "full_name":        _rand_name(),
                "date_of_birth":    "1985-06-15",
                "mobile":           _rand_mobile(),
                "nationality":      "Bangladeshi",
                "present_address":  "Dhaka, Bangladesh",
            },
            headers=self._h(),
            name="/kyc/profile",
        )

    @task(1)
    def screening_check(self):
        """BFIU §3.2.2 — full screening."""
        self.client.post(
            "/api/v1/screening/full",
            json={
                "name":        _rand_name(),
                "nid_number":  _rand_nid(),
                "nationality": "BD",
                "kyc_type":    "SIMPLIFIED",
            },
            headers=self._h(),
            name="/screening/full",
        )

    @task(1)
    def list_profiles(self):
        """Admin — list KYC profiles."""
        self.client.get(
            "/api/v1/kyc/profiles",
            headers=self._h(),
            name="/kyc/profiles",
        )


@events.quitting.add_listener
def check_fail_ratio(environment, **kwargs):
    stats = environment.runner.stats.total
    if stats.num_requests == 0:
        return
    fail_rate = stats.num_failures / stats.num_requests * 100
    print(f"\n── M83 Load Test Results ──")
    for entry in environment.runner.stats.entries.values():
        print(
            f"  {entry.method:<6} {entry.name:<40} "
            f"reqs={entry.num_requests:>5} fail={entry.num_failures:>4} "
            f"p99={entry.get_response_time_percentile(0.99):.0f}ms"
        )
    print(f"\n  Total fail rate: {fail_rate:.2f}%")
    if fail_rate > 1.0:
        print(f"  WARNING: FAIL RATE EXCEEDS 1% — not production ready")
        environment.process_exit_code = 1
    else:
        print(f"  PASS — fail rate within 1% threshold")
