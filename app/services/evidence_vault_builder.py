"""
COMPLIANCE RISK ANALYTICS SYSTEM (CRAS)
Comprehensive Watermarked Statutory Evidence Vault Builder
Generates organized, watermarked statutory PDF documents matching each folder description
and packages them into a ready-to-download ZIP archive.
"""

import io
import os
import zipfile
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.services.pdf_evidence_generator import (
    EvidenceCanvas, _get_base_styles,
    generate_kra_tax_compliance_cert,
    generate_odpc_registration_cert,
    generate_wiba_policy_schedule,
    generate_osha_inspection_report,
    generate_etims_signoff_cert,
)


def _build_doc(elements, watermark_text=None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    
    class CustomWatermarkCanvas(EvidenceCanvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, watermark_text=watermark_text or "STATUTORY COMPLIANCE EVIDENCE", **kwargs)
            
    doc.build(elements, canvasmaker=CustomWatermarkCanvas)
    return buf.getvalue()


def generate_paye_remittance_receipt(org_name: str, kra_pin: str) -> bytes:
    """Generates authentic KRA PAYE Monthly Remittance & PRN Receipt."""
    styles = _get_base_styles()
    primary = colors.HexColor("#172B4D")
    border_col = colors.HexColor("#E2E8F0")
    bg_light = colors.HexColor("#F8FAFC")
    green = colors.HexColor("#16A34A")

    elements = [
        Spacer(1, 10),
        Paragraph("REPUBLIC OF KENYA", styles["DocTitle"]),
        Paragraph("KENYA REVENUE AUTHORITY", styles["AgencyHeader"]),
        Paragraph("iTax PAYMENT REGISTRATION & STATUTORY REMITTANCE ACKNOWLEDGMENT", styles["DocSubTitle"]),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#DC2626"), spaceBefore=2, spaceAfter=10),
        Paragraph("MONTHLY PAYE RETURN & BANK REMITTANCE RECEIPT", styles["CertHeading"]),
        Paragraph("<i>Issued Pursuant to Section 37 of the Income Tax Act (Cap. 470) & Tax Procedures Act 2015</i>", styles["NoticeText"]),
        Spacer(1, 14),
    ]

    prn_data = [
        [Paragraph("<b>Payment Reg. Number (PRN):</b>", styles["Body"]), Paragraph("<b>PRN-2026-PAYE-981240</b>", styles["BodyBold"]), Paragraph("<b>Payment Date:</b>", styles["Body"]), Paragraph("08 November 2026", styles["Body"])],
        [Paragraph("<b>Employer Name:</b>", styles["Body"]), Paragraph(f"<b>{org_name}</b>", styles["BodyBold"]), Paragraph("<b>Statutory Due Date:</b>", styles["Body"]), Paragraph("<b>09 November 2026</b>", styles["BodyBold"])],
        [Paragraph("<b>Employer KRA PIN:</b>", styles["Body"]), Paragraph(f"<b>{kra_pin}</b>", styles["BodyBold"]), Paragraph("<b>Tax Period:</b>", styles["Body"]), Paragraph("October 2026 Payroll", styles["Body"])],
        [Paragraph("<b>Payment Status:</b>", styles["Body"]), Paragraph("<font color='#16A34A'><b>SETTLED & CONFIRMED</b></font>", styles["BodyBold"]), Paragraph("<b>Receiving Bank:</b>", styles["Body"]), Paragraph("KCB Bank Kenya Ltd (Times Tower)", styles["Body"])],
    ]
    t = Table(prn_data, colWidths=[130, 160, 110, 120])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>Payroll Statutory Deductions Breakdown</b>", styles["SectionHeader"]))
    heads_data = [
        [Paragraph("Tax Obligation Head", styles["TableHead"]), Paragraph("Staff Count", styles["TableHead"]), Paragraph("Taxable Payroll Gross", styles["TableHead"]), Paragraph("Tax Deducted & Remitted", styles["TableHead"])],
        [Paragraph("Pay As You Earn (PAYE)", styles["TableCellBold"]), Paragraph("35 Employees", styles["TableCell"]), Paragraph("KES 2,450,000.00", styles["TableCell"]), Paragraph("<font color='#16A34A'><b>KES 412,500.00</b></font>", styles["TableCellBold"])],
        [Paragraph("Affordable Housing Levy (AHL)", styles["TableCellBold"]), Paragraph("35 Employees", styles["TableCell"]), Paragraph("KES 2,450,000.00", styles["TableCell"]), Paragraph("KES 73,500.00 (1.5% + 1.5%)", styles["TableCellBold"])],
        [Paragraph("NITA Industrial Training Levy", styles["TableCellBold"]), Paragraph("35 Employees", styles["TableCell"]), Paragraph("Cap. 237 Statutory Levy", styles["TableCell"]), Paragraph("KES 1,750.00 (KES 50/staff)", styles["TableCellBold"])],
        [Paragraph("<b>Total Statutory Payment Settled</b>", styles["TableCellBold"]), Paragraph("-", styles["TableCell"]), Paragraph("-", styles["TableCell"]), Paragraph("<b>KES 487,750.00</b>", styles["TableCellBold"])],
    ]
    ht = Table(heads_data, colWidths=[160, 90, 130, 140])
    ht.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, bg_light]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E2E8F0")),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(ht)
    elements.append(Spacer(1, 14))

    cert_text = (
        "<b>STATUTORY COMPLIANCE RECEIPT:</b> The Kenya Revenue Authority hereby acknowledges settlement of the above "
        "statutory payroll deductions via Central Bank of Kenya settlement switch. The employer has met its obligations "
        "under Section 37 of the Income Tax Act for the stated period."
    )
    elements.append(Paragraph(cert_text, styles["Body"]))
    elements.append(Spacer(1, 18))

    sig_data = [
        [
            Paragraph("<b>KRA DOMESTIC TAXES CASH OFFICE</b><br/><br/><i>[Electronic Stamp & Seal]</i><br/><b>Verified Electronic Payment</b><br/>Ref: CBK/EFT/2026/0991823", styles["Body"]),
            Paragraph("<b>COMMISSIONER GENERAL, KRA</b><br/><br/>Times Tower, Haile Selassie Ave<br/>Nairobi, Kenya", styles["SealText"]),
        ]
    ]
    st = Table(sig_data, colWidths=[270, 250])
    st.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(st)

    return _build_doc(elements, watermark_text="KRA PAYE REMITTANCE • VERIFIED")


