from datetime import datetime
import re

from .config import SCHEMA_FIELDS


def valid_date(value):
    if value is None:
        return None

    value = str(value).strip()

    if not re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", value):
        return None

    # Keep the assignment's date format exactly as DD.MM.YYYY.
    # Do not reject dates only because the source document contains
    # unusual dates such as 31.11.2009.
    return value


def normalize_value(value):
    if value is None:
        return None

    value = str(value).strip()

    if value.lower() in {"null", "none", ""}:
        return None

    # Numeric-only agreement value.
    cleaned = re.sub(r"[^0-9.]", "", value)

    if re.fullmatch(r"\d+(?:\.\d+)?", cleaned):
        return str(int(float(cleaned)))

    return None


def normalize_notice(value):
    if value is None:
        return None

    value = str(value).strip()

    if value.lower() in {"null", "none", ""}:
        return None

    if re.fullmatch(r"\d+(?:\.0+)?", value):
        return float(value)

    return None


def validate_metadata(metadata):
    result = dict(metadata)

    result["Agreement Value"] = normalize_value(
        result.get("Agreement Value")
    )

    result["Agreement Start Date"] = valid_date(
        result.get("Agreement Start Date")
    )

    result["Agreement End Date"] = valid_date(
        result.get("Agreement End Date")
    )

    # ONLY this field is converted to float.
    result["Renewal Notice (Days)"] = normalize_notice(
        result.get("Renewal Notice (Days)")
    )

    return result


def normalize_metadata(metadata):
    """
    Normalize model output while preserving the original datatype
    of all fields except Renewal Notice (Days).
    """

    normalized = {}

    for field in SCHEMA_FIELDS:
        value = metadata.get(field)

        if value is None:
            normalized[field] = None
            continue

        if field == "Renewal Notice (Days)":
            try:
                normalized[field] = float(value)
            except (ValueError, TypeError):
                normalized[field] = None
        else:
            normalized[field] = value

    return normalized