"""Labels for age, survival, hosts, heartwood, and GPS confidence.

Exact values are shown only when a field record exists. Everything else
stays an estimate or an explicit unknown.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any, Optional

from app.services.sandalwood_biometrics import calculate_allometric_sandalwood_biometrics

_INTERNET_PREFIX = "[INTERNET_SANDALWOOD]"

# Provenance of girth_cm / height_m on a tree record.
BIOMETRICS_FIELD_MEASURED = "FIELD_MEASURED"
BIOMETRICS_ALLOMETRIC_ESTIMATE = "ALLOMETRIC_ESTIMATE"


def age_label(
    planting_year: Optional[int],
    estimated_age_years: Optional[float],
    biometrics_source: Optional[str] = None,
) -> str:
    if planting_year is not None:
        age = date.today().year - int(planting_year)
        return f"{max(0, age)} yrs (planting record)"
    if estimated_age_years is not None:
        years = int(round(float(estimated_age_years)))
        if biometrics_source == BIOMETRICS_ALLOMETRIC_ESTIMATE:
            return f"~{years} yrs (allometric estimate, no planting record)"
        return f"~{years} yrs (estimated)"
    return "Age unknown"


def resolved_age_years(
    planting_year: Optional[int],
    estimated_age_years: Optional[float],
) -> Optional[float]:
    if planting_year is not None:
        return float(max(0, date.today().year - int(planting_year)))
    if estimated_age_years is None:
        return None
    return float(estimated_age_years)


def survival_is_confirmed(
    survival_confirmed: Optional[bool],
    notes: Optional[str],
) -> bool:
    if survival_confirmed is True:
        return True
    if survival_confirmed is False:
        return False
    return not str(notes or "").lstrip().startswith(_INTERNET_PREFIX)


def survival_label(
    status: Any,
    survival_confirmed: Optional[bool],
    last_observed_on: Optional[str],
    notes: Optional[str],
) -> str:
    raw = status.value if hasattr(status, "value") else str(status or "UNKNOWN")
    pretty = raw.replace("_", " ")
    if survival_is_confirmed(survival_confirmed, notes):
        return f"Confirmed {pretty}"
    if last_observed_on and str(last_observed_on).strip():
        return f"Last observed alive on {str(last_observed_on).strip()}"
    return "Not confirmed alive today"


def gps_label(gps_accuracy: Optional[float]) -> str:
    if gps_accuracy is None:
        return "GPS uncertainty unknown"
    return f"±{round(float(gps_accuracy))} m"


def hosts_label(host_notes: Optional[str]) -> str:
    text = (host_notes or "").strip()
    if text:
        return text
    # Host species cannot be inferred from occurrence records or simulated
    # aerial presets, so this stays open until someone visits the tree.
    return "Hosts not surveyed — needs a field visit to record neighbouring species"


def heartwood_label(
    girth_cm: Optional[float],
    height_m: Optional[float],
    biometrics_source: Optional[str] = None,
) -> str:
    if not girth_cm or not height_m or float(girth_cm) <= 0 or float(height_m) <= 0:
        return "Heartwood unknown (needs measured girth and height)"
    dbh_cm = float(girth_cm) / math.pi
    bio = calculate_allometric_sandalwood_biometrics(dbh_cm, float(height_m))
    if biometrics_source == BIOMETRICS_ALLOMETRIC_ESTIMATE:
        return (
            f"~{bio['heartwood_kg']} kg (modelled from estimated stem, "
            "not a measured core)"
        )
    return f"~{bio['heartwood_kg']} kg (estimated, not a measured core)"