def generate_vat_return_acknowledgment(org_name: str, kra_pin: str) -> bytes:
    """Generates authentic KRA VAT Monthly Return Filing Acknowledgment."""
    styles = _get_base_styles()
    primary = colors.HexColor("#172B4D")
    border_col = colors.HexColor("#E2E8F0")
    bg_light = colors.HexColor("#F8FAFC")

    elements = [
        Spacer(1, 10),
        Paragraph("REPUBLIC OF KENYA", styles["DocTitle"]),
        Paragraph("KENYA REVENUE AUTHORITY", styles["AgencyHeader"]),
        Paragraph("DOMESTIC TAXES DEPARTMENT - VALUE ADDED TAX (VAT)", styles["DocSubTitle"]),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#DC2626"), spaceBefore=2, spaceAfter=10),
        Paragraph("STATUTORY VAT RETURN FILING ACKNOWLEDGMENT RECEIPT", styles["CertHeading"]),
        Paragraph("<i>Filed Pursuant to Section 44 of the Value Added Tax Act, No. 35 of 2013</i>", styles["NoticeText"]),
        Spacer(1, 14),
    ]

    vat_data = [
        [Paragraph("<b>Acknowledgment No:</b>", styles["Body"]), Paragraph("<b>KRA-VAT-ACK-2026-10492</b>", styles["BodyBold"]), Paragraph("<b>Filing Date:</b>", styles["Body"]), Paragraph("18 November 2026", styles["Body"])],
        [Paragraph("<b>Taxpayer Name:</b>", styles["Body"]), Paragraph(f"<b>{org_name}</b>", styles["BodyBold"]), Paragraph("<b>Statutory Due Date:</b>", styles["Body"]), Paragraph("<b>20 November 2026</b>", styles["BodyBold"])],
        [Paragraph("<b>Taxpayer KRA PIN:</b>", styles["Body"]), Paragraph(f"<b>{kra_pin}</b>", styles["BodyBold"]), Paragraph("<b>Tax Period:</b>", styles["Body"]), Paragraph("October 2026", styles["Body"])],
        [Paragraph("<b>Filing Status:</b>", styles["Body"]), Paragraph("<font color='#16A34A'><b>SUBMITTED & VALIDATED</b></font>", styles["BodyBold"]), Paragraph("<b>eTIMS Match Ratio:</b>", styles["Body"]), Paragraph("<font color='#16A34A'><b>100% Reconciled</b></font>", styles["BodyBold"])],
    ]
    t = Table(vat_data, colWidths=[130, 160, 110, 120])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>VAT Return Computation Schedule</b>", styles["SectionHeader"]))
    v_data = [
        [Paragraph("VAT Return Line Item", styles["TableHead"]), Paragraph("Statutory Rate", styles["TableHead"]), Paragraph("Taxable Amount (KES)", styles["TableHead"]), Paragraph("VAT Output / Input (KES)", styles["TableHead"])],
        [Paragraph("General Rated Sales (16%)", styles["TableCellBold"]), Paragraph("16.0%", styles["TableCell"]), Paragraph("KES 4,800,000.00", styles["TableCell"]), Paragraph("KES 768,000.00 (Output)", styles["TableCellBold"])],
        [Paragraph("Zero-Rated / Exempt Supplies", styles["TableCellBold"]), Paragraph("0.0% / Exempt", styles["TableCell"]), Paragraph("KES 650,000.00", styles["TableCell"]), Paragraph("KES 0.00", styles["TableCell"])],
        [Paragraph("Eligible Input Tax Deductions", styles["TableCellBold"]), Paragraph("16.0%", styles["TableCell"]), Paragraph("KES 2,950,000.00", styles["TableCell"]), Paragraph("KES 472,000.00 (Input)", styles["TableCellBold"])],
        [Paragraph("<b>Net VAT Payable Settled</b>", styles["TableCellBold"]), Paragraph("-", styles["TableCell"]), Paragraph("-", styles["TableCell"]), Paragraph("<b>KES 296,000.00</b>", styles["TableCellBold"])],
    ]
    vt = Table(v_data, colWidths=[170, 90, 130, 130])
    vt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, bg_light]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E2E8F0")),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(vt)
    elements.append(Spacer(1, 14))

    cert_text = (
        "<b>OFFICIAL ACKNOWLEDGMENT:</b> The Commissioner for Domestic Taxes confirms that the monthly VAT Return for the "
        "period stated above has been received and verified via the iTax e-Filing Engine. Invoices declared match the "
        "electronic fiscal records transmitted via the eTIMS platform."
    )
    elements.append(Paragraph(cert_text, styles["Body"]))
    elements.append(Spacer(1, 18))

    sig_data = [
        [
            Paragraph("<b>FOR: COMMISSIONER FOR DOMESTIC TAXES</b><br/><br/><i>[Digitally Authenticated]</i><br/><b>KRA iTax VAT Operations</b><br/>PRN Receipt Ref: VAT-PRN-881920", styles["Body"]),
            Paragraph("<b>KENYA REVENUE AUTHORITY</b><br/><br/>VAT Automated Clearing System<br/>ISO 9001:2015 Registered", styles["SealText"]),
        ]
    ]
    st = Table(sig_data, colWidths=[270, 250])
    st.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(st)

    return _build_doc(elements, watermark_text="KRA VAT FILING • VERIFIED RECEIPT")


def generate_corporate_tax_return(org_name: str, kra_pin: str) -> bytes:
    """Generates authentic KRA Annual Corporate Income Tax Return (IT2C) & Audited Statement."""
    styles = _get_base_styles()
    primary = colors.HexColor("#172B4D")
    border_col = colors.HexColor("#E2E8F0")
    bg_light = colors.HexColor("#F8FAFC")

    elements = [
        Spacer(1, 10),
        Paragraph("REPUBLIC OF KENYA", styles["DocTitle"]),
        Paragraph("KENYA REVENUE AUTHORITY", styles["AgencyHeader"]),
        Paragraph("DOMESTIC TAXES DEPARTMENT - CORPORATE INCOME TAX", styles["DocSubTitle"]),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#DC2626"), spaceBefore=2, spaceAfter=10),
        Paragraph("ANNUAL CORPORATE INCOME TAX RETURN (FORM IT2C)", styles["CertHeading"]),
        Paragraph("<i>Filed Pursuant to Section 52B of the Income Tax Act (Cap. 470)</i>", styles["NoticeText"]),
        Spacer(1, 14),
    ]

    cit_data = [
        [Paragraph("<b>Return Reference:</b>", styles["Body"]), Paragraph("<b>KRA-IT2C-2025-08194</b>", styles["BodyBold"]), Paragraph("<b>Filing Date:</b>", styles["Body"]), Paragraph("25 June 2026", styles["Body"])],
        [Paragraph("<b>Company Name:</b>", styles["Body"]), Paragraph(f"<b>{org_name}</b>", styles["BodyBold"]), Paragraph("<b>Year of Income:</b>", styles["Body"]), Paragraph("<b>2025 Financial Year</b>", styles["BodyBold"])],
        [Paragraph("<b>Company PIN:</b>", styles["Body"]), Paragraph(f"<b>{kra_pin}</b>", styles["BodyBold"]), Paragraph("<b>Accounting Period:</b>", styles["Body"]), Paragraph("01 Jan 2025 – 31 Dec 2025", styles["Body"])],
        [Paragraph("<b>Assessment Status:</b>", styles["Body"]), Paragraph("<font color='#16A34A'><b>ASSESSED & FULLY PAID</b></font>", styles["BodyBold"]), Paragraph("<b>Auditor PIN:</b>", styles["Body"]), Paragraph("P051189201K (ICPAK Reg)", styles["Body"])],
    ]
    t = Table(cit_data, colWidths=[130, 160, 110, 120])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>Statutory Profit & Tax Computation Summary</b>", styles["SectionHeader"]))
    heads_data = [
        [Paragraph("Audited Accounts Item", styles["TableHead"]), Paragraph("Statutory Reference", styles["TableHead"]), Paragraph("Amount (KES)", styles["TableHead"])],
        [Paragraph("Gross Commercial Turnover / Revenue", styles["TableCellBold"]), Paragraph("Sec 3 Income Tax Act", styles["TableCell"]), Paragraph("KES 42,500,000.00", styles["TableCell"])],
        [Paragraph("Allowable Business Operating Expenses", styles["TableCellBold"]), Paragraph("Sec 15 Income Tax Act", styles["TableCell"]), Paragraph("KES (34,800,000.00)", styles["TableCell"])],
        [Paragraph("Statutory Capital Allowances (Depreciation Wear & Tear)", styles["TableCellBold"]), Paragraph("Second Schedule ITA", styles["TableCell"]), Paragraph("KES (1,450,000.00)", styles["TableCell"])],
        [Paragraph("Taxable Adjusted Corporate Profit", styles["TableCellBold"]), Paragraph("Sec 4 Income Tax Act", styles["TableCell"]), Paragraph("KES 6,250,000.00", styles["TableCellBold"])],
        [Paragraph("<b>Corporate Tax Due (30% Resident Rate)</b>", styles["TableCellBold"]), Paragraph("Third Schedule ITA", styles["TableCell"]), Paragraph("<b>KES 1,875,000.00</b>", styles["TableCellBold"])],
        [Paragraph("Less: Installment Taxes Paid (Sec 12 ITA)", styles["TableCellBold"]), Paragraph("Paid in 4 Quarters", styles["TableCell"]), Paragraph("KES (1,875,000.00)", styles["TableCell"])],
        [Paragraph("<b>Balance of Tax Due (Nil Outstanding)</b>", styles["TableCellBold"]), Paragraph("-", styles["TableCell"]), Paragraph("<font color='#16A34A'><b>KES 0.00 (NIL BALANCE)</b></font>", styles["TableCellBold"])],
    ]
    ht = Table(heads_data, colWidths=[230, 150, 140])
    ht.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, bg_light]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E2E8F0")),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(ht)
    elements.append(Spacer(1, 14))

    cert_text = (
        "<b>CERTIFICATE OF TAX RETURN LODGMENT:</b> The above self-assessment return has been duly received "
        "and accepted by the Kenya Revenue Authority. Audited accounts certified by an authorized ICPAK licensed auditor "
        "are on record."
    )
    elements.append(Paragraph(cert_text, styles["Body"]))
    elements.append(Spacer(1, 18))

    sig_data = [
        [
            Paragraph("<b>MANAGING DIRECTOR & PRINCIPAL OFFICER</b><br/><br/><i>[Digitally Signed by Taxpayer]</i><br/>Accounting Officer<br/>CRAS Verified Business Entity", styles["Body"]),
            Paragraph("<b>COMMISSIONER FOR DOMESTIC TAXES</b><br/><br/>KRA Large & Medium Taxpayers Office<br/>Nairobi, Republic of Kenya", styles["SealText"]),
        ]
    ]
    st = Table(sig_data, colWidths=[270, 250])
    st.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(st)

    return _build_doc(elements, watermark_text="KRA CORPORATE TAX RETURN • FILED")


