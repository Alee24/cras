from datetime import date
from app.models.base import db
from app.models.auth import Role, Permission, User, UserRole
from app.models.organization import Organization, Department, OrganizationUser
from app.models.regulatory import RegulatoryDomain, RegulatoryCategory, RegulatoryRequirement, ComplianceQuestion
from app.models.scoring import ScoringPolicy, ScoringPolicyVersion
from app.models.compliance_management import ComplianceDeadline


def seed_roles_and_permissions():
    """Seeds the 6 standard CRAS roles and default permissions."""
    roles_data = [
        (Role.SUPER_ADMIN, "Super Administrator", "Full platform access across all organizations and system settings."),
        (Role.ORG_ADMIN, "Organization Administrator", "Manages organization profile, users, departments, and compliance settings."),
        (Role.COMPLIANCE_OFFICER, "Compliance Officer", "Conducts assessments, monitors compliance gaps, assigns corrective actions, and generates reports."),
        (Role.FINANCE_MANAGER, "Finance Manager", "Oversees tax compliance obligations, KRA filings, eTIMS, and financial audit readiness."),
        (Role.HR_MANAGER, "HR Manager", "Oversees employment contracts, labour laws, NSSF/SHIF deductions, and occupational safety."),
        (Role.AUDITOR, "Auditor / Viewer", "Read-only access to compliance reports, assessment history, and audit logs."),
    ]

    for name, display_name, desc in roles_data:
        role = Role.query.filter_by(name=name).first()
        if not role:
            role = Role(name=name, display_name=display_name, description=desc)
            db.session.add(role)

    db.session.commit()


def seed_scoring_policy():
    """Seeds the standard SME Kenya scoring policy and version v1.0."""
    policy = ScoringPolicy.query.filter_by(code="SME_KENYA_STANDARD").first()
    if not policy:
        policy = ScoringPolicy(
            code="SME_KENYA_STANDARD",
            name="Kenya SME Standard Compliance Scoring Policy",
            description="Weighted regulatory domain compliance model based on Data Protection (35%), Tax (35%), and Labour (30%).",
            is_active=True,
        )
        db.session.add(policy)
        db.session.flush()

    version = ScoringPolicyVersion.query.filter_by(policy_id=policy.id, version_number="v1.0").first()
    if not version:
        version = ScoringPolicyVersion(
            policy_id=policy.id,
            version_number="v1.0",
            domain_weights_json='{"DATA_PROTECTION": 0.35, "TAX": 0.35, "LABOUR": 0.30}',
            response_scores_json='{"COMPLIANT": 1.0, "PARTIALLY_COMPLIANT": 0.5, "NON_COMPLIANT": 0.0}',
            rag_thresholds_json='{"high_risk_max": 49.99, "moderate_risk_max": 79.99, "compliant_min": 80.0}',
            is_active=True,
        )
        db.session.add(version)

    db.session.commit()
    return policy, version


