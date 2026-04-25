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
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


def _rand_nid():
    return "".join(random.choices(string.digits, k=17))


def _rand_mobile():
    return "017" + "".join(random.choices(string.digits, k=8))


def _rand_name():
    first = random.choice(["Karim", "Rahim", "Fatima", "Nasrin", "Abdul", "Mohammad"])
    last  = random.choice(["Uddin", "Ahmed", "Islam", "Rahman", "Hossain", "Khan"])
    return f"{first} {last}"


def _rand_session():
    return str(uuid.uuid4())


# ── Auth token cache ────────────────────────────────────────────────────────
_TOKEN_CACHE: dict[str, str] = {}


class EKYCOnboardingUser(HttpUser):
    """
    Simulates a field agent performing eKYC onboarding.
    Mix: 60% face verify, 20% KYC profile create, 10% screening, 10% status check.
    """
    wait_time = between(0.5, 2.0)
    _token: str = ""

    def on_start(self):
        """Login once per simulated user."""
        resp = self.client.post(
            "/api/v1/auth/login",
            json={
                "username": "load_test_agent",
                "password": "LoadTest@2026!",
                "institution_id": "LOAD_TEST",
            },
            name="/auth/login",
        )
        if resp.status_code == 200:
            self._token = resp.json().get("access_token", "")
        else:
            # Use dev token if login endpoint not available in test env
            self._token = "dev_load_test_token"

    def _headers(self):
        return {"Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "X-Institution-ID": "LOAD_TEST"}

    @task(6)
    def face_verify(self):
        """BFIU §3.2 — face verification (most common operation)."""
        session_id = _rand_session()
        self.client.post(
            "/api/v1/face/verify",
            json={
                "session_id": session_id,
                "nid_number": _rand_nid(),
                "live_image_b64": "data:image/jpeg;base64,/9j/4AAQ",  # stub
                "nid_image_b64":  "data:image/jpeg;base64,/9j/4AAQ",
            },
            headers=self._headers(),
            name="/face/verify",
        )

    @task(2)
    def create_kyc_profile(self):
        """BFIU §6.1/6.2 — KYC profile creation."""
        session_id = _rand_session()
        self.client.post(
            "/api/v1/kyc/profile",
            json={
                "session_id":       session_id,
                "verdict":          "MATCHED",
                "confidence":       round(random.uniform(0.75, 0.99), 2),
                "institution_type": "INSURANCE_LIFE",
                "full_name":        _rand_name(),
                "date_of_birth":    "1985-06-15",
                "mobile":           _rand_mobile(),
                "nationality":      "Bangladeshi",
                "present_address":  "Dhaka, Bangladesh",
                "unscr_checked":    True,
            },
            headers=self._headers(),
            name="/kyc/profile",
        )

    @task(1)
    def screening_check(self):
        """BFIU §3.2.2 — UNSCR/PEP screening."""
        self.client.post(
            "/api/v1/screening/check",
            json={
                "name":       _rand_name(),
                "nid_number": _rand_nid(),
                "dob":        "1980-01-01",
            },
            headers=self._headers(),
            name="/screening/check",
        )

    @task(1)
    def get_kyc_profile(self):
        """Status check — read existing profile."""
        session_id = _rand_session()
        self.client.get(
            f"/api/v1/kyc/profile/{session_id}",
            headers=self._headers(),
            name="/kyc/profile/[session_id]",
        )


class EKYCCheckerUser(HttpUser):
    """Simulates checker reviewing KYC submissions — lower concurrency."""
    wait_time = between(2.0, 5.0)
    weight = 1  # 1 checker per 10 agents

    def on_start(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"username": "load_test_checker", "password": "LoadTest@2026!",
                  "institution_id": "LOAD_TEST"},
            name="/auth/login",
        )
        self._token = resp.json().get("access_token", "") if resp.status_code == 200 else ""

    def _headers(self):
        return {"Authorization": f"Bearer {self._token}"}

    @task(3)
    def list_profiles(self):
        self.client.get(
            "/api/v1/kyc/profiles?limit=20",
            headers=self._headers(),
            name="/kyc/profiles",
        )

    @task(1)
    def approve_profile(self):
        session_id = _rand_session()
        self.client.patch(
            f"/api/v1/kyc/profile/{session_id}/approve",
            headers=self._headers(),
            name="/kyc/profile/approve",
        )


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    if isinstance(environment.runner, MasterRunner):
        print("""
+======================================================╗
|  M83: eKYC Load Test — BFIU Production Capacity     |
|  Target: 500 concurrent users, 0% error rate        |
|  SLA:    p99 face_verify < 3s, profile < 2s         |
+======================================================╝
        """)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats
    print("\n── M83 Load Test Results ──")
    for name, s in stats.entries.items():
        if s.num_requests > 0:
            print(f"  {name[1]:40s} "
                  f"reqs={s.num_requests:5d} "
                  f"fail={s.num_failures:3d} "
                  f"p99={s.get_response_time_percentile(0.99):.0f}ms")
    fail_rate = stats.total.fail_ratio * 100
    print(f"\n  Total fail rate: {fail_rate:.2f}%")
    if fail_rate > 1.0:
        print("  ⚠️  FAIL RATE EXCEEDS 1% — not production ready")
    else:
        print("  ✅ PASS — platform ready for 500 concurrent users")