def generate_data_protection_policy(org_name: str) -> bytes:
    """Generates an authentic Data Protection Policy & Privacy Notice."""
    styles = _get_base_styles()
    primary = colors.HexColor("#172B4D")
    odpc_blue = colors.HexColor("#0284C7")
    border_col = colors.HexColor("#E2E8F0")
    bg_light = colors.HexColor("#F8FAFC")

    elements = [
        Spacer(1, 10),
        Paragraph("ORGANIZATIONAL COMPLIANCE DIRECTIVE", styles["DocTitle"]),
        Paragraph("STATUTORY DATA PROTECTION POLICY & PRIVACY CHARTER", ParagraphStyle("H1", parent=styles["AgencyHeader"], textColor=odpc_blue)),
        Paragraph("<i>Formulated in Strict Compliance with Kenya Data Protection Act, 2019 & ODPC Regulations 2021</i>", styles["NoticeText"]),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=2, color=odpc_blue, spaceBefore=2, spaceAfter=10),
        Paragraph(f"{org_name.upper()} • DATA GOVERNANCE FRAMEWORK", styles["CertHeading"]),
        Spacer(1, 14),
    ]

    pol_meta = [
        [Paragraph("<b>Policy Reference:</b>", styles["Body"]), Paragraph("<b>DP-POL-2026-v2.1</b>", styles["BodyBold"]), Paragraph("<b>Effective Date:</b>", styles["Body"]), Paragraph("01 January 2026", styles["Body"])],
        [Paragraph("<b>Entity Covered:</b>", styles["Body"]), Paragraph(f"<b>{org_name}</b>", styles["BodyBold"]), Paragraph("<b>Next Review Date:</b>", styles["Body"]), Paragraph("31 December 2026", styles["Body"])],
        [Paragraph("<b>Statutory Jurisdiction:</b>", styles["Body"]), Paragraph("Republic of Kenya (ODPC)", styles["Body"]), Paragraph("<b>Approval Level:</b>", styles["Body"]), Paragraph("Board of Directors", styles["BodyBold"])],
        [Paragraph("<b>DPO Contact:</b>", styles["Body"]), Paragraph("dpo@organization.co.ke", styles["Body"]), Paragraph("<b>ODPC Reg Category:</b>", styles["Body"]), Paragraph("Data Controller & Processor", styles["Body"])],
    ]
    t = Table(pol_meta, colWidths=[130, 160, 110, 120])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>Statutory Principles of Personal Data Processing (Section 25)</b>", styles["SectionHeader"]))
    principles_data = [
        [Paragraph("Statutory Principle", styles["TableHead"]), Paragraph("Statutory Legal Mandate", styles["TableHead"]), Paragraph("Implementation Protocol", styles["TableHead"])],
        [Paragraph("Lawfulness, Fairness & Transparency", styles["TableCellBold"]), Paragraph("Sec 25(a) Data Protection Act", styles["TableCell"]), Paragraph("Clear privacy notices displayed on all customer & staff touchpoints.", styles["TableCell"])],
        [Paragraph("Purpose Limitation", styles["TableCellBold"]), Paragraph("Sec 25(b) Data Protection Act", styles["TableCell"]), Paragraph("Data collected strictly for explicit, specified and legitimate purposes.", styles["TableCell"])],
        [Paragraph("Data Minimization", styles["TableCellBold"]), Paragraph("Sec 25(c) Data Protection Act", styles["TableCell"]), Paragraph("Collection restricted to what is necessary for the defined processing.", styles["TableCell"])],
        [Paragraph("Accuracy & Rectification", styles["TableCellBold"]), Paragraph("Sec 25(d) Data Protection Act", styles["TableCell"]), Paragraph("Regular auditing and prompt correction of inaccurate personal records.", styles["TableCell"])],
        [Paragraph("Storage Limitation", styles["TableCellBold"]), Paragraph("Sec 25(e) Data Protection Act", styles["TableCell"]), Paragraph("Retention periods defined; automatic archival/destruction after 7 years.", styles["TableCell"])],
        [Paragraph("Integrity, Confidentiality & Security", styles["TableCellBold"]), Paragraph("Sec 25(f), Sec 41 DPA", styles["TableCell"]), Paragraph("AES-256 encryption at rest, TLS in transit, and role-based access.", styles["TableCell"])],
    ]
    pt = Table(principles_data, colWidths=[150, 140, 230])
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(pt)
    elements.append(Spacer(1, 14))

    statement = (
        "<b>DATA SUBJECT RIGHTS ASSURANCE:</b> In accordance with Section 26 of the Act, all individuals have "
        "the right to be informed, access their data, object to processing, rectify incorrect information, "
        "and request erasure. All Data Subject Access Requests (DSAR) are processed within twenty-one (21) days free of charge."
    )
    elements.append(Paragraph(statement, styles["Body"]))
    elements.append(Spacer(1, 16))

    sig_data = [
        [
            Paragraph("<b>DATA PROTECTION OFFICER (DPO)</b><br/><br/><i>[Formally Adopted]</i><br/>Head of Compliance & Legal Affairs<br/>Registered with ODPC Kenya", styles["Body"]),
            Paragraph("<b>MANAGING DIRECTOR & CEO</b><br/><br/>Executive Board Approval<br/>CRAS Compliance Governance Oversight", styles["SealText"]),
        ]
    ]
    st = Table(sig_data, colWidths=[270, 250])
    st.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(st)

    return _build_doc(elements, watermark_text="DATA PROTECTION POLICY • OFFICIAL")