def seed_regulatory_content():
    """Seeds the regulatory domains, categories, requirements, and compliance questions."""
    
    # -------------------------------------------------------------
    # DOMAIN 1: DATA PROTECTION
    # -------------------------------------------------------------
    dp_domain = RegulatoryDomain.query.filter_by(code="DATA_PROTECTION").first()
    if not dp_domain:
        dp_domain = RegulatoryDomain(
            code="DATA_PROTECTION",
            title="Data Protection & Privacy",
            description="Compliance with Kenya Data Protection Act 2019 and Data Protection (General) Regulations 2021 overseen by the Office of the Data Protection Commissioner (ODPC).",
            legal_framework="Kenya Data Protection Act, 2019 & Regulations 2021",
            icon="fa-shield-halved",
            display_order=1,
            is_active=True,
        )
        db.session.add(dp_domain)
        db.session.flush()

    dp_categories = {
        "DP_REG": ("ODPC Registration & Governance", "Statutory registration as data controller or processor and organizational oversight.", 1),
        "DP_PRINCIPLES": ("Principles & Lawful Processing", "Lawful basis for data collection, purpose limitation, and consent management.", 2),
        "DP_RIGHTS": ("Data Subject Rights & Transparency", "Privacy notices, subject access requests, rectification, and erasure.", 3),
        "DP_SECURITY": ("Data Security, DPIA & Breaches", "Technical security safeguards, third-party agreements, impact assessments, and 72-hour breach notification.", 4),
    }

    dp_cat_objs = {}
    for code, (title, desc, order) in dp_categories.items():
        cat = RegulatoryCategory.query.filter_by(domain_id=dp_domain.id, code=code).first()
        if not cat:
            cat = RegulatoryCategory(domain_id=dp_domain.id, code=code, title=title, description=desc, display_order=order)
            db.session.add(cat)
            db.session.flush()
        dp_cat_objs[code] = cat

    dp_requirements = [
        # DP_REG
        {
            "cat": "DP_REG",
            "code": "DP-001",
            "title": "ODPC Registration as Data Controller / Processor",
            "plain_description": "Registration with the Office of the Data Protection Commissioner (ODPC) if the business processes personal data and meets statutory thresholds (turnover > Ksh 5M or > 10 employees, or processing sensitive personal data).",
            "legal_reference": "Data Protection Act, 2019, Section 18; ODPC (Registration of Data Controllers and Processors) Regulations, 2021",
            "applicability_rule": "SMEs processing personal data meeting ODPC threshold guidelines",
            "required_evidence_desc": "Valid ODPC Certificate of Registration or statutory exemption assessment memo.",
            "risk_weight": 3.0,
            "potential_consequence": "Statutory penalty notice of up to Ksh 5,000,000 or 1% of annual turnover, administrative enforcement orders, or imprisonment of directors for up to 2 years.",
            "recommended_corrective_action": "Submit online registration application through the ODPC official portal (odpc.go.ke) and upload the certificate upon issuance.",
            "question": "Has your organization registered as a Data Controller or Data Processor with the ODPC, or formally documented a legal exemption?",
            "help_text": "Verify registration certificate status and renewal date with the ODPC.",
        },
        {
            "cat": "DP_REG",
            "code": "DP-002",
            "title": "Designation of Data Protection Lead / Officer",
            "plain_description": "Appointment of an internal Data Protection Officer (DPO) or designated compliance lead responsible for overseeing data protection practices.",
            "legal_reference": "Data Protection Act, 2019, Section 24",
            "applicability_rule": "All organizations processing personal data systematically",
            "required_evidence_desc": "Formal letter of appointment or job description identifying the designated DPO/lead and communication of details to the ODPC where required.",
            "risk_weight": 2.0,
            "potential_consequence": "Lack of internal accountability, failure to respond to regulatory inquiries, regulatory citations.",
            "recommended_corrective_action": "Formally designate a qualified employee or external consultant as DPO/Lead and establish clear reporting to executive management.",
            "question": "Has your organization formally appointed a Data Protection Officer (DPO) or designated an internal Data Protection Lead?",
            "help_text": "The lead can be an internal manager or external consultant for SMEs.",
        },
        {
            "cat": "DP_REG",
            "code": "DP-003",
            "title": "Data Protection Policy & Governance Framework",
            "plain_description": "Existence of an approved, up-to-date internal Data Protection and Privacy Policy communicated to all employees.",
            "legal_reference": "Data Protection Act, 2019, Section 24 & 25",
            "applicability_rule": "All SMEs collecting employee, customer, or vendor data",
            "required_evidence_desc": "Board/management approved Data Protection Policy document and evidence of staff distribution/acknowledgment.",
            "risk_weight": 2.0,
            "potential_consequence": "Regulatory non-compliance findings, operational inconsistency, employee mishandling of sensitive data.",
            "recommended_corrective_action": "Draft, approve, and circulate an organizational Data Protection Policy aligned with the Data Protection Act 2019.",
            "question": "Does your organization have a formal, management-approved Data Protection Policy communicated to staff?",
            "help_text": "Policy must define categories of personal data, handling procedures, and staff responsibilities.",
        },
        {
            "cat": "DP_REG",
            "code": "DP-004",
            "title": "Staff Privacy Training and Awareness",
            "plain_description": "Regular training and awareness sessions for staff on data privacy obligations, handling sensitive personal data, and recognizing data breaches.",
            "legal_reference": "Data Protection Act, 2019, Section 24",
            "applicability_rule": "All SMEs with permanent or contracted staff",
            "required_evidence_desc": "Training attendance registers, presentation slides, or digital course completion certificates within the last 12 months.",
            "risk_weight": 1.5,
            "potential_consequence": "High risk of human-error data leaks, phishing vulnerability, failure to identify breach events.",
            "recommended_corrective_action": "Conduct and document mandatory annual data protection training for all employees handling personal data.",
            "question": "Have your employees undergone data protection and privacy awareness training within the past 12 months?",
            "help_text": "Verify attendance logs and training curriculum.",
        },
        # DP_PRINCIPLES
        {
            "cat": "DP_PRINCIPLES",
            "code": "DP-005",
            "title": "Lawful Basis for Personal Data Processing",
            "plain_description": "Documentation of a recognized lawful basis (consent, contract performance, legal obligation, vital interest, or legitimate interest) for every personal data collection stream.",
            "legal_reference": "Data Protection Act, 2019, Section 30",
            "applicability_rule": "All organizations collecting personal data",
            "required_evidence_desc": "Record of Processing Activities (ROPA) or data asset inventory mapping data fields to lawful bases.",
            "risk_weight": 2.5,
            "potential_consequence": "Unlawful processing claims, administrative fines up to Ksh 5M, voided customer contracts.",
            "recommended_corrective_action": "Compile a Record of Processing Activities (ROPA) detailing data items, lawful basis, and processing purposes.",
            "question": "Has your organization documented the specific legal basis (e.g. contract, legal duty, explicit consent) for each category of personal data collected?",
            "help_text": "Check if a ROPA (Record of Processing Activities) spreadsheet or register is maintained.",
        },
        {
            "cat": "DP_PRINCIPLES",
            "code": "DP-006",
            "title": "Explicit and Informed Consent Mechanism",
            "plain_description": "Obtaining freely given, specific, informed, and unambiguous consent where consent is the basis of processing, with simple withdrawal options.",
            "legal_reference": "Data Protection Act, 2019, Section 32 & 33",
            "applicability_rule": "Organizations relying on consent for marketing or processing sensitive data",
            "required_evidence_desc": "Sample opt-in consent forms, website cookie consent banners, digital opt-in logs, and consent withdrawal procedure.",
            "risk_weight": 2.5,
            "potential_consequence": "Invalidation of marketing databases, ODPC enforcement notices, compensation claims from data subjects.",
            "recommended_corrective_action": "Update customer intake forms and digital portals with unbundled, affirmative opt-in checkboxes and clear withdrawal instructions.",
            "question": "Do customer intake forms and digital channels record affirmative, verifiable consent with clear opt-out options?",
            "help_text": "Pre-ticked boxes do not constitute valid consent under Kenya law.",
        },
        {
            "cat": "DP_PRINCIPLES",
            "code": "DP-007",
            "title": "Data Minimization and Purpose Limitation",
            "plain_description": "Collecting only personal data strictly adequate, relevant, and necessary for defined statutory or business purposes.",
            "legal_reference": "Data Protection Act, 2019, Section 25(b) & (c)",
            "applicability_rule": "All data collection workflows",
            "required_evidence_desc": "Form design audit review showing exclusion of unnecessary national ID, biometric, or personal information.",
            "risk_weight": 1.5,
            "potential_consequence": "Regulatory citations for excessive data retention, heightened exposure in the event of a security breach.",
            "recommended_corrective_action": "Review and prune all customer and employee application forms to eliminate non-essential data collection fields.",
            "question": "Are all data collection forms reviewed periodically to ensure only strictly necessary information is gathered?",
            "help_text": "Ensure you are not requesting sensitive data unless legally required.",
        },
        {
            "cat": "DP_PRINCIPLES",
            "code": "DP-008",
            "title": "Data Retention and Secure Disposal Schedule",
            "plain_description": "Established retention schedules stipulating timeframes for holding personal data and secure destruction procedures upon expiration.",
            "legal_reference": "Data Protection Act, 2019, Section 39",
            "applicability_rule": "All organizations retaining customer or employee records",
            "required_evidence_desc": "Approved Data Retention Schedule policy and certificates of secure digital/physical destruction.",
            "risk_weight": 2.0,
            "potential_consequence": "Statutory non-compliance, increased damage in cyber attacks, failure to satisfy audit reviews.",
            "recommended_corrective_action": "Adopt a defined data retention policy specifying statutory retention periods (e.g. 5-7 years for financial records) and automatic purging.",
            "question": "Does the business enforce a clear retention schedule with secure deletion/shredding for expired personal records?",
            "help_text": "Check if old customer records are securely archived or purged according to schedule.",
        },
        # DP_RIGHTS
        {
            "cat": "DP_RIGHTS",
            "code": "DP-009",
            "title": "Public & Customer Facing Privacy Notice",
            "plain_description": "Easily accessible, plain-language privacy notice published on the website and presented at all points of personal data collection.",
            "legal_reference": "Data Protection Act, 2019, Section 26 & 29",
            "applicability_rule": "All SMEs interacting with customers, website visitors, or partners",
            "required_evidence_desc": "Live website Privacy Policy URL, physical copy displayed at reception/intake, date of last update.",
            "risk_weight": 2.0,
            "potential_consequence": "ODPC warning letters, consumer complaints, non-compliance fines.",
            "recommended_corrective_action": "Publish an ODPC-compliant privacy notice outlining data controller identity, purposes, recipients, and rights.",
            "question": "Is a clear and updated Privacy Notice published on your website and made accessible at data collection points?",
            "help_text": "Verify the privacy notice contains ODPC contact details and describes data subject rights.",
        },
        {
            "cat": "DP_RIGHTS",
            "code": "DP-010",
            "title": "Data Subject Access Request (DSAR) Procedure",
            "plain_description": "Standard operating procedure to receive, verify, and resolve requests from data subjects seeking access, rectification, or deletion within 21 days.",
            "legal_reference": "Data Protection Act, 2019, Section 26, 38, 40",
            "applicability_rule": "All data controllers",
            "required_evidence_desc": "Written DSAR procedure document, dedicated privacy inbox/channel, and DSAR request log.",
            "risk_weight": 2.0,
            "potential_consequence": "ODPC complaint escalation, penalty orders for failure to comply with statutory response deadlines.",
            "recommended_corrective_action": "Establish an internal DSAR logging procedure and designated email address (e.g. privacy@company.co.ke).",
            "question": "Does your organization maintain a documented procedure to handle and resolve Data Subject Access Requests within statutory timelines?",
            "help_text": "Check if requests are logged and answered within 21 calendar days.",
        },
        # DP_SECURITY
        {
            "cat": "DP_SECURITY",
            "code": "DP-011",
            "title": "Technical and Organizational Security Safeguards",
            "plain_description": "Implementation of reasonable measures including role-based access controls, data encryption at rest and in transit, password policies, and firewalls.",
            "legal_reference": "Data Protection Act, 2019, Section 41",
            "applicability_rule": "All information systems processing personal data",
            "required_evidence_desc": "IT security policy, encryption documentation, multi-factor authentication (MFA) enforcement records, backup logs.",
            "risk_weight": 3.0,
            "potential_consequence": "Data breaches, catastrophic data loss, reputational damage, regulatory fines up to Ksh 5M.",
            "recommended_corrective_action": "Implement mandatory MFA on all email and accounting systems, enforce strong password policies, and encrypt sensitive data.",
            "question": "Are appropriate technical safeguards (such as encryption, role-based access control, and MFA) active across systems holding personal data?",
            "help_text": "Ensure databases, spreadsheets, and backup drives containing personal data are restricted and encrypted.",
        },
        {
            "cat": "DP_SECURITY",
            "code": "DP-012",
            "title": "Third-Party Data Processor Agreements (DPAs)",
            "plain_description": "Written contracts with all third-party vendors (cloud providers, payroll software, IT support, marketing agencies) binding them to Data Protection Act standards.",
            "legal_reference": "Data Protection Act, 2019, Section 42",
            "applicability_rule": "Any SME using external software vendors or outsourced service providers",
            "required_evidence_desc": "Signed Data Processing Addenda (DPAs) or contractual confidentiality and security clauses with all key service providers.",
            "risk_weight": 2.5,
            "potential_consequence": "Vicarious liability for vendor breaches, inability to enforce security commitments, regulatory sanctions.",
            "recommended_corrective_action": "Execute standard ODPC-compliant Data Processing Addenda with all outsourced IT, HR, and cloud vendors.",
            "question": "Do you have signed Data Processing Agreements (DPAs) or privacy clauses with all third-party vendors handling company data?",
            "help_text": "Verify vendor contracts include confidentiality, audit rights, and breach notification terms.",
        },
        {
            "cat": "DP_SECURITY",
            "code": "DP-013",
            "title": "Cross-Border Data Transfer Safeguards",
            "plain_description": "Ensuring personal data transferred outside Kenya (e.g. foreign cloud servers, overseas headquarters) complies with statutory transfer safeguards and ODPC approval.",
            "legal_reference": "Data Protection Act, 2019, Section 48 & 49",
            "applicability_rule": "Organizations storing or transferring data outside Kenyan territory",
            "required_evidence_desc": "Standard contractual clauses for cross-border transfers or proof of cloud provider jurisdiction compliance.",
            "risk_weight": 2.0,
            "potential_consequence": "Unlawful cross-border transfer violations, regulatory sanctions, order to repatriate data.",
            "recommended_corrective_action": "Document geographical server locations of all cloud services and ensure standard contractual clauses protect international data transfers.",
            "question": "Are transfers of personal data outside Kenya supported by appropriate safeguards (such as standard contractual clauses or ODPC approval)?",
            "help_text": "Check where cloud email, hosting, and backup servers are geographically located.",
        },
        {
            "cat": "DP_SECURITY",
            "code": "DP-014",
            "title": "Data Protection Impact Assessment (DPIA) Process",
            "plain_description": "Conducting a formal DPIA prior to implementing high-risk processing operations (e.g. large-scale automated profiling, biometric scanning, video surveillance).",
            "legal_reference": "Data Protection Act, 2019, Section 31",
            "applicability_rule": "Organizations undertaking high-risk processing or new technology deployments",
            "required_evidence_desc": "Completed DPIA reports submitted to or ready for ODPC inspection.",
            "risk_weight": 2.0,
            "potential_consequence": "Order to suspend processing operations, administrative fines.",
            "recommended_corrective_action": "Establish a DPIA screening checklist to evaluate privacy risks before rolling out new software or surveillance systems.",
            "question": "Does your organization conduct a Data Protection Impact Assessment (DPIA) before launching high-risk systems or processing operations?",
            "help_text": "Required when implementing biometrics, extensive employee tracking, or health data processing.",
        },
        {
            "cat": "DP_SECURITY",
            "code": "DP-015",
            "title": "Personal Data Breach Incident Response & 72-Hour Notification",
            "plain_description": "Documented incident response plan ensuring any personal data breach is reported to the ODPC within 72 hours of awareness and affected data subjects notified where risk is high.",
            "legal_reference": "Data Protection Act, 2019, Section 43",
            "applicability_rule": "All organizations processing personal data",
            "required_evidence_desc": "Written Incident Response Plan, Data Breach Register, and emergency escalation contact list.",
            "risk_weight": 3.0,
            "potential_consequence": "Severe regulatory fines up to Ksh 5,000,000, public enforcement censure, heightened exposure in civil lawsuits.",
            "recommended_corrective_action": "Formalize a data breach response playbook defining containment, root-cause investigation, and mandatory 72-hour ODPC filing.",
            "question": "Is there a documented incident response procedure to report personal data breaches to the ODPC within 72 hours?",
            "help_text": "Verify breach reporting template and internal escalation procedure exist.",
        },
        {
            "cat": "DP_SECURITY",
            "code": "DP-016",
            "title": "Internal Audit and Periodic Compliance Review",
            "plain_description": "Conducting periodic internal or external audits of data processing activities to ensure continuous compliance with the Act.",
            "legal_reference": "Data Protection Act, 2019, Section 24 & 25",
            "applicability_rule": "All registered data controllers and processors",
            "required_evidence_desc": "Annual compliance audit report or self-assessment documentation.",
            "risk_weight": 1.5,
            "potential_consequence": "Accumulation of undetected compliance gaps, inability to demonstrate accountability during ODPC inspections.",
            "recommended_corrective_action": "Schedule an annual data protection audit and present findings to executive directors.",
            "question": "Has your organization conducted an internal or third-party data protection compliance review within the last 12 months?",
            "help_text": "Verify documentation of past review findings and management action plans.",
        },
    ]

    for item in dp_requirements:
        req = RegulatoryRequirement.query.filter_by(code=item["code"]).first()
        cat = dp_cat_objs[item["cat"]]
        if not req:
            req = RegulatoryRequirement(
                domain_id=dp_domain.id,
                category_id=cat.id,
                code=item["code"],
                title=item["title"],
                plain_description=item["plain_description"],
                legal_reference=item["legal_reference"],
                applicability_rule=item["applicability_rule"],
                required_evidence_desc=item["required_evidence_desc"],
                risk_weight=item["risk_weight"],
                potential_consequence=item["potential_consequence"],
                recommended_corrective_action=item["recommended_corrective_action"],
                effective_date=date(2019, 11, 25),
                verification_status=RegulatoryRequirement.VERIFIED,
                is_active=True,
            )
            db.session.add(req)
            db.session.flush()

            # Add question
            q = ComplianceQuestion(
                requirement_id=req.id,
                question_text=item["question"],
                help_text=item["help_text"],
                display_order=1,
            )
            db.session.add(q)

    # -------------------------------------------------------------
    # DOMAIN 2: TAX COMPLIANCE (KRA)
    # -------------------------------------------------------------
    tax_domain = RegulatoryDomain.query.filter_by(code="TAX").first()
    if not tax_domain:
        tax_domain = RegulatoryDomain(
            code="TAX",
            title="Tax Compliance (KRA)",
            description="Compliance with statutory tax obligations under the Tax Procedures Act, Income Tax Act, VAT Act, and KRA eTIMS electronic invoicing requirements.",
            legal_framework="Tax Procedures Act 2015, Income Tax Act Cap 470, VAT Act 2013",
            icon="fa-receipt",
            display_order=2,
            is_active=True,
        )
        db.session.add(tax_domain)
        db.session.flush()

    tax_categories = {
        "TAX_REG": ("Registration & Identification", "KRA PIN registration, profile updates, and tax obligation activation.", 1),
        "TAX_DIRECT": ("Income & Corporate Tax", "Corporate income tax filing, installment taxes, and annual returns.", 2),
        "TAX_PAYE": ("Employment Taxes (PAYE)", "Accurate deduction and monthly remittance of Pay As You Earn.", 3),
        "TAX_VAT_ETIMS": ("VAT, WHT & eTIMS Invoicing", "VAT filings, electronic tax invoicing (eTIMS), and withholding tax compliance.", 4),
        "TAX_RECORDS": ("Tax Records & Audit Readiness", "Statutory 5-year record retention and tax audit readiness.", 5),
    }

    tax_cat_objs = {}
    for code, (title, desc, order) in tax_categories.items():
        cat = RegulatoryCategory.query.filter_by(domain_id=tax_domain.id, code=code).first()
        if not cat:
            cat = RegulatoryCategory(domain_id=tax_domain.id, code=code, title=title, description=desc, display_order=order)
            db.session.add(cat)
            db.session.flush()
        tax_cat_objs[code] = cat

    tax_requirements = [
        {
            "cat": "TAX_REG",
            "code": "TAX-001",
            "title": "Valid KRA PIN and Correct Tax Obligations",
            "plain_description": "Maintaining an active KRA PIN with all appropriate tax obligations registered on iTax (Income Tax Company, PAYE, VAT, Withholding Tax where applicable).",
            "legal_reference": "Tax Procedures Act, 2015, Section 8, 9, 12",
            "applicability_rule": "All registered business entities in Kenya",
            "required_evidence_desc": "Official KRA PIN Certificate and iTax profile summary showing active registered obligations.",
            "risk_weight": 3.0,
            "potential_consequence": "Inability to bid for tenders, open bank accounts, or obtain a Tax Compliance Certificate (TCC); automatic penalties for unfulfilled dormant obligations.",
            "recommended_corrective_action": "Log in to KRA iTax portal, review active obligations, amend missing or dormant obligations, and download an updated PIN certificate.",
            "question": "Does the business possess a valid KRA PIN certificate with all relevant operational obligations actively registered?",
            "help_text": "Verify on the KRA iTax checker that the PIN is valid and active.",
        },
        {
            "cat": "TAX_REG",
            "code": "TAX-002",
            "title": "Valid Tax Compliance Certificate (TCC)",
            "plain_description": "Holding a current, valid Tax Compliance Certificate issued by the Kenya Revenue Authority confirming no outstanding tax liabilities.",
            "legal_reference": "Tax Procedures Act, 2015, Section 70",
            "applicability_rule": "All commercial enterprises seeking public/private tenders or regulatory licenses",
            "required_evidence_desc": "Current KRA Tax Compliance Certificate (TCC) showing issue date and expiration date.",
            "risk_weight": 2.5,
            "potential_consequence": "Disqualification from commercial contracts, banking restrictions, immediate scrutiny and tax debt enforcement by KRA.",
            "recommended_corrective_action": "Clear any outstanding ledger balances or return filing penalties on iTax and apply for an annual TCC renewal.",
            "question": "Does your organization hold an active and unexpired KRA Tax Compliance Certificate (TCC)?",
            "help_text": "Check expiry date on the TCC document (validity is 12 months from issuance).",
        },
        {
            "cat": "TAX_DIRECT",
            "code": "TAX-003",
            "title": "Annual Corporate Income Tax Return Filing",
            "plain_description": "Filing the audited corporate income tax return on iTax within six months after the end of the accounting year (e.g., by 30th June for December year-end).",
            "legal_reference": "Income Tax Act, Cap 470, Section 52B; Tax Procedures Act, 2015, Section 24",
            "applicability_rule": "All incorporated companies and registered partnerships",
            "required_evidence_desc": "iTax return acknowledgment receipt and audited financial statements for the prior fiscal year.",
            "risk_weight": 3.0,
            "potential_consequence": "Late filing penalty of Ksh 20,000 or 5% of tax payable, late payment interest at 1% per month, and issuance of default assessments.",
            "recommended_corrective_action": "Coordinate with external certified auditors to finalize financial accounts and file the return on iTax before the statutory deadline.",
            "question": "Was the annual corporate income tax return for the preceding accounting year submitted on time with full audited accounts?",
            "help_text": "Verify the iTax e-Return acknowledgment receipt date.",
        },
        {
            "cat": "TAX_DIRECT",
            "code": "TAX-004",
            "title": "Installment Tax Calculations & Timely Payments",
            "plain_description": "Payment of installment taxes by the 20th day of the 4th, 6th, 9th, and 12th months of the financial year where tax liability exceeds Ksh 40,000.",
            "legal_reference": "Income Tax Act, Cap 470, Section 12",
            "applicability_rule": "Entities with corporate income tax liability exceeding Ksh 40,000",
            "required_evidence_desc": "KRA payment registration slips (PRNs) and bank payment confirmation receipts for installment tax payments.",
            "risk_weight": 2.0,
            "potential_consequence": "Installment underpayment penalty of 20% on the shortfall plus 1% late payment interest per month.",
            "recommended_corrective_action": "Calculate projected tax liability quarterly and remit installment PRNs on or before the 20th of the respective quarter.",
            "question": "Are statutory installment tax payments calculated and remitted by the 20th day of each applicable quarter?",
            "help_text": "Check PRN payments for 20th April, 20th June, 20th September, and 20th December (for Dec year-end).",
        },
        {
            "cat": "TAX_PAYE",
            "code": "TAX-005",
            "title": "Monthly PAYE Deduction & Remittance by the 9th",
            "plain_description": "Deduction of PAYE from all taxable employee emoluments using prevailing tax bands and remittance to KRA on or before the 9th of the following month.",
            "legal_reference": "Income Tax Act, Cap 470, Section 37; Income Tax (PAYE) Rules",
            "applicability_rule": "All employers with salaried or wage-earning staff",
            "required_evidence_desc": "Monthly PAYE returns acknowledgment receipts, payroll summaries, and bank payment receipts for the last 3 months.",
            "risk_weight": 3.0,
            "potential_consequence": "Penalty of 25% of tax due or Ksh 10,000 for late filing, 5% late payment penalty, plus 1% compounding interest per month.",
            "recommended_corrective_action": "Finalize monthly payroll by the 30th of each month, generate the iTax CSV return, and pay on or before the 9th.",
            "question": "Are monthly PAYE returns filed and tax payments remitted on or before the 9th of every month without arrears?",
            "help_text": "Review payroll tax receipts for the most recent calendar months.",
        },
        {
            "cat": "TAX_PAYE",
            "code": "TAX-006",
            "title": "Annual PAYE P9 Certificates Issued to Employees",
            "plain_description": "Preparation and issuance of statutory Form P9 (tax deduction card) to all employees by 28th February following the tax year.",
            "legal_reference": "Income Tax (PAYE) Rules, Rule 13",
            "applicability_rule": "All employers",
            "required_evidence_desc": "Copies of signed or digitally distributed P9 forms for staff for the preceding tax year.",
            "risk_weight": 1.5,
            "potential_consequence": "Employee disputes, inability of staff to file annual individual returns, potential KRA audit queries.",
            "recommended_corrective_action": "Generate and distribute signed P9 forms to all employees before end of February each year.",
            "question": "Were statutory P9 tax deduction forms issued to all staff by the end of February for individual return filing?",
            "help_text": "Verify payroll records show distribution of P9 forms.",
        },
        {
            "cat": "TAX_VAT_ETIMS",
            "code": "TAX-007",
            "title": "eTIMS Electronic Tax Invoicing Compliance",
            "plain_description": "Onboarding to KRA's electronic Tax Invoice Management System (eTIMS) and generating electronic tax invoices for every business transaction/sale.",
            "legal_reference": "Tax Procedures Act, 2015, Section 23A; Tax Procedures (Electronic Tax Invoice) Regulations",
            "applicability_rule": "All entities carrying on business in Kenya (mandatory for all businesses)",
            "required_evidence_desc": "eTIMS device or software integration confirmation, sample electronic tax invoices with valid KRA QR codes.",
            "risk_weight": 3.0,
            "potential_consequence": "Disallowance of business expenses for corporate tax deductions (Sec 16(1) ITA), fine of twice the tax due, business disruption.",
            "recommended_corrective_action": "Onboard on eTIMS via online client, eTIMS Lite, or ERP system integration immediately and issue QR-coded invoices for all sales.",
            "question": "Has your organization fully onboarded onto eTIMS and does it generate valid eTIMS invoices for all commercial transactions?",
            "help_text": "Check invoices have the required KRA QR code and invoice control number.",
        },
        {
            "cat": "TAX_VAT_ETIMS",
            "code": "TAX-008",
            "title": "Monthly VAT Return Filing & Payment by 20th",
            "plain_description": "Filing of monthly Value Added Tax (VAT) return on iTax and payment of VAT due on or before the 20th of the following month (or filing nil return if no taxable supplies).",
            "legal_reference": "Value Added Tax Act, 2013, Section 44",
            "applicability_rule": "Entities registered for VAT (turnover >= Ksh 5M or voluntary registration)",
            "required_evidence_desc": "Monthly VAT returns acknowledgment receipts and payment slips for the last 3 months.",
            "risk_weight": 2.5,
            "potential_consequence": "Penalty of Ksh 10,000 or 5% of tax due per month, 5% late payment penalty, plus 1% compounding interest per month.",
            "recommended_corrective_action": "Reconcile sales and purchase eTIMS logs monthly and file the VAT return and payment on or before the 20th.",
            "question": "Are monthly VAT returns filed and settled on or before the 20th of each month on the iTax portal?",
            "help_text": "Select 'Not Applicable' only if entity is not registered for VAT and below statutory turnover threshold.",
        },
        {
            "cat": "TAX_VAT_ETIMS",
            "code": "TAX-009",
            "title": "Withholding Tax (WHT) Deductions & Remittance",
            "plain_description": "Deduction of applicable withholding tax on payments for professional fees, management fees, contractual services, or rent, and remittance to KRA by the 20th.",
            "legal_reference": "Income Tax Act, Cap 470, Section 35",
            "applicability_rule": "Entities engaging professional consultants, service contractors, or paying dividends/royalties",
            "required_evidence_desc": "WHT payment certificates generated on iTax and corresponding bank payment slips.",
            "risk_weight": 2.0,
            "potential_consequence": "Liable for unpaid tax as principal debtor, penalty of 10% of tax, interest at 1% per month.",
            "recommended_corrective_action": "Withhold statutory percentage (e.g. 5% on professional fees) upon payment and remit PRN immediately.",
            "question": "Does the business deduct withholding tax on eligible consultancy, professional, and contractor fees and remit with iTax certificates?",
            "help_text": "Check vendor payment vouchers and corresponding WHT certificates.",
        },
        {
            "cat": "TAX_RECORDS",
            "code": "TAX-010",
            "title": "Statutory 5-Year Financial Record Retention",
            "plain_description": "Maintaining all books of account, invoices, bank statements, receipts, and tax records in Kenya for a minimum statutory period of five (5) years.",
            "legal_reference": "Tax Procedures Act, 2015, Section 23",
            "applicability_rule": "All business taxpayers",
            "required_evidence_desc": "Archived financial records, physical storage or cloud backup policy covering the previous 5 financial years.",
            "risk_weight": 2.0,
            "potential_consequence": "Disallowance of expense deductions during tax audits, penalty of Ksh 2,000,000 or default assessments by the Commissioner.",
            "recommended_corrective_action": "Implement a structured electronic and physical archiving system ensuring records are retrievable for 5 years.",
            "question": "Are complete accounting records, receipts, and eTIMS invoices retained and accessible for a minimum of 5 years?",
            "help_text": "Verify records for the past 5 consecutive financial years are available for audit.",
        },
        {
            "cat": "TAX_RECORDS",
            "code": "TAX-011",
            "title": "Tax Audit Readiness and Periodic Ledger Reconciliation",
            "plain_description": "Conducting periodic reconciliations between financial accounting ledgers and iTax portal balances to ensure no discrepancy or unaccounted liabilities.",
            "legal_reference": "Tax Procedures Act, 2015, Section 59",
            "applicability_rule": "All SMEs",
            "required_evidence_desc": "Recent iTax ledger reconciliation statement or tax health check report.",
            "risk_weight": 1.5,
            "potential_consequence": "Unexpected bank agency notices, unmonitored accumulation of system-generated penalties.",
            "recommended_corrective_action": "Perform a quarterly iTax debt ledger audit and request remission of erroneous penalties from KRA where applicable.",
            "question": "Does your finance team conduct quarterly reconciliations between company books and KRA iTax ledger balances?",
            "help_text": "Check iTax debt ledger to verify zero unexplained pending penalties.",
        },
        {
            "cat": "TAX_RECORDS",
            "code": "TAX-012",
            "title": "Expense Deductibility eTIMS Compliance Verification",
            "plain_description": "Ensuring all business purchases and expenses claimed for tax deduction are supported by valid eTIMS invoices from suppliers.",
            "legal_reference": "Tax Procedures Act, 2015, Section 23A; Income Tax Act, Section 16(1)",
            "applicability_rule": "All registered businesses claiming deductible operating expenses",
            "required_evidence_desc": "Accounts payable policy requiring eTIMS verification before vendor payment and valid supplier QR invoices.",
            "risk_weight": 2.5,
            "potential_consequence": "Disallowance of all non-eTIMS supplier expenses, leading to massive back-tax assessments and corporate income tax penalties.",
            "recommended_corrective_action": "Enforce strict accounting rule: no vendor invoice is processed for payment without a valid KRA eTIMS invoice.",
            "question": "Does your accounts payable process verify that all supplier invoices have a valid eTIMS QR code before approving payments?",
            "help_text": "Verify random sample of vendor invoices against KRA invoice checker.",
        },
        {
            "cat": "TAX_RECORDS",
            "code": "TAX-013",
            "title": "Withholding VAT (WHVAT) Compliance (Where Appointed)",
            "plain_description": "Deduction and remittance of 2% Withholding VAT by appointed withholding agents on or before the 20th of the following month.",
            "legal_reference": "Value Added Tax Act, 2013, Section 42A",
            "applicability_rule": "Businesses appointed as WHVAT agents by the Commissioner",
            "required_evidence_desc": "WHVAT appointment letter (if applicable), payment receipts, and WHVAT certificates.",
            "risk_weight": 1.5,
            "potential_consequence": "Late payment interest and agent liability for unremitted amounts.",
            "recommended_corrective_action": "If appointed as a WHVAT agent, withhold 2% VAT on taxable supplies and remit by the 20th.",
            "question": "If appointed as a Withholding VAT agent, does the business deduct and remit 2% WHVAT in compliance with KRA regulations?",
            "help_text": "Select 'Not Applicable' if your business has not been appointed as a WHVAT agent.",
        },
    ]

    for item in tax_requirements:
        req = RegulatoryRequirement.query.filter_by(code=item["code"]).first()
        cat = tax_cat_objs[item["cat"]]
        if not req:
            req = RegulatoryRequirement(
                domain_id=tax_domain.id,
                category_id=cat.id,
                code=item["code"],
                title=item["title"],
                plain_description=item["plain_description"],
                legal_reference=item["legal_reference"],
                applicability_rule=item["applicability_rule"],
                required_evidence_desc=item["required_evidence_desc"],
                risk_weight=item["risk_weight"],
                potential_consequence=item["potential_consequence"],
                recommended_corrective_action=item["recommended_corrective_action"],
                effective_date=date(2015, 12, 1),
                verification_status=RegulatoryRequirement.VERIFIED,
                is_active=True,
            )
            db.session.add(req)
            db.session.flush()

            # Add question
            q = ComplianceQuestion(
                requirement_id=req.id,
                question_text=item["question"],
                help_text=item["help_text"],
                display_order=1,
            )
            db.session.add(q)

    # -------------------------------------------------------------
    # DOMAIN 3: EMPLOYMENT AND LABOUR COMPLIANCE
    # -------------------------------------------------------------
    labour_domain = RegulatoryDomain.query.filter_by(code="LABOUR").first()
    if not labour_domain:
        labour_domain = RegulatoryDomain(
            code="LABOUR",
            title="Employment & Labour Compliance",
            description="Compliance with Kenya Employment Act 2007, statutory deductions (NSSF & SHIF), Labour Institutions Act, and Occupational Safety & Health Act (OSHA 2007).",
            legal_framework="Employment Act 2007, NSSF Act 2013, Social Health Insurance Act 2023, OSHA 2007",
            icon="fa-users-gear",
            display_order=3,
            is_active=True,
        )
        db.session.add(labour_domain)
        db.session.flush()

    labour_categories = {
        "LABOUR_CONTRACTS": ("Contracts & Employment Records", "Written contracts, job descriptions, and personnel file maintenance.", 1),
        "LABOUR_WAGES_STATUTORY": ("Wages, NSSF & SHIF Deductions", "Minimum wage, itemized payslips, and monthly NSSF/SHIF contributions.", 2),
        "LABOUR_LEAVE": ("Leave & Working Conditions", "Annual leave, sick leave, maternity/paternity leave, and working hour limits.", 3),
        "LABOUR_SAFETY_POLICY": ("Workplace Safety, Policies & Termination", "OSHA safety standards, anti-harassment policies, and fair termination procedures.", 4),
    }

    labour_cat_objs = {}
    for code, (title, desc, order) in labour_categories.items():
        cat = RegulatoryCategory.query.filter_by(domain_id=labour_domain.id, code=code).first()
        if not cat:
            cat = RegulatoryCategory(domain_id=labour_domain.id, code=code, title=title, description=desc, display_order=order)
            db.session.add(cat)
            db.session.flush()
        labour_cat_objs[code] = cat

    labour_requirements = [
        {
            "cat": "LABOUR_CONTRACTS",
            "code": "EMP-001",
            "title": "Written Employment Contracts for All Staff",
            "plain_description": "Execution of written employment contracts for every employee working for a period exceeding three months, detailing job description, remuneration, working hours, and termination notice.",
            "legal_reference": "Employment Act, 2007, Section 9 & 10",
            "applicability_rule": "All employers with full-time, part-time, or contract employees",
            "required_evidence_desc": "Signed copies of employment contracts or letters of appointment on file for all employees.",
            "risk_weight": 3.0,
            "potential_consequence": "Statutory fine up to Ksh 100,000 per violation, adverse awards in the Employment and Labour Relations Court, presumption of employee assertions.",
            "recommended_corrective_action": "Audit employee records and issue compliant written contracts signed by both parties for all staff immediately.",
            "question": "Are valid written employment contracts signed and maintained for 100% of current staff members?",
            "help_text": "Ensure contracts include terms of remuneration, leave entitlement, and notice periods.",
        },
        {
            "cat": "LABOUR_CONTRACTS",
            "code": "EMP-002",
            "title": "Mandatory Employee Personnel Records & Registers",
            "plain_description": "Maintaining a complete personnel file and statutory employment register for every employee containing bio-data, national ID copy, KRA PIN, contract, and disciplinary history.",
            "legal_reference": "Employment Act, 2007, Section 74",
            "applicability_rule": "All employers",
            "required_evidence_desc": "Staff personnel files, employee register containing statutory details specified in Section 74.",
            "risk_weight": 2.0,
            "potential_consequence": "Fine not exceeding Ksh 100,000, citation by Ministry of Labour inspectors.",
            "recommended_corrective_action": "Standardize employee personnel folders and maintain an up-to-date staff master register.",
            "question": "Does the business maintain complete statutory personnel files and employment registers for all staff?",
            "help_text": "Verify files contain copy of ID card, contract, NSSF, and SHIF numbers.",
        },
        {
            "cat": "LABOUR_WAGES_STATUTORY",
            "code": "EMP-003",
            "title": "Itemized Monthly Pay Slips",
            "plain_description": "Providing every employee with a written or digital itemized pay slip detailing basic salary, allowances, overtime, and all statutory and voluntary deductions at the time of payment.",
            "legal_reference": "Employment Act, 2007, Section 20",
            "applicability_rule": "All employers paying wages or salaries",
            "required_evidence_desc": "Sample monthly payslips issued to staff or electronic payroll delivery logs.",
            "risk_weight": 2.0,
            "potential_consequence": "Ministry of Labour penalty notices, civil claims for undocumented wage deductions.",
            "recommended_corrective_action": "Automate payroll software to deliver itemized electronic payslips to staff every pay cycle.",
            "question": "Does every employee receive a detailed, itemized pay slip clearly breaking down gross pay and all statutory deductions?",
            "help_text": "Check sample payslips from recent payroll cycles.",
        },
        {
            "cat": "LABOUR_WAGES_STATUTORY",
            "code": "EMP-004",
            "title": "Statutory Minimum Wage Compliance",
            "plain_description": "Ensuring all employees are paid remuneration at or above the prevailing statutory basic minimum wage rates under the Regulation of Wages Orders.",
            "legal_reference": "Labour Institutions Act, 2007; Regulation of Wages (General) Amendment Orders",
            "applicability_rule": "All employers across all sectors and geographic regions",
            "required_evidence_desc": "Payroll summary showing lowest paid employee rates compared against the prevailing government minimum wage schedule.",
            "risk_weight": 2.5,
            "potential_consequence": "Prosecution by Labour Officers, back-pay court orders, penalties.",
            "recommended_corrective_action": "Adjust basic salaries for any staff member below statutory threshold to conform to the current wage guidelines.",
            "question": "Are all employees (including support, security, and casual staff) paid at or above statutory minimum wage rates?",
            "help_text": "Cross-check lowest salaries against urban and peri-urban gazetted minimum wage tables.",
        },
        {
            "cat": "LABOUR_WAGES_STATUTORY",
            "code": "EMP-005",
            "title": "NSSF Tier I & Tier II Deductions and Remittance by 9th",
            "plain_description": "Deduction of employee NSSF contributions and matching employer contributions (Tier I and Tier II under NSSF Act 2013) and remittance to NSSF on or before the 9th of each month.",
            "legal_reference": "National Social Security Fund (NSSF) Act, 2013, Section 20 & 27",
            "applicability_rule": "All employers with one or more employees",
            "required_evidence_desc": "Monthly NSSF returns receipts and bank payment slips for the last 3 consecutive months.",
            "risk_weight": 3.0,
            "potential_consequence": "Statutory penalty of 5% of unpaid contributions per month, civil suit by NSSF, director liability.",
            "recommended_corrective_action": "Submit monthly NSSF return on the NSSF portal and settle the PRN on or before the 9th of every month.",
            "question": "Are statutory NSSF contributions (Tier I & II) deducted and fully remitted by the 9th of every month without default?",
            "help_text": "Verify NSSF receipts for the most recent month.",
        },
        {
            "cat": "LABOUR_WAGES_STATUTORY",
            "code": "EMP-006",
            "title": "Social Health Insurance Fund (SHIF) Remittance by 9th",
            "plain_description": "Deduction of statutory health insurance contributions (2.75% under Social Health Insurance Act 2023) and remittance to the Social Health Authority by the 9th of following month.",
            "legal_reference": "Social Health Insurance Act, 2023; Social Health Insurance (General) Regulations 2024",
            "applicability_rule": "All employers in Kenya",
            "required_evidence_desc": "Monthly SHIF return submission receipts and corresponding bank payment slips.",
            "risk_weight": 3.0,
            "potential_consequence": "Statutory penalty of 2% of unpaid contributions per month, suspension of healthcare cover for employees.",
            "recommended_corrective_action": "Calculate SHIF deduction at the statutory rate, upload the monthly payroll schedule on the SHA portal, and remit by the 9th.",
            "question": "Are monthly SHIF (Social Health Insurance Fund) contributions deducted and remitted on or before the 9th of each month?",
            "help_text": "Verify monthly SHA employer portal payment acknowledgment receipts.",
        },
        {
            "cat": "LABOUR_WAGES_STATUTORY",
            "code": "EMP-007",
            "title": "National Industrial Training Authority (NITA) Levy",
            "plain_description": "Payment of statutory training levy of Ksh 50 per employee per month to the National Industrial Training Authority (NITA) by the 9th of each month.",
            "legal_reference": "Industrial Training Act, Cap 237; Industrial Training (Training Levy) Order",
            "applicability_rule": "All registered employers",
            "required_evidence_desc": "Monthly NITA payment slips or unified payroll remittance confirmation.",
            "risk_weight": 1.5,
            "potential_consequence": "Penalty of 5% per month on outstanding levy, exclusion from NITA training reimbursement grants.",
            "recommended_corrective_action": "Include Ksh 50 per employee NITA levy in monthly payroll payments via unified KRA portal.",
            "question": "Does the business remit the statutory NITA training levy of Ksh 50 per employee each month?",
            "help_text": "Check unified payroll return or NITA receipt.",
        },
        {
            "cat": "LABOUR_LEAVE",
            "code": "EMP-008",
            "title": "Statutory Annual Leave (Minimum 21 Days)",
            "plain_description": "Granting employees at least 21 working days of fully paid annual leave after every twelve consecutive months of service, with proper leave tracking records.",
            "legal_reference": "Employment Act, 2007, Section 28",
            "applicability_rule": "All employees completing 12 months continuous service",
            "required_evidence_desc": "Company leave policy and updated annual leave schedule/register showing approved leave days and balances.",
            "risk_weight": 2.0,
            "potential_consequence": "Labour officer intervention, mandatory pay in lieu upon separation, employee tribunal claims.",
            "recommended_corrective_action": "Establish an annual leave tracking register and ensure staff utilize statutory leave days within statutory carryover limits.",
            "question": "Do staff receive a minimum of 21 working days of paid annual leave with an active leave tracking system?",
            "help_text": "Verify leave policy and leave application records.",
        },
        {
            "cat": "LABOUR_LEAVE",
            "code": "EMP-009",
            "title": "Maternity (3 Months) and Paternity (2 Weeks) Leave",
            "plain_description": "Providing 3 months fully paid maternity leave without loss of annual leave, and 2 weeks fully paid paternity leave for male employees.",
            "legal_reference": "Employment Act, 2007, Section 29",
            "applicability_rule": "All employers",
            "required_evidence_desc": "HR leave policy document and records of approved maternity and paternity leave granted.",
            "risk_weight": 2.0,
            "potential_consequence": "Unlawful discrimination claims, substantial compensation awards in the Labour Relations Court.",
            "recommended_corrective_action": "Incorporate statutory maternity and paternity rights explicitly into the staff handbook.",
            "question": "Does the organization grant full statutory maternity leave (3 months) and paternity leave (2 weeks) with full basic pay?",
            "help_text": "Check staff handbook and leave approval forms.",
        },
        {
            "cat": "LABOUR_LEAVE",
            "code": "EMP-010",
            "title": "Statutory Sick Leave Entitlement",
            "plain_description": "Granting at least 7 days sick leave with full pay and 7 days with half pay in each period of twelve consecutive months upon presentation of a medical certificate.",
            "legal_reference": "Employment Act, 2007, Section 30",
            "applicability_rule": "Employees completing two continuous months of service",
            "required_evidence_desc": "Sick leave policy and sick leave log accompanied by medical certificates from registered medical practitioners.",
            "risk_weight": 1.5,
            "potential_consequence": "Labour inspector complaints, unlawful deduction claims.",
            "recommended_corrective_action": "Implement a formal sick leave procedure requiring registered medical doctor notes for absences exceeding 2 days.",
            "question": "Is statutory sick leave (minimum 7 days full pay, 7 days half pay) properly documented and administered?",
            "help_text": "Verify policy against Section 30 of the Employment Act 2007.",
        },
        {
            "cat": "LABOUR_SAFETY_POLICY",
            "code": "EMP-011",
            "title": "Workplace Health & Safety (OSHA 2007) Compliance",
            "plain_description": "Ensuring safe working premises, provision of first aid kits, adequate fire extinguishers, clear emergency exits, and sanitary workplace facilities.",
            "legal_reference": "Occupational Safety and Health Act (OSHA), 2007, Section 6, 47, 55",
            "applicability_rule": "All workplaces and business premises",
            "required_evidence_desc": "Annual DOSHS (Directorate of Occupational Safety and Health Services) workplace registration certificate, fire inspection report, or safety audit.",
            "risk_weight": 2.5,
            "potential_consequence": "Workplace closure orders by DOSHS, fines up to Ksh 300,000, civil liability for workplace injuries.",
            "recommended_corrective_action": "Equip premises with serviced fire extinguishers and stocked first aid kits, and register the workplace with DOSHS.",
            "question": "Are the premises equipped with serviced fire extinguishers, stocked first aid kits, and registered with DOSHS where required?",
            "help_text": "Check servicing tags on fire extinguishers and workplace safety audit reports.",
        },
        {
            "cat": "LABOUR_SAFETY_POLICY",
            "code": "EMP-012",
            "title": "Workplace Injury Insurance (WIBA 2007)",
            "plain_description": "Obtaining and maintaining a valid Work Injury Benefits Act (WIBA) insurance policy covering all employees against occupational accidents and diseases.",
            "legal_reference": "Work Injury Benefits Act (WIBA), 2007, Section 7",
            "applicability_rule": "All employers with employees in Kenya",
            "required_evidence_desc": "Current, active WIBA insurance policy schedule and premium payment receipt.",
            "risk_weight": 3.0,
            "potential_consequence": "Criminal prosecution under WIBA, personal director liability for catastrophic injury compensation awards up to millions of shillings.",
            "recommended_corrective_action": "Procure a comprehensive WIBA insurance policy from a licensed insurer covering all full-time and temporary employees.",
            "question": "Does the business maintain an active, fully paid WIBA insurance policy covering all employees?",
            "help_text": "Review current WIBA insurance policy certificate and expiry date.",
        },
        {
            "cat": "LABOUR_SAFETY_POLICY",
            "code": "EMP-013",
            "title": "Workplace Policy on Sexual Harassment (For 20+ Employees)",
            "plain_description": "Implementing a formal, written statement of policy on sexual harassment defining harassment, complaint procedures, and disciplinary sanctions (mandatory for employers with 20 or more staff).",
            "legal_reference": "Employment Act, 2007, Section 6",
            "applicability_rule": "Mandatory for employers with twenty or more employees; best practice for all",
            "required_evidence_desc": "Approved Sexual Harassment Policy document signed by management and circulated to employees.",
            "risk_weight": 2.0,
            "potential_consequence": "Statutory fine up to Ksh 100,000, severe reputational and legal exposure in discrimination lawsuits.",
            "recommended_corrective_action": "Adopt and circulate an anti-sexual harassment policy in accordance with Section 6(2) of the Employment Act 2007.",
            "question": "Does your organization maintain a written anti-sexual harassment policy detailing confidential reporting and disciplinary measures?",
            "help_text": "Mandatory by law if you have 20 or more staff.",
        },
        {
            "cat": "LABOUR_SAFETY_POLICY",
            "code": "EMP-014",
            "title": "Fair Disciplinary and Termination Procedures",
            "plain_description": "Conducting fair disciplinary hearings before termination for misconduct or poor performance, explaining reasons to the employee in the presence of another employee, and issuing statutory notice.",
            "legal_reference": "Employment Act, 2007, Section 41, 43, 45",
            "applicability_rule": "All termination of employment workflows",
            "required_evidence_desc": "Documented HR disciplinary procedure policy and sample show-cause letters and hearing minutes.",
            "risk_weight": 2.5,
            "potential_consequence": "Employment Court awards for unfair termination of up to 12 months gross salary plus damages and legal costs.",
            "recommended_corrective_action": "Mandate that no termination takes place without a formal show-cause letter, hearing invitation with right of representation, and documented hearing.",
            "question": "Does the company follow mandatory Section 41 hearing procedures (show-cause letter and hearing with representation) before any termination?",
            "help_text": "Check HR disciplinary handbook and past hearing minutes.",
        },
    ]

    for item in labour_requirements:
        req = RegulatoryRequirement.query.filter_by(code=item["code"]).first()
        cat = labour_cat_objs[item["cat"]]
        if not req:
            req = RegulatoryRequirement(
                domain_id=labour_domain.id,
                category_id=cat.id,
                code=item["code"],
                title=item["title"],
                plain_description=item["plain_description"],
                legal_reference=item["legal_reference"],
                applicability_rule=item["applicability_rule"],
                required_evidence_desc=item["required_evidence_desc"],
                risk_weight=item["risk_weight"],
                potential_consequence=item["potential_consequence"],
                recommended_corrective_action=item["recommended_corrective_action"],
                effective_date=date(2008, 6, 2),
                verification_status=RegulatoryRequirement.VERIFIED,
                is_active=True,
            )
            db.session.add(req)
            db.session.flush()

            # Add question
            q = ComplianceQuestion(
                requirement_id=req.id,
                question_text=item["question"],
                help_text=item["help_text"],
                display_order=1,
            )
            db.session.add(q)

    db.session.commit()


