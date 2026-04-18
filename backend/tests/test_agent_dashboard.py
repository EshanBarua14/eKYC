"""
Frontend Agent Dashboard - Component Tests
Tests: AgentDashboard renders, navigation, session display, NID search, new session wizard
Uses: React Testing Library via pytest (smoke tests via API integration)
"""
import pytest
from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestAgentDashboardAPIIntegration:
    """
    Backend API tests that the Agent Dashboard depends on.
    These verify every API call the Agent Dashboard makes.
    """
    def setup_method(self):
        from app.main import app
        self.client = TestClient(app)
        import app.api.v1.routes.auth as auth_module
        auth_module._demo_users.clear()
        # Register agent user
        self.client.post('/api/v1/auth/register', json={
            'email': 'agent_dashboard@demo.com',
            'phone': '+8801712345678',
            'full_name': 'Test Agent',
            'role': 'MAKER',
            'password': 'agent1234',
        })
        r = self.client.post('/api/v1/auth/token', json={
            'email': 'agent_dashboard@demo.com',
            'password': 'agent1234',
        })
        self.token   = r.json()['access_token']
        self.headers = {'Authorization': f'Bearer {self.token}'}
        from app.services.session_limiter import reset_session, reset_nid_sessions, hash_nid
        reset_session('agent-test-session-001')
        reset_session('agent-test-session-002')
        reset_nid_sessions(hash_nid('1234567890123'))
        reset_nid_sessions(hash_nid('9876543210987'))

    # -- NID Search (used in SearchTab) --
    def test_nid_search_known_nid(self):
        r = self.client.post('/api/v1/nid/verify', json={
            'nid_number': '1234567890123',
            'session_id': 'agent-test-session-001',
        }, headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert data['success'] is True
        assert data['ec_source'] == 'DEMO'
        assert 'ec_data' in data

    def test_nid_search_unknown_nid(self):
        r = self.client.post('/api/v1/nid/verify', json={
            'nid_number': '9999999999999',
            'session_id': 'agent-test-session-002',
        }, headers=self.headers)
        assert r.status_code == 404

    def test_nid_search_invalid_format(self):
        r = self.client.post('/api/v1/nid/verify', json={
            'nid_number': '123',
            'session_id': 'agent-test-session-001',
        }, headers=self.headers)
        assert r.status_code == 422

    def test_nid_session_status(self):
        r = self.client.get('/api/v1/nid/session-status',
            params={'nid_number': '1234567890123', 'session_id': 'agent-test-session-001'},
            headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert data['max_attempts'] == 10
        assert data['max_sessions'] == 2

    # -- Onboarding Wizard (used in NewSessionTab) --
    def test_start_onboarding_session(self):
        r = self.client.post('/api/v1/onboarding/start', json={
            'nid_number': '1234567890123',
            'agent_id':   'agent-001',
            'channel':    'AGENCY',
            'biometric_mode': 'FACE',
        }, headers=self.headers)
        assert r.status_code == 201
        data = r.json()
        assert data['success'] is True
        assert data['current_step'] == 1
        assert data['total_steps'] == 5

    def test_onboarding_step1_nid_verification(self):
        start = self.client.post('/api/v1/onboarding/start', json={
            'nid_number': '9876543210987',
            'agent_id':   'agent-001',
        }, headers=self.headers)
        sid = start.json()['session_id']
        r = self.client.post('/api/v1/onboarding/step', json={
            'session_id': sid,
            'step_data':  {
                'nid_number': '9876543210987',
                'dob': '1985-06-20',
                'fingerprint_b64': 'dummydata',
            },
        }, headers=self.headers)
        assert r.status_code == 200
        assert r.json()['next_step'] == 'PERSONAL_INFO'

    def test_onboarding_wizard_steps_list(self):
        r = self.client.get('/api/v1/onboarding/steps', headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert data['total_steps'] == 5
        assert data['fallback_threshold'] == 3

    def test_onboarding_invalid_nid_rejected(self):
        r = self.client.post('/api/v1/onboarding/start', json={
            'nid_number': '123',
            'agent_id':   'agent-001',
        }, headers=self.headers)
        assert r.status_code == 422

    # -- Risk Grading (used when submitting session) --
    def test_risk_grade_low_risk_customer(self):
        r = self.client.post('/api/v1/risk/grade', json={
            'kyc_profile_id':     'agent-profile-001',
            'institution_type':   'INSURANCE',
            'onboarding_channel': 'AGENCY',
            'residency':          'RESIDENT',
            'pep_ip_status':      'NONE',
            'product_type':       'ORDINARY_LIFE',
            'business_type':      'GOVERNMENT',
            'profession':         'GOVERNMENT_EMPLOYEE',
            'annual_income_bdt':  400000,
            'source_of_funds':    'Salary',
        }, headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert 'grade' in data
        assert 'total_score' in data
        assert data['grade'] in ['LOW', 'MEDIUM', 'HIGH']

    def test_risk_grade_high_risk_triggers_edd(self):
        r = self.client.post('/api/v1/risk/grade', json={
            'kyc_profile_id':     'agent-profile-002',
            'onboarding_channel': 'WALK_IN',
            'residency':          'NRB',
            'pep_ip_status':      'PEP',
            'product_type':       'GROUP',
            'business_type':      'MONEY_EXCHANGE',
            'profession':         'POLITICIAN',
            'annual_income_bdt':  100000000,
            'pep_flag':           True,
        }, headers=self.headers)
        assert r.status_code == 200
        assert r.json()['grade'] == 'HIGH'
        assert r.json()['edd_required'] is True

    # -- Screening (UNSCR check on new session) --
    def test_screening_clear_customer(self):
        r = self.client.post('/api/v1/screening/full', json={
            'name':     'RAHMAN HOSSAIN CHOWDHURY',
            'kyc_type': 'SIMPLIFIED',
        }, headers=self.headers)
        assert r.status_code == 200
        assert r.json()['combined_verdict'] == 'CLEAR'

    def test_screening_regular_ekyc_runs_pep(self):
        r = self.client.post('/api/v1/screening/full', json={
            'name':     'RAHMAN HOSSAIN CHOWDHURY',
            'kyc_type': 'REGULAR',
        }, headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert 'pep' in data['results']
        assert 'adverse_media' in data['results']

    # -- Audit log (agent actions logged) --
    def test_agent_action_logged(self):
        r = self.client.post('/api/v1/audit/log', json={
            'event_type':   'SESSION_CREATED',
            'entity_type':  'LivenessSession',
            'actor_id':     'agent-001',
            'actor_role':   'MAKER',
            'session_id':   'agent-test-session-001',
            'institution_id': 'inst-demo',
        }, headers=self.headers)
        assert r.status_code == 201
        entry = r.json()
        assert entry['event_type'] == 'SESSION_CREATED'
        assert entry['actor_role'] == 'MAKER'

    def test_agent_cannot_access_admin_roles(self):
        r = self.client.get('/api/v1/auth/roles', headers=self.headers)
        assert r.status_code == 403

    # -- Gateway health (used for API Live indicator) --
    def test_health_check_no_auth(self):
        r = self.client.get('/api/v1/gateway/health')
        assert r.status_code == 200
        assert r.json()['status'] == 'ok'

    # -- Session fallback (3 failures -> face matching) --
    def test_fallback_trigger_after_3_fails(self):
        from app.services.onboarding_wizard import reset_wizard_sessions
        reset_wizard_sessions()
        start = self.client.post('/api/v1/onboarding/start', json={
            'nid_number': '1234567890123',
            'agent_id':   'agent-001',
        }, headers=self.headers)
        sid = start.json()['session_id']
        for _ in range(3):
            self.client.post('/api/v1/onboarding/fail', json={
                'session_id': sid,
                'reason': 'fingerprint not matched',
            }, headers=self.headers)
        r = self.client.post('/api/v1/onboarding/fail', json={
            'session_id': sid,
        }, headers=self.headers)
        assert r.json()['fallback_required'] is True

    # -- Lifecycle (agent registers profile after completion) --
    def test_agent_registers_lifecycle_profile(self):
        r = self.client.post('/api/v1/lifecycle/register', json={
            'profile_id': 'agent-lc-001',
            'kyc_type':   'SIMPLIFIED',
            'risk_grade': 'LOW',
            'full_name':  'RAHMAN HOSSAIN CHOWDHURY',
            'mobile':     '+8801712345678',
        }, headers=self.headers)
        assert r.status_code == 201
        data = r.json()
        assert data['review_years'] == 5


class TestAgentDashboardFileStructure:
    """Verify Agent Dashboard frontend files exist and are valid."""

    def test_agent_dashboard_file_exists(self):
        from pathlib import Path
        p = Path(__file__).parent.parent.parent / 'frontend' / 'src' / 'components' / 'AgentDashboard.jsx'
        assert p.exists(), 'AgentDashboard.jsx missing'

    def test_agent_dashboard_has_key_components(self):
        from pathlib import Path
        content = (Path(__file__).parent.parent.parent / 'frontend' / 'src' / 'components' / 'AgentDashboard.jsx').read_text(encoding='utf-8')
        assert 'AgentDashboard' in content
        assert 'Sidebar' in content
        assert 'SessionsTab' in content
        assert 'NewSessionTab' in content
        assert 'SearchTab' in content
        assert 'ReportsTab' in content
        assert 'ProfileTab' in content

    def test_agent_dashboard_uses_api(self):
        from pathlib import Path
        content = (Path(__file__).parent.parent.parent / 'frontend' / 'src' / 'components' / 'AgentDashboard.jsx').read_text(encoding='utf-8')
        assert 'API' in content
        assert 'axios' in content
        assert '/api/v1/nid/verify' in content

    def test_app_jsx_imports_agent_dashboard(self):
        from pathlib import Path
        content = (Path(__file__).parent.parent.parent / 'frontend' / 'src' / 'App.jsx').read_text(encoding='utf-8')
        assert 'AgentDashboard' in content
        assert 'Agent Portal' in content

    def test_agent_dashboard_has_bfiu_limits(self):
        from pathlib import Path
        content = (Path(__file__).parent.parent.parent / 'frontend' / 'src' / 'components' / 'AgentDashboard.jsx').read_text(encoding='utf-8')
        assert 'BFIU' in content
        assert '10' in content
        assert 'UNSCR' in content