def generate_dpo_appointment_letter(org_name: str) -> bytes:
    """Generates official Data Protection Officer (DPO) Designation Charter."""
    styles = _get_base_styles()
    primary = colors.HexColor("#172B4D")
    odpc_blue = colors.HexColor("#0284C7")
    border_col = colors.HexColor("#E2E8F0")
    bg_light = colors.HexColor("#F8FAFC")

    elements = [
        Spacer(1, 10),
        Paragraph("OFFICIAL DESIGNATION CHARTER", styles["DocTitle"]),
        Paragraph("APPOINTMENT OF DATA PROTECTION OFFICER (DPO)", ParagraphStyle("H1", parent=styles["AgencyHeader"], textColor=odpc_blue)),
        Paragraph("<i>Issued Pursuant to Section 24 of the Data Protection Act, 2019</i>", styles["NoticeText"]),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=2, color=odpc_blue, spaceBefore=2, spaceAfter=10),
        Paragraph(f"{org_name.upper()} • STATUTORY COMPLIANCE OFFICE", styles["CertHeading"]),
        Spacer(1, 14),
    ]

    dpo_meta = [
        [Paragraph("<b>Designation Ref:</b>", styles["Body"]), Paragraph("<b>DPO-CHARTER-2026-004</b>", styles["BodyBold"]), Paragraph("<b>Effective Date:</b>", styles["Body"]), Paragraph("15 January 2026", styles["Body"])],
        [Paragraph("<b>Appointed DPO:</b>", styles["Body"]), Paragraph("<b>Adv. Sarah Cherono, LL.B</b>", styles["BodyBold"]), Paragraph("<b>Tenure:</b>", styles["Body"]), Paragraph("3 Years (Renewable)", styles["Body"])],
        [Paragraph("<b>Appointing Authority:</b>", styles["Body"]), Paragraph(f"Board of Directors, {org_name}", styles["Body"]), Paragraph("<b>Reporting Line:</b>", styles["Body"]), Paragraph("Direct to Chief Executive Officer", styles["BodyBold"])],
        [Paragraph("<b>ODPC Notification:</b>", styles["Body"]), Paragraph("Lodge Ref: ODPC/NOTIF/DPO/8812", styles["Body"]), Paragraph("<b>Independence:</b>", styles["Body"]), Paragraph("Guaranteed under Sec 24(5)", styles["BodyBold"])],
    ]
    t = Table(dpo_meta, colWidths=[130, 160, 110, 120])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>Statutory Roles & Responsibilities of the DPO (Section 24)</b>", styles["SectionHeader"]))
    roles_data = [
        [Paragraph("Mandate Area", styles["TableHead"]), Paragraph("Statutory Reference", styles["TableHead"]), Paragraph("Key Deliverables & Powers", styles["TableHead"])],
        [Paragraph("Advisory & Guidance", styles["TableCellBold"]), Paragraph("Sec 24(1)(a) DPA", styles["TableCell"]), Paragraph("Advise management and employees on statutory data protection obligations.", styles["TableCell"])],
        [Paragraph("Compliance Auditing", styles["TableCellBold"]), Paragraph("Sec 24(1)(b) DPA", styles["TableCell"]), Paragraph("Monitor internal compliance, conduct quarterly audits, and direct training.", styles["TableCell"])],
        [Paragraph("DPIA Oversight", styles["TableCellBold"]), Paragraph("Sec 31 DPA", styles["TableCell"]), Paragraph("Oversee Data Protection Impact Assessments prior to new system rollouts.", styles["TableCell"])],
        [Paragraph("ODPC Liaison", styles["TableCellBold"]), Paragraph("Sec 24(1)(d) DPA", styles["TableCell"]), Paragraph("Serve as primary contact point for the Data Commissioner on all matters.", styles["TableCell"])],
        [Paragraph("Breach Notification", styles["TableCellBold"]), Paragraph("Sec 43 DPA", styles["TableCell"]), Paragraph("Notify ODPC within 72 hours of becoming aware of any personal data breach.", styles["TableCell"])],
    ]
    rt = Table(roles_data, colWidths=[140, 130, 250])
    rt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(rt)
    elements.append(Spacer(1, 14))

    statement = (
        "<b>STATUTORY INDEPENDENCE & PROTECTION:</b> Under Section 24(5) of the Data Protection Act, "
        "the designated Data Protection Officer shall perform their duties with full operational independence "
        "and shall not be dismissed or penalized for performing statutory compliance obligations."
    )
    elements.append(Paragraph(statement, styles["Body"]))
    elements.append(Spacer(1, 16))

    sig_data = [
        [
            Paragraph("<b>MANAGING DIRECTOR & CEO</b><br/><br/><i>[Executive Appointment]</i><br/>Board of Directors Representative<br/>Corporate Seal Affixed", styles["Body"]),
            Paragraph("<b>ACCEPTED BY DATA PROTECTION OFFICER</b><br/><br/>Adv. Sarah Cherono, LL.B<br/>Certified Data Protection Officer", styles["SealText"]),
        ]
    ]
    st = Table(sig_data, colWidths=[270, 250])
    st.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(st)

    return _build_doc(elements, watermark_text="DPO APPOINTMENT CHARTER • VERIFIED")


