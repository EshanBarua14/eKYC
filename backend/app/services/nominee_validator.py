"""
M68: Nominee validation
BFIU Circular No. 29 §6.1/§6.2

Nominee details are mandatory for all eKYC accounts.
Validation rules:
- nominee_name: required, min 2 chars, no digits
- nominee_relation: required, must be from allowed list
- nominee_dob: optional but if provided must be valid date and nominee must be adult
  (for guardian nominees, minor_guardian flag can override)
"""
from __future__ import annotations
import re
from datetime import datetime, date

# BFIU §6.1: allowed nominee relations
ALLOWED_RELATIONS = {
    "SPOUSE", "FATHER", "MOTHER", "SON", "DAUGHTER",
    "BROTHER", "SISTER", "GRANDFATHER", "GRANDMOTHER",
    "GRANDSON", "GRANDDAUGHTER", "UNCLE", "AUNT",
    "NEPHEW", "NIECE", "FATHER_IN_LAW", "MOTHER_IN_LAW",
    "SON_IN_LAW", "DAUGHTER_IN_LAW", "GUARDIAN", "OTHER",
}

_NAME_RE = re.compile(r"^[A-Za-z\u0980-\u09FF\s\.\-\']+$")


class NomineeValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def validate_nominee(
    nominee_name: str | None,
    nominee_relation: str | None,
    nominee_dob: str | None = None,
    kyc_type: str = "SIMPLIFIED",
    is_minor_guardian: bool = False,
) -> dict:
    """
    Validate nominee details.
    Returns dict with validated fields or raises NomineeValidationError.
    BFIU §6.1: nominee mandatory for all accounts.
    """
    errors = []

    # ── nominee_name ──────────────────────────────────────────────────────
    if not nominee_name or not nominee_name.strip():
        errors.append(NomineeValidationError(
            "nominee_name", "Nominee name is required (BFIU §6.1)"
        ))
    elif len(nominee_name.strip()) < 2:
        errors.append(NomineeValidationError(
            "nominee_name", "Nominee name must be at least 2 characters"
        ))
    elif not _NAME_RE.match(nominee_name.strip()):
        errors.append(NomineeValidationError(
            "nominee_name", "Nominee name must contain only letters, spaces, hyphens"
        ))

    # ── nominee_relation ──────────────────────────────────────────────────
    if not nominee_relation or not nominee_relation.strip():
        errors.append(NomineeValidationError(
            "nominee_relation", "Nominee relation is required (BFIU §6.1)"
        ))
    elif nominee_relation.upper() not in ALLOWED_RELATIONS:
        errors.append(NomineeValidationError(
            "nominee_relation",
            f"Invalid relation '{nominee_relation}'. Allowed: {sorted(ALLOWED_RELATIONS)}"
        ))

    # ── nominee_dob (optional) ────────────────────────────────────────────
    parsed_dob = None
    if nominee_dob:
        try:
            parsed_dob = datetime.strptime(nominee_dob, "%Y-%m-%d").date()
            if parsed_dob > date.today():
                errors.append(NomineeValidationError(
                    "nominee_dob", "Nominee date of birth cannot be in the future"
                ))
            # Check nominee is adult (>=18) unless guardian flag set
            age = (date.today() - parsed_dob).days // 365
            if age < 18 and not is_minor_guardian:
                errors.append(NomineeValidationError(
                    "nominee_dob",
                    "Nominee must be 18 or older. Set is_minor_guardian=True for guardian nominees."
                ))
        except ValueError:
            errors.append(NomineeValidationError(
                "nominee_dob", "Invalid date format. Use YYYY-MM-DD"
            ))

    if errors:
        # Return all errors at once
        raise NomineeValidationError(
            "nominee",
            "; ".join(f"{e.field}: {e.message}" for e in errors)
        )

    return {
        "nominee_name": nominee_name.strip().upper(),
        "nominee_relation": nominee_relation.strip().upper(),
        "nominee_dob": nominee_dob,
        "nominee_age": (date.today() - parsed_dob).days // 365 if parsed_dob else None,
        "validated": True,
        "bfiu_ref": "BFIU Circular No. 29 §6.1",
    }


def validate_nominee_from_data(data: dict, kyc_type: str = "SIMPLIFIED") -> dict | None:
    """
    Validate nominee from session data dict.
    Returns validation result or None if nominee not provided (and not required).
    Raises NomineeValidationError if nominee partially filled or invalid.
    """
    name = data.get("nominee_name", "").strip()
    relation = data.get("nominee_relation", "").strip()
    dob = data.get("nominee_dob", "")

    # If nothing provided — warn but don't block (nominee is strongly recommended)
    if not name and not relation:
        return {
            "validated": False,
            "warning": "Nominee details not provided. Recommended by BFIU §6.1.",
            "bfiu_ref": "BFIU Circular No. 29 §6.1",
        }

    return validate_nominee(
        nominee_name=name or None,
        nominee_relation=relation or None,
        nominee_dob=dob or None,
        kyc_type=kyc_type,
    )
