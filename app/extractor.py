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

Find the date on which the rental agreement/tenancy ends.

Use the strongest available evidence in the document.

1. EXPLICIT END / EXPIRY DATE
--------------------------------
If the agreement explicitly states an expiry/end date, extract that date
exactly as written in the document.

Look for phrases such as:
- "agreement expires on"
- "expires on"
- "expiry date"
- "ends on"
- "ending on"
- "valid up to"
- "valid till"
- "valid until"
- "terminates on"
- "shall expire on"
- "period ending"
- "up to [date]"
- "for the period from [start date] to [end date]"

If an explicit end date is present, prefer it over a calculated date.

IMPORTANT:
Do NOT validate or correct the calendar validity of an explicit date.

If the document explicitly contains a date such as:
"31.11.2009"
extract it as:
"31.11.2009"

Do NOT change it to null.

Do NOT change:
- the day
- the month
- the year

Do NOT replace an explicit date with a nearby or mathematically
more reasonable date.

2. AGREEMENT DURATION / TENURE
--------------------------------
If no explicit end date is available, look for a clearly stated agreement
duration.

Look especially for:
- "valid for X months"
- "for X months from this date"
- "agreement made only for X months from this date"
- "tenure of X months"
- "period of X months"
- "term of X months"
- "lease period of X months"
- "rental period of X months"
- "shall be in force for X months"
- "shall continue for X months"
- "for a period of X months"
- "from the date of tenancy"
- "from the date of commencement"

If the document provides BOTH:
1. a reliable agreement/tenancy start date, and
2. a clearly stated duration,

you may calculate the end date using the stated duration.

Example:
"Agreement shall be in force for 11 months from 01.04.2011"
-> "01.03.2012"

Do not use a generic assumption such as "rental agreements are normally
11 months."

3. DATE RANGE
--------------------------------
If the document states a date range such as:

"from 01.04.2011 to 31.03.2012"

then use the second date as the Agreement End Date.

4. DISTINGUISH AGREEMENT END DATE FROM OTHER DATES
--------------------------------
Do NOT confuse the agreement end date with:

- rent payment/due dates
- security deposit dates
- registration dates
- execution/signing dates
- notice dates
- renewal dates
- dates mentioned in property descriptions
- dates from previous agreements
- dates from receipts or supporting documents

The end date must describe the end of the rental agreement/tenancy itself.

5. HANDLING OCR ERRORS
--------------------------------
The document may contain OCR errors.

Use surrounding text as evidence when determining whether a date belongs
to the agreement end date.

If the same end date appears clearly elsewhere in the SAME document,
use the clearer occurrence.

Do NOT invent missing digits or modify an explicit date merely because
another date would make the agreement duration look more reasonable.

6. IMPORTANT DATE RULE
--------------------------------
Extract the date based on what is actually written in the document.

For an EXPLICIT end date:
- Preserve the date exactly as stated.
- Do NOT correct invalid calendar dates.
- Do NOT return null merely because the date is not a valid calendar date.
- Do NOT calculate a replacement date.

For a CALCULATED end date:
- Calculate only when both the start date and duration are clearly supported
  by the document.
- Return the calculated date in DD.MM.YYYY format.

7. OUTPUT FORMAT
--------------------------------
Return the Agreement End Date in exactly:

DD.MM.YYYY

Do not return an ISO date.

If an explicit end date is available, return that date exactly as extracted
from the document.

Return null only when the end date cannot be determined from the document.

==================================================
FIELD 4: Renewal Notice (Days)
==================================================

Find ONLY the advance notice period required to terminate,
cancel, or end the rental agreement.

Look for a number directly associated with words such as:
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
- Extract the notice period, NOT the agreement duration.
- Extract the number specifically connected to the notice/termination clause.
- Do NOT use numbers from unrelated clauses.

Do NOT use:
- agreement duration
- rental period
- lease period
- "11 months" when it describes the agreement duration
- payment date
- rent due date
- security deposit
- advance rent
- maintenance period

If the notice period is stated in months, convert:
1 month -> 30 days
2 months -> 60 days
3 months -> 90 days

If the notice period is stated in weeks, convert:
1 week -> 7 days
2 weeks -> 14 days