def generate_nssf_remittance_schedule(org_name: str, employee_count: int = 35) -> bytes:
    """Generates authentic NSSF Tier I & Tier II Statutory Contribution Schedule & Receipt."""
    styles = _get_base_styles()
    primary = colors.HexColor("#172B4D")
    border_col = colors.HexColor("#E2E8F0")
    bg_light = colors.HexColor("#F8FAFC")

    elements = [
        Spacer(1, 10),
        Paragraph("REPUBLIC OF KENYA", styles["DocTitle"]),
        Paragraph("NATIONAL SOCIAL SECURITY FUND (NSSF)", styles["AgencyHeader"]),
        Paragraph("PENSION CONTRIBUTIONS & STATUTORY COMPLIANCE ACKNOWLEDGMENT", styles["DocSubTitle"]),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=2, color=primary, spaceBefore=2, spaceAfter=10),
        Paragraph("STATUTORY NSSF TIER I & TIER II CONTRIBUTION SCHEDULE", styles["CertHeading"]),
        Paragraph("<i>Compliant with Section 20 of the National Social Security Fund Act, No. 45 of 2013</i>", styles["NoticeText"]),
        Spacer(1, 14),
    ]

    nssf_meta = [
        [Paragraph("<b>NSSF Employer Reg No:</b>", styles["Body"]), Paragraph("<b>NSSF-ER-2024-88123</b>", styles["BodyBold"]), Paragraph("<b>Filing Date:</b>", styles["Body"]), Paragraph("07 November 2026", styles["Body"])],
        [Paragraph("<b>Employer Name:</b>", styles["Body"]), Paragraph(f"<b>{org_name}</b>", styles["BodyBold"]), Paragraph("<b>Statutory Due Date:</b>", styles["Body"]), Paragraph("<b>09 November 2026</b>", styles["BodyBold"])],
        [Paragraph("<b>Payroll Period:</b>", styles["Body"]), Paragraph("October 2026", styles["Body"]), Paragraph("<b>Insured Employees:</b>", styles["Body"]), Paragraph(f"<b>{employee_count} Members</b>", styles["BodyBold"])],
        [Paragraph("<b>PRN Settlement Status:</b>", styles["Body"]), Paragraph("<font color='#16A34A'><b>SETTLED & CLEARED</b></font>", styles["BodyBold"]), Paragraph("<b>NSSF e-Receipt No:</b>", styles["Body"]), Paragraph("NSSF-REC-2026-99014", styles["BodyBold"])],
    ]
    t = Table(nssf_meta, colWidths=[130, 160, 110, 120])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>NSSF Statutory Contribution Breakdown (NSSF Act 2013)</b>", styles["SectionHeader"]))
    heads_data = [
        [Paragraph("Pension Tier Category", styles["TableHead"]), Paragraph("Earnings Limit Band", styles["TableHead"]), Paragraph("Employer Share (6%)", styles["TableHead"]), Paragraph("Employee Share (6%)", styles["TableHead"]), Paragraph("Total Remitted", styles["TableHead"])],
        [Paragraph("Tier I Pension Contribution", styles["TableCellBold"]), Paragraph("Lower Earnings (Up to KES 7,000)", styles["TableCell"]), Paragraph("KES 14,700.00", styles["TableCell"]), Paragraph("KES 14,700.00", styles["TableCell"]), Paragraph("KES 29,400.00", styles["TableCellBold"])],
        [Paragraph("Tier II Pension Contribution", styles["TableCellBold"]), Paragraph("Upper Earnings (KES 7,001 - 36,000)", styles["TableCell"]), Paragraph("KES 60,900.00", styles["TableCell"]), Paragraph("KES 60,900.00", styles["TableCell"]), Paragraph("KES 121,800.00", styles["TableCellBold"])],
        [Paragraph("<b>Total Monthly Contribution</b>", styles["TableCellBold"]), Paragraph("-", styles["TableCell"]), Paragraph("<b>KES 75,600.00</b>", styles["TableCellBold"]), Paragraph("<b>KES 75,600.00</b>", styles["TableCellBold"]), Paragraph("<font color='#16A34A'><b>KES 151,200.00</b></font>", styles["TableCellBold"])],
    ]
    ht = Table(heads_data, colWidths=[150, 130, 80, 80, 80])
    ht.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, bg_light]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E2E8F0")),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(ht)
    elements.append(Spacer(1, 14))

    cert_text = (
        "<b>STATUTORY CLEARANCE CERTIFICATE:</b> The National Social Security Fund confirms that the employer "
        "has submitted the monthly member returns and settled total pension contributions for all registered employees "
        "before the 9th statutory deadline. No penalties or default interests are accrued."
    )
    elements.append(Paragraph(cert_text, styles["Body"]))
    elements.append(Spacer(1, 18))

    sig_data = [
        [
            Paragraph("<b>MANAGING TRUSTEE, NSSF KENYA</b><br/><br/><i>[Electronic Pension Stamp]</i><br/>NSSF Electronic Contributions Bureau<br/>NSSF Building, Bishops Road, Nairobi", styles["Body"]),
            Paragraph("<b>CENTRAL BANK SETTLEMENT SEAL</b><br/><br/>PRN Verification Code: NSSF-SETTL-049<br/>Cleared via CBK Switch", styles["SealText"]),
        ]
    ]
    st = Table(sig_data, colWidths=[270, 250])
    st.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(st)

    return _build_doc(elements, watermark_text="NSSF STATUTORY PENSION • VERIFIED")


def generate_shif_remittance_schedule(org_name: str, employee_count: int = 35) -> bytes:
    """Generates authentic Social Health Authority (SHA/SHIF) Statutory Contribution Schedule."""
    styles = _get_base_styles()
    primary = colors.HexColor("#172B4D")
    sha_green = colors.HexColor("#0D9488")
    border_col = colors.HexColor("#E2E8F0")
    bg_light = colors.HexColor("#F8FAFC")

    elements = [
        Spacer(1, 10),
        Paragraph("REPUBLIC OF KENYA", styles["DocTitle"]),
        Paragraph("SOCIAL HEALTH AUTHORITY (SHA)", ParagraphStyle("SHA", parent=styles["AgencyHeader"], textColor=sha_green)),
        Paragraph("SOCIAL HEALTH INSURANCE FUND (SHIF) STATUTORY REMITTANCE ACKNOWLEDGMENT", styles["DocSubTitle"]),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=2, color=sha_green, spaceBefore=2, spaceAfter=10),
        Paragraph("STATUTORY EMPLOYER HEALTH INSURANCE REMITTANCE SCHEDULE", styles["CertHeading"]),
        Paragraph("<i>Compliant with Section 27 of the Social Health Insurance Act, No. 16 of 2023</i>", styles["NoticeText"]),
        Spacer(1, 14),
    ]

    sha_meta = [
        [Paragraph("<b>SHA Employer Number:</b>", styles["Body"]), Paragraph("<b>SHA-ER-2024-91024</b>", styles["BodyBold"]), Paragraph("<b>Payment Date:</b>", styles["Body"]), Paragraph("08 November 2026", styles["Body"])],
        [Paragraph("<b>Employer Name:</b>", styles["Body"]), Paragraph(f"<b>{org_name}</b>", styles["BodyBold"]), Paragraph("<b>Statutory Due Date:</b>", styles["Body"]), Paragraph("<b>09 November 2026</b>", styles["BodyBold"])],
        [Paragraph("<b>Contribution Period:</b>", styles["Body"]), Paragraph("October 2026", styles["Body"]), Paragraph("<b>Covered Workers:</b>", styles["Body"]), Paragraph(f"<b>{employee_count} Employees</b>", styles["BodyBold"])],
        [Paragraph("<b>Remittance Status:</b>", styles["Body"]), Paragraph("<font color='#16A34A'><b>REMITTED & ACTIVE</b></font>", styles["BodyBold"]), Paragraph("<b>SHA e-Receipt:</b>", styles["Body"]), Paragraph("SHA-REC-2026-88102", styles["BodyBold"])],
    ]
    t = Table(sha_meta, colWidths=[130, 160, 110, 120])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>SHIF Healthcare Contribution Breakdown (2.75% Statutory Rate)</b>", styles["SectionHeader"]))
    heads_data = [
        [Paragraph("Health Scheme Head", styles["TableHead"]), Paragraph("Statutory Basis", styles["TableHead"]), Paragraph("Eligible Gross Wage", styles["TableHead"]), Paragraph("Contribution Remitted", styles["TableHead"])],
        [Paragraph("Primary Healthcare Fund", styles["TableCellBold"]), Paragraph("Universal Access Fund", styles["TableCell"]), Paragraph("Government Subsidized", styles["TableCell"]), Paragraph("Fully Enrolled", styles["TableCell"])],
        [Paragraph("Social Health Insurance Fund (SHIF)", styles["TableCellBold"]), Paragraph("2.75% Gross Household Income", styles["TableCell"]), Paragraph("KES 2,450,000.00", styles["TableCell"]), Paragraph("<font color='#16A34A'><b>KES 67,375.00</b></font>", styles["TableCellBold"])],
        [Paragraph("Emergency & Chronic Illness Fund", styles["TableCellBold"]), Paragraph("Sec 28 SHI Act 2023", styles["TableCell"]), Paragraph("Pool Coverage Mandate", styles["TableCell"]), Paragraph("Active & Maintained", styles["TableCell"])],
        [Paragraph("<b>Total Monthly SHA Remittance</b>", styles["TableCellBold"]), Paragraph("-", styles["TableCell"]), Paragraph("-", styles["TableCell"]), Paragraph("<b>KES 67,375.00</b>", styles["TableCellBold"])],
    ]
    ht = Table(heads_data, colWidths=[160, 130, 110, 120])
    ht.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, bg_light]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E2E8F0")),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(ht)
    elements.append(Spacer(1, 14))

    cert_text = (
        "<b>HEALTH AUTHORITY CLEARANCE:</b> The Social Health Authority confirms receipt of statutory employee deductions. "
        "All workers listed on the employer's schedule are active on the National Health Benefits Scheme with full healthcare "
        "access rights across registered Kenyan health facilities."
    )
    elements.append(Paragraph(cert_text, styles["Body"]))
    elements.append(Spacer(1, 18))

    sig_data = [
        [
            Paragraph("<b>CHIEF EXECUTIVE OFFICER, SHA</b><br/><br/><i>[Digital Authorization]</i><br/>Social Health Authority Kenya<br/>NHIF Building, Ragati Road, Nairobi", styles["Body"]),
            Paragraph("<b>SHA REVENUE COLLECTION DESK</b><br/><br/>Electronic Remittance Reconciliation<br/>SHA National Database Validated", styles["SealText"]),
        ]
    ]
    st = Table(sig_data, colWidths=[270, 250])
    st.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(st)

    return _build_doc(elements, watermark_text="SHA SHIF HEALTHCARE • VERIFIED")


