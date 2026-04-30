"""
Xpert Fintech eKYC Platform
Security core - RS256 keys, JWT, RBAC, IP whitelist middleware
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from enum import Enum

from jose import JWTError, jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------
class Role(str, Enum):
    ADMIN   = "ADMIN"
    CHECKER = "CHECKER"
    MAKER   = "MAKER"
    AGENT   = "AGENT"
    AUDITOR = "AUDITOR"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"

ROLE_PERMISSIONS = {
    Role.ADMIN:   ["*"],
    Role.MAKER:   ["onboarding:create", "nid:scan", "face:verify", "fingerprint:submit"],
    Role.CHECKER: ["onboarding:review", "onboarding:approve", "onboarding:reject", "audit:read"],
    Role.AGENT:   ["face:verify", "ai:analyze"],
    Role.COMPLIANCE_OFFICER: ["edd:approve", "edd:escalate", "onboarding:review", "audit:read", "compliance:read"],
    Role.AUDITOR: ["audit:read", "report:export"],
}

# ---------------------------------------------------------------------------
# RS256 Key management
# ---------------------------------------------------------------------------
KEYS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "keys")

def _keys_dir() -> str:
    return os.path.abspath(KEYS_DIR)

def generate_rsa_keypair() -> tuple[str, str]:
    """Generate RSA-2048 keypair. Returns (private_pem, public_pem)."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")
    return private_pem, public_pem

def ensure_keypair_exists() -> tuple[str, str]:
    """Load or create RS256 keypair from keys/ directory."""
    keys_dir = _keys_dir()
    os.makedirs(keys_dir, exist_ok=True)
    priv_path = os.path.join(keys_dir, "private.pem")
    pub_path  = os.path.join(keys_dir, "public.pem")
    if not os.path.exists(priv_path) or not os.path.exists(pub_path):
        priv, pub = generate_rsa_keypair()
        with open(priv_path, "w") as f: f.write(priv)
        with open(pub_path,  "w") as f: f.write(pub)
        return priv, pub
    with open(priv_path) as f: priv = f.read()
    with open(pub_path)  as f: pub  = f.read()
    return priv, pub

# Load keys at module import
PRIVATE_KEY, PUBLIC_KEY = ensure_keypair_exists()

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------
ACCESS_TOKEN_TTL_MINUTES  = 15
REFRESH_TOKEN_TTL_DAYS    = 7
ALGORITHM                 = "RS256"

def create_access_token(
    institution_id: str,
    user_id: str,
    role: Role,
    tenant_schema: str,
    ip_whitelist: Optional[List[str]] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub":           institution_id,
        "user_id":       user_id,
        "role":          role.value,
        "tenant_schema": tenant_schema,
        "ip_whitelist":  ip_whitelist or [],
        "jti":           str(uuid.uuid4()),
        "iat":           now,
        "exp":           now + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
        "type":          "access",
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm=ALGORITHM)

def create_refresh_token(
    institution_id: str,
    user_id: str,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub":     institution_id,
        "user_id": user_id,
        "jti":     str(uuid.uuid4()),
        "iat":     now,
        "exp":     now + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
        "type":    "refresh",
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and verify a JWT. Raises JWTError on failure."""
    return jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])

# ---------------------------------------------------------------------------
# IP whitelist check
# ---------------------------------------------------------------------------
def is_ip_allowed(client_ip: str, whitelist: List[str]) -> bool:
    """Return True if whitelist is empty or client_ip is in the list."""
    if not whitelist:
        return True
    return client_ip in whitelist

# ---------------------------------------------------------------------------
# RBAC permission check
# ---------------------------------------------------------------------------
def has_permission(role: Role, permission: str) -> bool:
    """Check if a role has a given permission."""
    perms = ROLE_PERMISSIONS.get(role, [])
    return "*" in perms or permission in perms
