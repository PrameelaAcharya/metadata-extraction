# Rental Agreement Metadata Extraction

## 1. Project Overview

This project extracts structured metadata from rental agreement documents using OCR text, an LLM, and rule-based validation.

The system extracts the following six fields:

- Agreement Value
- Agreement Start Date
- Agreement End Date
- Renewal Notice (Days)
- Party One
- Party Two

The extracted results are compared with the provided ground-truth data to measure exact-match recall.

---

## 2. Processing Pipeline

The project follows this pipeline:

```text
Rental Agreement Documents
          ↓
OCR / Text Extraction
          ↓
Clean and Prepare Text
          ↓
LLM Metadata Extraction
          ↓
Rule-Based Normalization
          ↓
Validation
          ↓
Final Metadata
          ↓
Evaluation
```

### Step 1: OCR / Text Extraction

The rental agreement documents are converted into text using OCR.

The OCR text may contain errors such as:

- incorrect characters
- missing spaces
- incorrect numbers
- incorrect names
- formatting issues

The system works with the extracted document text and does not use outside information to correct the document.

### Step 2: Clean and Prepare Text

The extracted text is cleaned and prepared before sending it to the LLM.

This makes the document text easier for the extraction model to process.

### Step 3: LLM Metadata Extraction

The LLM receives the prepared rental agreement text and extracts the six required fields.

The extraction prompt provides specific rules for each field.

The LLM returns one JSON object containing the requested metadata.

### Step 4: Rule-Based Normalization

The extracted values are normalized after LLM extraction.

Examples include:

- converting rent values to numeric values
- converting notice periods to days
- standardizing dates to `DD.MM.YYYY`
- removing unwanted party-name prefixes or descriptions

### Step 5: Validation

The extracted metadata is validated using predefined rules.

For example:

- dates must represent valid calendar dates
- missing or unreliable values are returned as `null`
- the agreement end date should not be calculated without reliable supporting information
- Party One and Party Two must remain in the correct order

### Step 6: Evaluation

The predictions are compared against the provided ground-truth labels.

The evaluation uses exact-match recall:

```text
Exact-match recall =
Correct predictions / Eligible ground-truth values × 100
```

The evaluation is performed separately for each metadata field.

---

## 3. Project Structure

```text
metadata-extraction/
│
├── data/
│   ├── train/
│   └── test/
│
├── outputs/
│   ├── train_predictions.csv
│   ├── evaluation_summary.csv
│   └── evaluation_failures.csv
│
├── metadata_extraction.ipynb
├── requirements.txt
├── README.md
└── assignment-details.pdf
```

---

## 4. Main Notebook

The main implementation is provided in:

```text
metadata_extraction.ipynb
```

The notebook contains the complete workflow for:

1. loading the documents
2. preparing the document text
3. extracting metadata
4. validating the extracted values
5. generating predictions
6. evaluating predictions
7. generating failure cases

---

## 5. Required Environment

The project uses Python and the following main libraries:

- Python
- Pandas
- Requests
- tqdm

The LLM is accessed through a locally running Ollama server.

---

## 6. Setup

Create and activate the project environment.

```bash
conda create -n metadata-extraction python=3.12
conda activate metadata-extraction
```

Install the required packages:

```bash
pip install -r requirements.txt
```

Make sure Ollama is running locally and the required model is available.

---

## 7. Running the Project

Open the project in VS Code and open:

```text
metadata_extraction.ipynb
```

Select the Python kernel from the `metadata-extraction` environment.

Then run the notebook cells from top to bottom.

The notebook will:

```text
Load documents
    ↓
Prepare OCR text
    ↓
Extract metadata using LLM
    ↓
Normalize and validate results
    ↓
Save predictions
    ↓
Evaluate against ground truth
    ↓
Generate failure report
```

---

## 8. Output Files

### `train_predictions.csv`

Contains the metadata extracted from the training documents.

The file contains:

- File Name
- Split
- Agreement Value
- Agreement Start Date
- Agreement End Date
- Renewal Notice (Days)
- Party One
- Party Two
- Extraction Status

### `evaluation_summary.csv`

Contains the evaluation results for each metadata field.

Example:

```text
Field                         Correct    Eligible    Exact-match recall
Agreement Value                  ...         ...             ...
Agreement Start Date             ...         ...             ...
Agreement End Date               ...         ...             ...
Renewal Notice (Days)            ...         ...             ...
Party One                        ...         ...             ...
Party Two                        ...         ...             ...
```

### `evaluation_failures.csv`

Contains the documents where the predicted value does not exactly match the ground-truth value.

It is used to analyse extraction errors.

---

## 9. Important Extraction Rules

### Agreement Value

The system extracts the monthly rental amount.

It does not use:

- security deposit
- advance
- maintenance charges
- electricity charges

### Agreement Start Date

The system identifies the agreement commencement or effective date.

Payment dates are not treated as the agreement start date.

### Agreement End Date

The system uses an explicit end date when available.

If the document provides a reliable start date and agreement duration, the end date may be calculated from them.

Invalid calendar dates are not corrected.

### Renewal Notice

Only the notice period associated with termination, cancellation, or ending the agreement is extracted.

Agreement duration or rental period is not treated as the notice period.

### Party One and Party Two

The parties are extracted according to their order in the agreement.

```text
First contracting party → Party One
Second contracting party → Party Two
```

Witnesses and unrelated people mentioned later in the document are not selected as contracting parties.

---

## 10. Evaluation

The main evaluation metric is **exact-match recall**.

A prediction is counted as correct only when the normalized prediction matches the corresponding ground-truth value.

The evaluation is performed independently for all six fields.

This makes it possible to identify which metadata fields require further improvement.

---

## 11. Limitations

The extraction quality depends on:

- OCR quality
- document formatting
- LLM extraction accuracy
- OCR errors in names, dates, and numbers
- ambiguous wording in rental agreements

The system therefore combines LLM extraction with rule-based normalization and validation instead of relying only on the LLM output.

```

```