def generate_fire_safety_audit_cert(org_name: str, county: str = "Nairobi") -> bytes:
    """Generates authentic Workplace Fire Risk Reduction & Safety Inspection Certificate."""
    styles = _get_base_styles()
    primary = colors.HexColor("#172B4D")
    border_col = colors.HexColor("#E2E8F0")
    bg_light = colors.HexColor("#F8FAFC")

    elements = [
        Spacer(1, 10),
        Paragraph("REPUBLIC OF KENYA", styles["DocTitle"]),
        Paragraph("COUNTY GOVERNMENT OCCUPATIONAL SAFETY & FIRE RESCUE SERVICES", styles["AgencyHeader"]),
        Paragraph(f"COUNTY OF {county.upper()} - DISASTER MANAGEMENT & FIRE BRIGADE", styles["DocSubTitle"]),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#EA580C"), spaceBefore=2, spaceAfter=10),
        Paragraph("ANNUAL WORKPLACE FIRE SAFETY & RISK REDUCTION CERTIFICATE", styles["CertHeading"]),
        Paragraph("<i>Issued Pursuant to Factories and Other Places of Work (Fire Risk Reduction) Rules, 2007 (LN 59/2007)</i>", styles["NoticeText"]),
        Spacer(1, 14),
    ]

    fire_meta = [
        [Paragraph("<b>Fire Safety Cert No:</b>", styles["Body"]), Paragraph("<b>FIRE-CERT-2026-4401</b>", styles["BodyBold"]), Paragraph("<b>Audit Date:</b>", styles["Body"]), Paragraph("14 October 2025", styles["Body"])],
        [Paragraph("<b>Premises Name:</b>", styles["Body"]), Paragraph(f"<b>{org_name}</b>", styles["BodyBold"]), Paragraph("<b>Expiry Date:</b>", styles["Body"]), Paragraph("<b>13 October 2026</b>", styles["BodyBold"])],
        [Paragraph("<b>Inspected Location:</b>", styles["Body"]), Paragraph(f"Commercial Facility, {county}", styles["Body"]), Paragraph("<b>Fire Safety Grade:</b>", styles["Body"]), Paragraph("<font color='#16A34A'><b>GRADE A (COMPLIANT)</b></font>", styles["BodyBold"])],
        [Paragraph("<b>Lead Fire Safety Officer:</b>", styles["Body"]), Paragraph("Insp. Kenneth Gitonga (DOSHS/F/102)", styles["Body"]), Paragraph("<b>Evacuation Drill:</b>", styles["Body"]), Paragraph("Conducted 02 Oct 2025 (2m 15s)", styles["Body"])],
    ]
    t = Table(fire_meta, colWidths=[130, 160, 110, 120])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>Statutory Fire Protection Assessment Matrix (Legal Notice 59/2007)</b>", styles["SectionHeader"]))
    heads_data = [
        [Paragraph("Safety Checklist Item", styles["TableHead"]), Paragraph("Statutory Legal Rule", styles["TableHead"]), Paragraph("Inspection Assessment", styles["TableHead"])],
        [Paragraph("Fire Detection & Alarm System", styles["TableCellBold"]), Paragraph("Rule 14 Fire Rules 2007", styles["TableCell"]), Paragraph("<font color='#16A34A'><b>PASSED:</b></font> Smoke detectors functional, manual call points operational.", styles["TableCell"])],
        [Paragraph("Portable Fire Extinguishers", styles["TableCellBold"]), Paragraph("Rule 22 Fire Rules 2007", styles["TableCell"]), Paragraph("<font color='#16A34A'><b>PASSED:</b></font> CO2 & Dry Powder units inspected & serviced within 12 months.", styles["TableCell"])],
        [Paragraph("Emergency Exits & Clear Routes", styles["TableCellBold"]), Paragraph("Rule 17 Fire Rules 2007", styles["TableCell"]), Paragraph("<font color='#16A34A'><b>PASSED:</b></font> Unobstructed panic-exit doors and luminescent signage.", styles["TableCell"])],
        [Paragraph("Workplace Fire Safety Team", styles["TableCellBold"]), Paragraph("Rule 20 Fire Rules 2007", styles["TableCell"]), Paragraph("<font color='#16A34A'><b>PASSED:</b></font> 8 Fire Marshals formally trained by Kenya Red Cross.", styles["TableCell"])],
        [Paragraph("Hazardous Flammables Storage", styles["TableCellBold"]), Paragraph("Rule 27 Fire Rules 2007", styles["TableCell"]), Paragraph("<font color='#16A34A'><b>PASSED:</b></font> Segregated, ventilated store with bunding and hazard placards.", styles["TableCell"])],
    ]
    ht = Table(heads_data, colWidths=[160, 140, 220])
    ht.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(ht)
    elements.append(Spacer(1, 14))

    cert_text = (
        "<b>OFFICIAL FIRE CLEARANCE CERTIFICATION:</b> Having carried out a thorough statutory fire audit under "
        "Rule 34 of the Fire Risk Reduction Rules 2007, the premises are certified to possess adequate fire fighting "
        "appliances and sufficient means of escape in case of fire."
    )
    elements.append(Paragraph(cert_text, styles["Body"]))
    elements.append(Spacer(1, 18))

    sig_data = [
        [
            Paragraph("<b>COUNTY CHIEF FIRE OFFICER</b><br/><br/><i>[Official County Seal]</i><br/><b>Chief Fire Marshal, County Services</b><br/>Fire & Disaster Management Bureau", styles["Body"]),
            Paragraph("<b>DOSHS CERTIFIED AUDIT AUTHORITY</b><br/><br/>Workplace Fire Safety Inspectorate<br/>ISO 9001:2015 Accredited", styles["SealText"]),
        ]
    ]
    st = Table(sig_data, colWidths=[270, 250])
    st.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(st)

    return _build_doc(elements, watermark_text="FIRE SAFETY AUDIT • VERIFIED CERTIFICATE")