If the document does not clearly state a termination/cancellation notice
period, return null.

Return ONLY the numeric number of days.

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

Strictly Remove:
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
STRICT EXTRACTION AND EVIDENCE RULES
==================================================

For every field, prefer the value that is directly supported by
the document text over a value that is inferred.

Do not guess.

If multiple candidate values exist, choose the candidate that is
most clearly associated with the requested field.

Do not confuse numbers belonging to different fields.

For example:
- A rent amount must not be confused with a deposit or advance.
- A commencement date must not be confused with an execution/signing date
  unless the document clearly indicates they are the same.
- An agreement duration must not be returned as a renewal notice period.
- A landlord/owner must not be returned as the tenant.
- A tenant/lessee must not be returned as the landlord.

==================================================
AGREEMENT VALUE - ADDITIONAL RULE
==================================================

When multiple monetary amounts appear, inspect the surrounding text
before selecting the agreement value.

The target is the recurring monthly rental amount.

Give higher priority to an amount explicitly associated with:
- monthly rent
- monthly rental
- rent per month
- rent payable per month
- monthly rental value

Do not select an amount merely because it is the largest or most
frequently occurring number.

If the same rent amount appears multiple times, use the amount that
is clearly identified as the monthly rent.

==================================================
DATE - ADDITIONAL RULE
==================================================

Do not swap the start date and end date.

First identify the date associated with the beginning/commencement
of the agreement.

Then independently identify the date associated with expiry/end/
termination of the agreement.

If both dates are explicitly present, return them exactly according
to their respective roles.

If a duration is given, calculate the end date only when the
relationship between the start date and duration is clearly stated.

Do not use the order in which dates appear in the document as the
reason for deciding which is the start date or end date.

==================================================
RENEWAL NOTICE - ADDITIONAL RULE
==================================================

The renewal notice field must contain ONLY the advance notice period
for termination/cancellation/end of the agreement.

The number must be converted to DAYS.

Conversions:
- 1 week = 7 days
- 2 weeks = 14 days
- 1 month = 30 days
- 2 months = 60 days
- 3 months = 90 days
- 4 months = 120 days
- 6 months = 180 days
- 12 months = 360 days

If the document contains both an agreement duration and a notice
period, use ONLY the notice period.

For example:
"Agreement shall remain valid for 11 months and either party may
terminate by giving 3 months notice."

Return:
"Renewal Notice (Days)": "90"

Do NOT return 11 or any other agreement-duration value.

If no termination/cancellation/advance-notice period can be
identified reliably, return null.

==================================================
PARTY ORDER - ADDITIONAL RULE
==================================================

Determine the parties from the contracting-party introduction,
normally the "BY AND BETWEEN" section.

The first named contracting party is Party One.

The second named contracting party is Party Two.

Do not determine party order from:
- signatures appearing later
- witness sections
- payment details
- WHEREAS clauses
- names appearing elsewhere in the document

If the same person's name appears in multiple places, use the name
from the contracting-party introduction.

==================================================
OCR HANDLING
==================================================

OCR text may contain spacing, punctuation, or character errors.

You may normalize obvious OCR formatting issues in a person's name,
such as unnecessary spaces between initials or punctuation errors,
but do not invent missing name components.

For example:
"M. V. V« VI JAY A SHANKAR"

may be interpreted as the OCR representation of:
"M.V.V. VIJAYA SHANKAR"

when the surrounding document evidence clearly supports that reading.

However, do not replace a name with a different person merely because
another name appears elsewhere in the document.

==================================================
FINAL SELF-CHECK
==================================================

Before returning the JSON, verify all six fields:

1. Agreement Value = monthly rent amount.
2. Agreement Start Date = beginning/commencement date.
3. Agreement End Date = expiry/end date.
4. Renewal Notice (Days) = termination/cancellation notice period
   converted to days.
5. Party One = first contracting party.
6. Party Two = second contracting party.

Check that Party One and Party Two have not been swapped.

Check that Agreement Start Date and Agreement End Date have not
been swapped.

Check that Renewal Notice (Days) is not the agreement duration.

Check that invalid dates are returned as null according to the
date rules above.

If evidence is insufficient, return null instead of guessing.

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
