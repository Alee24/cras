# COMPLIANCE RISK ANALYTICS SYSTEM (CRAS)
### Regulatory Compliance and Risk Intelligence for SMEs in Kenya

[![Build Status](https://img.shields.io/badge/tests-12%20passed-success)](tests/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-black)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)](docker-compose.yml)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%7C%20SQLite-336791)](app/models/)

CRAS is an enterprise-grade compliance monitoring and decision-support web application specifically engineered for Small and Medium Enterprises (SMEs) in Kenya. It simplifies complex statutory obligations, performs deterministic compliance scoring, surfaces regulatory exposures, coordinates corrective remediation workflows, and generates executive audit reports.

---

## 1. Statutory Regulatory Domains

Initially covers three primary statutory compliance domains with verified Kenya statutory content:

1. **Data Protection & Privacy**
   - **Framework:** Kenya Data Protection Act 2019 & Data Protection (General) Regulations 2021.
   - **Categories:** ODPC Registration, Lawful Basis & Consent, Data Subject Rights, Data Retention & Minimization, Security Safeguards & Encryption, Third-Party Processor Agreements (DPAs), Cross-Border Transfers, Data Protection Impact Assessments (DPIA), and 72-Hour Breach Notification.
2. **Tax Compliance**
   - **Framework:** Tax Procedures Act 2015, Income Tax Act Cap 470, VAT Act 2013, KRA eTIMS Regulations.
   - **Categories:** KRA PIN & Profile Obligations, Tax Compliance Certificate (TCC), Corporate Income Tax Return Filing, Installment Taxes, Monthly PAYE Deductions & Remittances (by 9th), eTIMS Electronic Invoicing Integration, Monthly VAT Filings & Payments (by 20th), Withholding Tax (WHT), and 5-Year Statutory Record Retention.
3. **Employment & Labour Compliance**
   - **Framework:** Employment Act 2007, OSHA 2007, NSSF Act 2013, Social Health Insurance Act 2023, WIBA 2007.
   - **Categories:** Written Employment Contracts, Statutory Personnel Records, Itemized Pay Slips, Minimum Wage Compliance, Monthly NSSF Tier I & II Remittance (by 9th), Monthly SHIF Deductions (by 9th), Paid Annual Leave (21 Days), Maternity & Paternity Leave, Statutory Sick Leave, Workplace Health & Safety (OSHA 2007), WIBA Workplace Injury Insurance, Anti-Sexual Harassment Policy (20+ staff), and Fair Disciplinary Hearing Procedures (Sec 41).

---

## 2. Deterministic Risk Scoring Engine

The scoring engine implements a weighted formula:

$$\text{Overall Compliance Score} = \sum (W_i \times C_i) \times 100$$

Where:
- $W_i$ = Regulatory domain weight: Data Protection (0.35), Tax Compliance (0.35), Employment & Labour (0.30) ($\sum W_i = 1.0$)
- $C_i$ = Domain compliance score, normalized between $0.0$ and $1.0$:
  $$C_i = \frac{\sum (w_{ik} \times s_{ik})}{\sum w_{ik}}$$
- $s_{ik}$ = Response factor: `Compliant` = 1.0, `Partially Compliant` = 0.5, `Non-Compliant` = 0.0.
- `Not Applicable` obligations are excluded from both numerator and denominator.
- `Not Assessed` obligations are flagged as incomplete; the engine refuses to submit and never silently treats unanswered items as compliant.

### RAG Risk Classification Thresholds

| Score Range | Classification | Color Badge | Meaning |
|---|---|---|---|
| **0.00% – 49.99%** | **High Risk** | Red | Critical non-compliance and exposure to statutory penalties and prosecution. |
| **50.00% – 79.99%** | **Moderate Risk** | Amber | Moderate compliance; targeted remediation required on specific obligations. |
| **80.00% – 100.00%** | **Compliant** | Green | Compliant posture with minimal statutory exposure. |

---

## 3. Technology Stack

- **Backend:** Python 3.11+, Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, WTForms, Bcrypt, Pydantic.
- **Database:** PostgreSQL 16 (Production) / SQLite (Development & Testing), normalized in Third Normal Form (3NF) with foreign keys, constraints, and audit logging.
- **Frontend:** Jinja2 templates, Bootstrap 5.3, FontAwesome 6, Chart.js 4 for visual business intelligence.
- **Reporting Engine:** Downloadable PDF reports (via ReportLab), multi-tab Excel (`.xlsx`) workbooks, and CSV exports.
- **Deployment:** Docker & Docker Compose, Gunicorn WSGI server, Nginx reverse proxy with gzip compression and security headers.

---

## 4. Quickstart: Local Development Setup

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/your-org/CRAS.git
cd CRAS
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

### 3. Initialize Database & Seed Statutory Content

```bash
python wsgi.py
```
This automatically initializes the database tables, seeds roles, the scoring policy version, all Kenya statutory requirements, and populates the 4 synthetic SME demonstration scenarios.

Default Super Administrator:
- **Email:** `admin@cras.ke`
- **Password:** `Admin@CRAS2026!`

---

## 5. Running Automated Tests

Run the automated pytest test suite:

```bash
pytest -v
```

All 12 test modules verify:
- Password hashing with Bcrypt
- User lockout after 5 consecutive failed attempts
- Role-based permissions (Super Admin, Org Admin, Compliance Officer, Finance Manager, HR Manager, Auditor)
- SME Registration & Onboarding workflow
- ReportLab PDF generation, CSV generation, and Excel export
- Boundary threshold tests (49.99, 50.00, 79.99, 80.00, 100.00)
- Unassessed obligation submission guards
- 4 Synthetic SME scenarios (Apex Logistics, Kilimani Health, Rift Valley Produce, Savanna Retail)
- Multi-tenant data isolation

---

## 6. Production Deployment with Docker Compose

Deploy the complete stack (PostgreSQL + Flask/Gunicorn + Nginx) with one command sequence:

```bash
docker compose build --no-cache && \
docker compose up -d && \
docker compose ps
```

Health check endpoint:
```bash
curl http://localhost/health
```

For complete VPS instructions, consult [DEPLOYMENT.md](DEPLOYMENT.md).

---

## 7. Synthetic SME Demonstration Profiles

| Organization | Sector | County | Size | Compliance Posture | RAG Classification |
|---|---|---|---|---|---|
| **Apex Logistics Solutions Ltd** | Transport & Logistics | Nairobi | 35 | Comprehensive governance & records | **Compliant** (100.0%) |
| **Kilimani Digital Health Clinic** | Healthcare & Healthtech | Nairobi | 22 | Strong privacy, PAYE/tax arrears | **Moderate Risk** (63.8%) |
| **Rift Valley Fresh Produce Ltd** | Agriculture | Nakuru | 45 | Missing ODPC registration & OSHA/WIBA | **High Risk** (23.5%) |
| **Savanna Retail Distributors Ltd** | Retail & Wholesale | Mombasa | 18 | Exact mathematical threshold baseline | **Moderate Risk** (50.0%) |

---

## 8. Statutory Disclaimer

The Compliance Risk Analytics System (CRAS) provides compliance monitoring, risk scoring, and decision support for SMEs in Kenya. It does not provide formal legal certification or guarantee statutory exemption from enforcement by the Kenya Revenue Authority (KRA), Office of the Data Protection Commissioner (ODPC), or Ministry of Labour.