def generate_standard_employment_contract(org_name: str) -> bytes:
    """Generates authentic Standard Kenyan Employment Contract & HR Terms."""
    styles = _get_base_styles()
    primary = colors.HexColor("#172B4D")
    border_col = colors.HexColor("#E2E8F0")
    bg_light = colors.HexColor("#F8FAFC")

    elements = [
        Spacer(1, 10),
        Paragraph("STATUTORY EMPLOYMENT AGREEMENT", styles["DocTitle"]),
        Paragraph("STANDARD TERMS OF SERVICE & EMPLOYMENT CONTRACT", styles["AgencyHeader"]),
        Paragraph("<i>Formulated in Full Compliance with Section 9 & 10 of the Employment Act, No. 11 of 2007</i>", styles["NoticeText"]),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=2, color=primary, spaceBefore=2, spaceAfter=10),
        Paragraph(f"{org_name.upper()} • EMPLOYMENT CONTRACT SCHEDULE", styles["CertHeading"]),
        Spacer(1, 14),
    ]

    emp_meta = [
        [Paragraph("<b>Contract Form No:</b>", styles["Body"]), Paragraph("<b>EMP-STD-2026-KEN</b>", styles["BodyBold"]), Paragraph("<b>Governing Law:</b>", styles["Body"]), Paragraph("Employment Act 2007 (Kenya)", styles["Body"])],
        [Paragraph("<b>Employing Enterprise:</b>", styles["Body"]), Paragraph(f"<b>{org_name}</b>", styles["BodyBold"]), Paragraph("<b>Jurisdiction:</b>", styles["Body"]), Paragraph("Industrial & Labour Relations Court", styles["Body"])],
        [Paragraph("<b>Statutory Working Hours:</b>", styles["Body"]), Paragraph("45 Hours/Week (Max Sec 27)", styles["Body"]), Paragraph("<b>Annual Leave:</b>", styles["Body"]), Paragraph("<b>21 Working Days (Sec 28)</b>", styles["BodyBold"])],
        [Paragraph("<b>Maternity / Paternity:</b>", styles["Body"]), Paragraph("3 Months / 2 Weeks (Sec 29)", styles["Body"]), Paragraph("<b>Probation Limit:</b>", styles["Body"]), Paragraph("Up to 6 Months (Sec 42)", styles["Body"])],
    ]
    t = Table(emp_meta, colWidths=[130, 160, 110, 120])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>Statutory Employment Terms Schedule (Employment Act 2007)</b>", styles["SectionHeader"]))
    terms_data = [
        [Paragraph("Statutory Term Area", styles["TableHead"]), Paragraph("Statutory Legal Section", styles["TableHead"]), Paragraph("Mandatory Standard Policy", styles["TableHead"])],
        [Paragraph("Itemized Monthly Payslips", styles["TableCellBold"]), Paragraph("Sec 20 Employment Act", styles["TableCell"]), Paragraph("Written pay statement detailing basic salary, allowances, and PAYE/NSSF/SHIF deductions.", styles["TableCell"])],
        [Paragraph("Paid Sick Leave Entitlement", styles["TableCellBold"]), Paragraph("Sec 30 Employment Act", styles["TableCell"]), Paragraph("Full pay for 7 days followed by half pay for 7 days upon medical certification.", styles["TableCell"])],
        [Paragraph("Fair Disciplinary Procedure", styles["TableCellBold"]), Paragraph("Sec 41 Employment Act", styles["TableCell"]), Paragraph("Written notice of charges, fair hearing in presence of chosen colleague, and appeal.", styles["TableCell"])],
        [Paragraph("Severance & Redundancy Pay", styles["TableCellBold"]), Paragraph("Sec 40 Employment Act", styles["TableCell"]), Paragraph("Not less than 15 days basic wages for each completed year of service.", styles["TableCell"])],
        [Paragraph("Prohibition of Harassment", styles["TableCellBold"]), Paragraph("Sec 6 Employment Act", styles["TableCell"]), Paragraph("Strict zero-tolerance policy against sexual harassment and discrimination.", styles["TableCell"])],
    ]
    tt = Table(terms_data, colWidths=[150, 140, 230])
    tt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_col),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(tt)
    elements.append(Spacer(1, 14))

    cert_text = (
        "<b>EMPLOYER COMPLIANCE DECLARATION:</b> The employer warrants that all personnel employed within the enterprise "
        "execute written contracts of service embodying these minimum statutory conditions in accordance with "
        "the Employment Act 2007 and General Wages Orders."
    )
    elements.append(Paragraph(cert_text, styles["Body"]))
    elements.append(Spacer(1, 18))

    sig_data = [
        [
            Paragraph("<b>FOR: THE EMPLOYER</b><br/><br/><i>[Authorized Signature]</i><br/>Head of Human Resources<br/>Registered Employer", styles["Body"]),
            Paragraph("<b>MINISTRY OF LABOUR COMPLIANCE</b><br/><br/>Standard Contract Schedule<br/>Republic of Kenya", styles["SealText"]),
        ]
    ]
    st = Table(sig_data, colWidths=[270, 250])
    st.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, border_col),
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(st)

    return _build_doc(elements, watermark_text="EMPLOYMENT CONTRACT • STATUTORY TERMS")


