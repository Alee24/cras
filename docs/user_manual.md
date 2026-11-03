# CRAS User Manual & Operations Guide

**System:** Compliance Risk Analytics System (CRAS)  
**Subtitle:** Regulatory Compliance and Risk Intelligence for SMEs in Kenya

---

## 1. Introduction

The Compliance Risk Analytics System (CRAS) is a centralized decision-support platform that empowers Kenyan Small and Medium Enterprises (SMEs) to proactively monitor statutory compliance obligations, evaluate exposure, and execute corrective action workflows across three primary regulatory domains:
1. **Data Protection & Privacy** (Kenya Data Protection Act 2019 & ODPC Regulations 2021)
2. **Tax Compliance** (Tax Procedures Act 2015, Income Tax Act, VAT Act, and eTIMS)
3. **Employment & Labour Laws** (Employment Act 2007, OSHA 2007, NSSF Act 2013, SHIF 2023, WIBA)

> **Important Regulatory Notice:** CRAS provides risk intelligence, self-assessment workflows, and managerial decision support. It does not provide legal certification or guarantee statutory exemption from regulatory enforcement.

---

## 2. Onboarding & Organization Setup

### Step 1: SME Registration
1. Navigate to `/auth/register`.
2. Provide your primary company details:
   - Business Registration / Certificate Number
   - KRA PIN
   - Industry Sector and Entity Type
   - County of Operation and Total Employees
   - Organization Administrator credentials
3. Upon submission, the organization profile is established, standard Kenyan statutory calendar rules are automatically seeded, and you are granted the **Organization Administrator** (`ORG_ADMIN`) role.

### Step 2: Setting up Departments & Team Members
1. Go to **Organization > Departments** to create or customize functional units (e.g. Legal, Finance, Human Resources, Operations).
2. Go to **Organization > Users & Roles** to invite team members and assign role-based permissions:
   - **Compliance Officer:** Conducts assessments, audits gaps, assigns actions, generates reports.
   - **Finance Manager:** Manages tax obligations, eTIMS compliance, KRA returns.
   - **HR Manager:** Manages labour contracts, payroll deductions, NSSF, SHIF, and OSHA.
   - **Auditor / Viewer:** Read-only access to completed audit reports and historical scores.

---

## 3. Conducting a Compliance Assessment

1. Navigate to **Compliance Management > Assessments** and click **New Assessment**.
2. Select your assessment period (e.g. `2026 Q1`, `Annual 2026`) and target date.
3. The assessment loads all active Kenyan statutory obligations grouped by regulatory domain:
   - **Data Protection:** 16 structured obligations.
   - **Tax Compliance:** 13 structured obligations.
   - **Labour Compliance:** 14 structured obligations.
4. For each statutory obligation:
   - Review the legal citation, plain-language description, and evaluation question.
   - Select your status:
     - **Compliant (1.0 factor):** Obligation is fully satisfied with documentation.
     - **Partially Compliant (0.5 factor):** In progress or partially implemented.
     - **Non-Compliant (0.0 factor):** Obligation is unfulfilled.
     - **Not Applicable:** Organization is legally exempt (excluded from denominator).
   - Enter assessor observations or click **Evidence Document** to upload supporting PDF, DOCX, XLSX, or image proofs.
5. Click **Save Draft** at any time to preserve responses without finalizing.
6. Click **Finalize & Calculate Score**.
   - Note: The scoring engine verifies that no obligations remain unassessed. Unanswered obligations cannot be silently treated as compliant.

---

## 4. Understanding the RAG Risk Scoring Engine

CRAS calculates transparent, deterministic compliance scores based on the weighted formula:

$$\text{Overall Compliance Score} = \sum (W_i \times C_i) \times 100$$

Where:
- $W_i$ = Domain weight: Data Protection (35%), Tax (35%), Labour (30%) ($\sum W_i = 1.0$)
- $C_i$ = Domain compliance score, normalized between $0.0$ and $1.0$

### RAG Risk Classification Thresholds

| Compliance Score (%) | RAG Risk Classification | Indicator Badge | Meaning & Impact |
|---|---|---|---|
| **0.00% – 49.99%** | **High Risk** | Red | Severe statutory non-compliance. Immediate threat of KRA penalties, ODPC fines up to Ksh 5M, or labour court awards. |
| **50.00% – 79.99%** | **Moderate Risk** | Amber | Acceptable core operational status, but specific exposures exist that require remediation before audit cycles. |
| **80.00% – 100.00%** | **Compliant** | Green | High standard of governance and adherence to Kenyan laws. Negligible regulatory exposure. |

---

## 5. Compliance Gap & Corrective Action Management

- Finalizing an assessment automatically identifies all non-compliant and partially compliant responses and creates entries in **Compliance Management > Compliance Gaps**.
- Each gap highlights:
  - Exact statutory legal section
  - Potential statutory consequences (fines, prosecution, license revocation)
  - Recommended remediation action
- From each gap, click **Assign Action** to create a **Corrective Action Task**:
  - Assign the task to a specific department user
  - Set a hard due date
  - Set priority (Critical, High, Medium, Low)
  - Update progress from `OPEN` $\to$ `IN_PROGRESS` $\to$ `RESOLVED` with documented remediation notes.

---

## 6. Statutory Compliance Calendar

- Navigate to **Compliance Management > Compliance Calendar** to track statutory recurring deadlines:
  - **9th of every month:** PAYE remittance, NSSF contributions, SHIF healthcare deductions
  - **20th of every month:** Monthly VAT return & payment, Withholding Tax
  - **30th June:** Annual Corporate Income Tax return filing
- Click **Mark Done** when a filing is completed to maintain an audit trail.

---

## 7. Reports & Data Exports

- Navigate to **Reporting > Compliance Reports**:
  - **Download PDF Report:** Generates a branded executive compliance audit document including score summary, domain breakdown, gap matrices, and statutory disclaimers.
  - **Download Excel Workbook:** Multi-tab `.xlsx` report ready for board presentations or CFO review.
  - **Export CSV:** Raw tabular export for integration with business intelligence tools.
  - **Printable HTML:** Browser print-friendly layout.

