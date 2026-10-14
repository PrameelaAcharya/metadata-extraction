import json
import re
import time
import requests
from .config import OLLAMA_URL, MODEL_NAME, OLLAMA_TIMEOUT, SCHEMA_FIELDS

PROMPT = r'''You are extracting structured metadata from ONE rental agreement.

IMPORTANT:
The document may contain OCR errors.
Do NOT correct the document using outside knowledge.
Use only the text supplied below.

Return exactly ONE JSON object with these six keys:
{schema}

==================================================
FIELD 1: Agreement Value
==================================================

Find the monthly rent / rental amount.

Look especially for phrases such as:
- monthly rent
- rent of
- rent Rs.
- Rs. ... p.m.
- per month

Return ONLY the numeric amount.

Examples:
"Rs. 4,000.00" -> "4000"
"Rs.8,000/-" -> "8000"

Do NOT use:
- security deposit
- advance
- maintenance charge
- electricity charge

If the amount is corrupted or cannot be determined reliably, return null.

==================================================
FIELD 2: Agreement Start Date
==================================================

Find the commencement/effective date of the agreement.

Look especially in:
- "made and executed on"
- "commencement"
- "effective from"
- "valid from"
- "from this date"

Convert the identified date to DD.MM.YYYY.

Do not use a rent payment date as the agreement start date.

==================================================
FIELD 3: Agreement End Date
==================================================

Find the expiry/end date of the rental agreement.

Look for:
- explicit expiry/end dates
- "valid for X months"
- "for X months from this date"
- "agreement made only for X months from this date"
- "tenure of X months"

If the document gives:
1. a reliable agreement start date, and
2. a reliable agreement duration,

you may calculate the end date from those two pieces of evidence.

Do NOT calculate the end date merely from a general assumption.

Return the resulting date in DD.MM.YYYY format.

Do not return an ISO date.

If an explicit end date is present in the document but that date is invalid,
return null. Do not calculate or replace it with another date.

Any calculated end date must also be a valid real calendar date; otherwise
return null.

==================================================
FIELD 4: Renewal Notice (Days)
==================================================

Find ONLY the advance notice period required to terminate,
cancel, or end the agreement.

Look especially for words such as:
- notice
- advance notice
- termination
- terminate
- cancellation

Examples:
"three month advance notice" -> "90"
"2 months notice" -> "60"
"60 days notice" -> "60"
"15 days advance notice" -> "15"
"one week notice" -> "7"

IMPORTANT:
Do NOT use:
- agreement duration
- rental period
- lease period
- 11 months
- payment date
- rent due date
- security deposit
- advance rent

Only extract the number associated with termination/notice.

==================================================
FIELD 5: Party One
==================================================

Identify the FIRST CONTRACTING PARTY.

Use the opening "BY AND BETWEEN" section or equivalent
introduction of the agreement.

The first party is usually introduced as:
- Lessor
- Landlord
- Owner
- First Party

Return ONLY the person's/company's actual name.

Remove:
- Mr.
- Mrs.
- Ms.
- Prof.
- S/o ...
- D/o ...
- W/o ...
- addresses
- property names
- descriptions

Example:
"MR.K.Kuttan S/o Kelu Aehari (Late)"
->
"MR.K.Kuttan"

Do NOT select a witness or a person mentioned later.

==================================================
FIELD 6: Party Two
==================================================

Identify the SECOND CONTRACTING PARTY.

Use the opening "AND" / "BY AND BETWEEN" section.

The second party is usually introduced as:
- Tenant
- Lessee
- Second Party

Return ONLY the actual name.

Remove:
- Mr.
- Mrs.
- Ms.
- Prof.
- S/o ...
- D/o ...
- W/o ...
- addresses
- business names
- property names

Example:
"Sri. P.M. Narayana Namboodri
'Laxmi Leela'"
->
"P.M. Narayana Namboodri"

Do NOT select a witness or another person mentioned later.

==================================================
IMPORTANT PARTY RULE
==================================================

The order is extremely important.

PARTY ONE = first contracting party.

PARTY TWO = second contracting party.

Do NOT swap them.

Do NOT use a person's name from the WHEREAS section
if that person is not one of the two contracting parties.

IMPORTANT DATE VALIDATION RULE:
- A date is valid only if it represents a real calendar date.
- If the document contains an invalid or impossible date, return null.
- Do not correct, modify, normalize, or guess an invalid date.
- Do not replace an invalid date with a nearby valid date.
- Do not infer a different day or month just because the date appears to be an OCR error.
- Validate the day against the actual number of days in the specified month.
- For example, "31.11.2009" is invalid because November has only 30 days, so return null.
- For example, "31.04.2011" is invalid because April has only 30 days, so return null.
- For example, "31.02.2011" is invalid because February does not have 31 days, so return null.
- If a date is invalid, return null even if a mathematically calculated or nearby date would appear more reasonable.
- If the day, month, or year is unclear or corrupted and the real date cannot be determined reliably, return null.
- Only return a date when the date itself is valid and supported by the document.

==================================================
OUTPUT RULES
==================================================

Return valid JSON only.

Every value must be a JSON string or null.

Use exactly these keys:
{schema}

DOCUMENT:
{document}
'''


def build_prompt(document_text: str) -> str:
    return PROMPT.format(schema=json.dumps(SCHEMA_FIELDS), document=document_text)


def call_ollama(prompt: str, retries: int = 3) -> str:
    last_error = None
    for attempt in range(retries):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": "You are a careful document metadata extraction system. Follow the requested JSON schema exactly."},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0},
                },
                timeout=OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()["message"]["content"]
        except requests.RequestException as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(3)
    raise last_error


def clean_party_name(value):
    if value is None:
        return None
    value = str(value).strip()
    if not value or value.lower() == "null":
        return None
    value = re.split(r"\s*,?\s*(?:S/O|S/o|D/O|D/o|W/O|W/o)\b", value, maxsplit=1)[0]
    value = re.sub(r"^\s*(?:Mr\.?|Mrs\.?|Ms\.?|Miss\.?|Prof\.?|Sri\.?)\s+", "", value, flags=re.IGNORECASE)
    return value.strip(" ,.-")


def normalize_metadata(metadata: dict) -> dict:
    result = {}
    for field in SCHEMA_FIELDS:
        value = metadata.get(field)
        result[field] = None if value is None or str(value).strip().lower() == "null" else str(value).strip()
    result["Party One"] = clean_party_name(result["Party One"])
    result["Party Two"] = clean_party_name(result["Party Two"])
    return result


def extract_metadata(document_text: str) -> dict:
    raw = call_ollama(build_prompt(document_text))
    return normalize_metadata(json.loads(raw))