def build_complete_statutory_evidence_vault(base_export_dir: Path, zip_dest_path: Path):
    """
    Builds the complete categorized folder structure with all watermarked statutory evidence documents
    and creates a ready-to-download ZIP archive.
    """
    base_export_dir.mkdir(parents=True, exist_ok=True)
    zip_dest_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Folder Definitions matching descriptions
    folders = {
        "01_Data_Protection_Compliance_ODPC": [
            ("ODPC_Data_Controller_Registration_Cert_Apex_Logistics.pdf", lambda: generate_odpc_registration_cert("Apex Logistics Solutions Ltd", "P051992233M")),
            ("ODPC_Data_Controller_Registration_Cert_Kilimani_Health.pdf", lambda: generate_odpc_registration_cert("Kilimani Healthcare Centre Ltd", "P051883344K")),
            ("ODPC_Data_Controller_Registration_Cert_Rift_Valley_Produce.pdf", lambda: generate_odpc_registration_cert("Rift Valley Fresh Produce Ltd", "P051774455R")),
            ("ODPC_Data_Controller_Registration_Cert_Savanna_Retail.pdf", lambda: generate_odpc_registration_cert("Savanna Retail Enterprises Ltd", "P051665566S")),
            ("Statutory_Data_Protection_Policy_and_Privacy_Notice.pdf", lambda: generate_data_protection_policy("Apex Logistics Solutions Ltd")),
            ("Data_Protection_Officer_DPO_Designation_Charter.pdf", lambda: generate_dpo_appointment_letter("Apex Logistics Solutions Ltd")),
        ],
        "02_Tax_Compliance_KRA": [
            ("KRA_Tax_Compliance_Certificate_TCC_Apex_Logistics.pdf", lambda: generate_kra_tax_compliance_cert("Apex Logistics Solutions Ltd", "P051992233M")),
            ("KRA_Tax_Compliance_Certificate_TCC_Kilimani_Health.pdf", lambda: generate_kra_tax_compliance_cert("Kilimani Healthcare Centre Ltd", "P051883344K")),
            ("KRA_Tax_Compliance_Certificate_TCC_Rift_Valley_Produce.pdf", lambda: generate_kra_tax_compliance_cert("Rift Valley Fresh Produce Ltd", "P051774455R")),
            ("KRA_Tax_Compliance_Certificate_TCC_Savanna_Retail.pdf", lambda: generate_kra_tax_compliance_cert("Savanna Retail Enterprises Ltd", "P051665566S")),
            ("KRA_eTIMS_Electronic_Fiscal_Device_Integration_Signoff.pdf", lambda: generate_etims_signoff_cert("Apex Logistics Solutions Ltd", "P051992233M")),
            ("Monthly_PAYE_Return_and_PRN_Remittance_Receipt.pdf", lambda: generate_paye_remittance_receipt("Apex Logistics Solutions Ltd", "P051992233M")),
            ("Monthly_VAT_Return_and_Payment_Acknowledgment.pdf", lambda: generate_vat_return_acknowledgment("Apex Logistics Solutions Ltd", "P051992233M")),
            ("Annual_Corporate_Income_Tax_Return_IT2C_and_Audited_Accounts.pdf", lambda: generate_corporate_tax_return("Apex Logistics Solutions Ltd", "P051992233M")),
        ],
        "03_Employment_and_Labour_Compliance": [
            ("WIBA_Workplace_Injury_Benefits_Statutory_Insurance_Policy.pdf", lambda: generate_wiba_policy_schedule("Apex Logistics Solutions Ltd", 35)),
            ("DOSHS_Workplace_Occupational_Safety_and_Health_Inspection_Audit.pdf", lambda: generate_osha_inspection_report("Apex Logistics Solutions Ltd", "Nairobi")),
            ("NSSF_Tier_I_and_Tier_II_Statutory_Pension_PRN_Receipt.pdf", lambda: generate_nssf_remittance_schedule("Apex Logistics Solutions Ltd", 35)),
            ("SHIF_Social_Health_Insurance_Fund_Remittance_Schedule.pdf", lambda: generate_shif_remittance_schedule("Apex Logistics Solutions Ltd", 35)),
            ("Workplace_Fire_Safety_Audit_and_Evacuation_Drill_Certificate.pdf", lambda: generate_fire_safety_audit_cert("Apex Logistics Solutions Ltd", "Nairobi")),
            ("Standard_Employment_Contract_and_HR_Manual.pdf", lambda: generate_standard_employment_contract("Apex Logistics Solutions Ltd")),
        ],
        "04_Evidence_By_Company/Apex_Logistics_Solutions_Ltd": [
            ("01_ODPC_Data_Controller_Registration_Cert.pdf", lambda: generate_odpc_registration_cert("Apex Logistics Solutions Ltd", "P051992233M")),
            ("02_KRA_Tax_Compliance_Certificate_2026.pdf", lambda: generate_kra_tax_compliance_cert("Apex Logistics Solutions Ltd", "P051992233M")),
            ("03_eTIMS_System_Integration_Signoff.pdf", lambda: generate_etims_signoff_cert("Apex Logistics Solutions Ltd", "P051992233M")),
            ("04_WIBA_Workplace_Injury_Insurance_Policy.pdf", lambda: generate_wiba_policy_schedule("Apex Logistics Solutions Ltd", 35)),
            ("05_DOSHS_Occupational_Safety_Inspection_Report.pdf", lambda: generate_osha_inspection_report("Apex Logistics Solutions Ltd", "Nairobi")),
        ],
        "04_Evidence_By_Company/Kilimani_Healthcare_Centre_Ltd": [
            ("01_ODPC_Data_Controller_Registration_Cert.pdf", lambda: generate_odpc_registration_cert("Kilimani Healthcare Centre Ltd", "P051883344K")),
            ("02_KRA_Tax_Compliance_Certificate_2026.pdf", lambda: generate_kra_tax_compliance_cert("Kilimani Healthcare Centre Ltd", "P051883344K")),
            ("03_eTIMS_System_Integration_Signoff.pdf", lambda: generate_etims_signoff_cert("Kilimani Healthcare Centre Ltd", "P051883344K")),
            ("04_WIBA_Workplace_Injury_Insurance_Policy.pdf", lambda: generate_wiba_policy_schedule("Kilimani Healthcare Centre Ltd", 48)),
            ("05_DOSHS_Occupational_Safety_Inspection_Report.pdf", lambda: generate_osha_inspection_report("Kilimani Healthcare Centre Ltd", "Nairobi")),
        ],
        "04_Evidence_By_Company/Rift_Valley_Fresh_Produce_Ltd": [
            ("01_ODPC_Data_Controller_Registration_Cert.pdf", lambda: generate_odpc_registration_cert("Rift Valley Fresh Produce Ltd", "P051774455R")),
            ("02_KRA_Tax_Compliance_Certificate_2026.pdf", lambda: generate_kra_tax_compliance_cert("Rift Valley Fresh Produce Ltd", "P051774455R")),
            ("03_eTIMS_System_Integration_Signoff.pdf", lambda: generate_etims_signoff_cert("Rift Valley Fresh Produce Ltd", "P051774455R")),
            ("04_WIBA_Workplace_Injury_Insurance_Policy.pdf", lambda: generate_wiba_policy_schedule("Rift Valley Fresh Produce Ltd", 85)),
            ("05_DOSHS_Occupational_Safety_Inspection_Report.pdf", lambda: generate_osha_inspection_report("Rift Valley Fresh Produce Ltd", "Nakuru")),
        ],
        "04_Evidence_By_Company/Savanna_Retail_Enterprises_Ltd": [
            ("01_ODPC_Data_Controller_Registration_Cert.pdf", lambda: generate_odpc_registration_cert("Savanna Retail Enterprises Ltd", "P051665566S")),
            ("02_KRA_Tax_Compliance_Certificate_2026.pdf", lambda: generate_kra_tax_compliance_cert("Savanna Retail Enterprises Ltd", "P051665566S")),
            ("03_eTIMS_System_Integration_Signoff.pdf", lambda: generate_etims_signoff_cert("Savanna Retail Enterprises Ltd", "P051665566S")),
            ("04_WIBA_Workplace_Injury_Insurance_Policy.pdf", lambda: generate_wiba_policy_schedule("Savanna Retail Enterprises Ltd", 24)),
            ("05_DOSHS_Occupational_Safety_Inspection_Report.pdf", lambda: generate_osha_inspection_report("Savanna Retail Enterprises Ltd", "Mombasa")),
        ],
    }

    # Generate documents into folder structure
    total_docs = 0
    for rel_folder, file_list in folders.items():
        folder_path = base_export_dir / rel_folder
        folder_path.mkdir(parents=True, exist_ok=True)
        for fname, gen_fn in file_list:
            fpath = folder_path / fname
            pdf_bytes = gen_fn()
            fpath.write_bytes(pdf_bytes)
            total_docs += 1

    # Create ZIP archive
    with zipfile.ZipFile(str(zip_dest_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(str(base_export_dir)):
            for file in files:
                full_fpath = Path(root) / file
                archive_name = full_fpath.relative_to(base_export_dir)
                zf.write(str(full_fpath), str(archive_name))

    return total_docs, zip_dest_path