def seed_statutory_calendar_rules(organization_id: int):
    """Generates standard Kenya statutory recurring compliance deadlines for an organization."""
    # PAYE - 9th of every month
    # NSSF - 9th of every month
    # SHIF - 9th of every month
    # VAT - 20th of every month
    # Withholding Tax - 20th of every month
    # Corporate Annual Return - 30th June
    tax_domain = RegulatoryDomain.query.filter_by(code="TAX").first()
    labour_domain = RegulatoryDomain.query.filter_by(code="LABOUR").first()

    rules = [
        {
            "org_id": organization_id,
            "domain_id": tax_domain.id if tax_domain else None,
            "title": "Monthly PAYE Return & Remittance",
            "description": "File employee PAYE return on iTax and remit deducted tax.",
            "legal_reference": "Income Tax Act, Section 37",
            "statutory_rule": "9th of every month",
            "deadline_type": "STATUTORY_RECURRING",
            "recurrence": "MONTHLY",
            "due_date": date(2026, 4, 9),
            "reminder_days": 5,
        },
        {
            "org_id": organization_id,
            "domain_id": labour_domain.id if labour_domain else None,
            "title": "Monthly NSSF Tier I & Tier II Remittance",
            "description": "Submit monthly payroll schedule to NSSF and settle PRN.",
            "legal_reference": "NSSF Act 2013, Section 20",
            "statutory_rule": "9th of every month",
            "deadline_type": "STATUTORY_RECURRING",
            "recurrence": "MONTHLY",
            "due_date": date(2026, 4, 9),
            "reminder_days": 5,
        },
        {
            "org_id": organization_id,
            "domain_id": labour_domain.id if labour_domain else None,
            "title": "Monthly SHIF Health Insurance Remittance",
            "description": "Submit payroll deductions to Social Health Authority (SHA) and remit contribution.",
            "legal_reference": "Social Health Insurance Act 2023",
            "statutory_rule": "9th of every month",
            "deadline_type": "STATUTORY_RECURRING",
            "recurrence": "MONTHLY",
            "due_date": date(2026, 4, 9),
            "reminder_days": 5,
        },
        {
            "org_id": organization_id,
            "domain_id": tax_domain.id if tax_domain else None,
            "title": "Monthly VAT Return & Payment",
            "description": "File monthly Value Added Tax return on iTax and settle tax due.",
            "legal_reference": "Value Added Tax Act 2013, Section 44",
            "statutory_rule": "20th of every month",
            "deadline_type": "STATUTORY_RECURRING",
            "recurrence": "MONTHLY",
            "due_date": date(2026, 4, 20),
            "reminder_days": 5,
        },
        {
            "org_id": organization_id,
            "domain_id": tax_domain.id if tax_domain else None,
            "title": "Annual Corporate Income Tax Return (Dec Year-End)",
            "description": "Submit audited financial statements and corporate income tax return on iTax.",
            "legal_reference": "Income Tax Act, Section 52B",
            "statutory_rule": "30th June annually",
            "deadline_type": "STATUTORY_RECURRING",
            "recurrence": "ANNUAL",
            "due_date": date(2026, 6, 30),
            "reminder_days": 30,
        },
    ]

    for item in rules:
        existing = ComplianceDeadline.query.filter_by(organization_id=organization_id, title=item["title"]).first()
        if not existing:
            deadline = ComplianceDeadline(
                organization_id=organization_id,
                domain_id=item["domain_id"],
                title=item["title"],
                description=item["description"],
                legal_reference=item["legal_reference"],
                statutory_rule=item["statutory_rule"],
                deadline_type=item["deadline_type"],
                recurrence=item["recurrence"],
                current_due_date=item["due_date"],
                reminder_days_before=item["reminder_days"],
                status=ComplianceDeadline.STATUS_PENDING,
                is_active=True,
            )
            db.session.add(deadline)

    db.session.commit()

