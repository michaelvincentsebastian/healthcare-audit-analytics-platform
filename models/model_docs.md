# Data Model Documentation

---

## Bronze

> Ingest Bulk API from RestAPI Response

### Characteristic
- Raw or save as it is (Get & Load all data in each format).
- Define all column that available in bulk response at sqlmesh models.
- Need external utils to extract -> parse -> then load data (at `model-dependencies`).

### Purpose
- Keeps source of truth.
- If later there are changes to the transformation/model output that are needed, just update the silver layer.

---

## Silver

> Transform raw & unreadable data into flat & readable format.

### Characteristic

#### Data Model Category Separation

> **Pre-Submission (Before Reporting):** Focuses on Financial Audits & Clinical Compliance. Serves to mitigate hospital losses before data is locked. If the real-time cost of a doctor's procedure exceeds the BPJS package ceiling, the system automatically triggers a Warning status and temporarily suspends data submission to SATUSEHAT/BPJS for medical coding re-evaluation.

> **Post-Submission (After Reporting):** Focuses on Technical Audits & Integration. Serves to monitor data pipeline performance after the input process is complete. The system audits indicators such as the EHR Submission Success Rate to detect submission failures or errors in the SATUSEHAT API. Advantages of the Language Improvements Above: Replaced the word "rembes" with "BPJS claim ceiling" or "INA-CBG Tariff" because BPJS regulations do not recognize the term "reimbursement"

#### Parent Data
- Apply stadardization

#### FHIR Resources
- Unwrap payload_json to clean FHIR json format.
- Flatten FHIR Format (nested) into flat table format (analytics ready data).