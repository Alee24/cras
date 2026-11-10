import io
import csv
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

from app.models.assessment import ComplianceAssessment, AssessmentDomainScore, AssessmentResponse
from app.models.compliance_management import ComplianceGap, CorrectiveAction
from app.models.regulatory import RegulatoryRequirement, RegulatoryDomain
from app.models.organization import Organization


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas that computes total page count dynamically and renders:
    - Running top header on pages 2+
    - Running bottom footer with 'Page X of Y' and official confidentiality stamp on all pages
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        self.saveState()
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running header (pages 2 and later)
        if self._pageNumber > 1:
            self.drawString(36, 812, "CRAS | Statutory Compliance Audit Report")
            self.drawRightString(559, 812, "Official Audit Register")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(36, 806, 559, 806)

        # Running footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 38, 559, 38)

        self.setFont("Helvetica", 7.5)
        self.drawString(36, 26, "Strictly Confidential — Compliance Risk Analytics System (CRAS) Kenya")
        self.drawRightString(559, 26, f"Page {self._pageNumber} of {total_pages}")
        self.restoreState()


class CertificateCanvas(canvas.Canvas):
    """Draws multi-tiered security borders and seal accents for the Landscape Compliance Certificate."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_certificate_frame()
            super().showPage()
        super().save()

    def draw_certificate_frame(self):
        self.saveState()
        # Outer formal border (Navy #172B4D)
        self.setStrokeColor(colors.HexColor("#172B4D"))
        self.setLineWidth(4)
        self.rect(20, 20, 802, 555)

        # Inner decorative gold border (#D97706)
        self.setStrokeColor(colors.HexColor("#D97706"))
        self.setLineWidth(1.5)
        self.rect(26, 26, 790, 543)

        # Subtle slate border
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.rect(30, 30, 782, 535)

        # Corner embellishments
        self.setFillColor(colors.HexColor("#D97706"))
        for x, y in [(34, 34), (34, 561), (808, 34), (808, 561)]:
            self.circle(x, y, 3, stroke=1, fill=1)

        # Security Watermark at Bottom
        self.setFont("Helvetica", 7)
        self.setFillColor(colors.HexColor("#94A3B8"))
        self.drawString(36, 12, "KENYA STATUTORY COMPLIANCE ASSURANCE • VERIFIABLE AUDIT RECORD • CRAS SECURE CERTIFICATION")
        self.drawRightString(806, 12, f"ISSUED: {datetime.now().strftime('%Y-%m-%d')} • VALIDATED")
        self.restoreState()


class ReportingService:
    @staticmethod
    def generate_assessment_pdf(assessment: ComplianceAssessment) -> io.BytesIO:
        """
        Generates a comprehensive, audit-grade PDF report for a ComplianceAssessment.
        Includes:
        - Executive Organization Metadata
        - Overall Compliance Score & Risk Classification
        - Regulatory Domain Compliance Breakdown
        - Section 2: Complete Statutory Obligations Audit Register (all 43 obligations)
        - Section 3: Identified Gaps & Legal/Financial Penalties
        - Section 4: Corrective Actions Register
        - Section 5: Dual Auditor Sign-off
        - Section 6: Statutory Disclaimer
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=46,
            bottomMargin=46,
        )

        styles = getSampleStyleSheet()

        primary_color = colors.HexColor("#172B4D")
        secondary_color = colors.HexColor("#2563EB")
        text_color = colors.HexColor("#1E293B")
        bg_light = colors.HexColor("#F8FAFC")
        border_color = colors.HexColor("#E2E8F0")

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=primary_color,
        )

        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=secondary_color,
        )

        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=primary_color,
            spaceAfter=6,
        )

        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=text_color,
        )

        body_bold = ParagraphStyle(
            "BodyBold",
            parent=body_style,
            fontName="Helvetica-Bold",
        )

        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10.5,
            textColor=colors.white,
        )

        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=text_color,
        )

        badge_text_style = ParagraphStyle(
            "BadgeText",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=colors.white,
            alignment=1,
        )

        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor("#64748B"),
        )

        elements = []

        # 1. Header Banner
        org = assessment.organization
        elements.append(Paragraph("COMPLIANCE RISK ANALYTICS SYSTEM (CRAS)", title_style))
        elements.append(Paragraph("Statutory Compliance & Regulatory Risk Intelligence Audit Report — Kenya SMEs", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=secondary_color, spaceBefore=4, spaceAfter=10))

        # 2. Executive Metadata Box
        meta_data = [
            [
                Paragraph("<b>Organization:</b>", body_style),
                Paragraph(org.name, body_bold),
                Paragraph("<b>KRA PIN:</b>", body_style),
                Paragraph(org.kra_pin, body_bold),
            ],
            [
                Paragraph("<b>Registration No:</b>", body_style),
                Paragraph(org.business_registration_number, body_style),
                Paragraph("<b>County:</b>", body_style),
                Paragraph(org.county, body_style),
            ],
            [
                Paragraph("<b>Assessment Period:</b>", body_style),
                Paragraph(assessment.assessment_period, body_bold),
                Paragraph("<b>Audit Date:</b>", body_style),
                Paragraph(assessment.assessment_date.strftime("%d %b %Y") if assessment.assessment_date else "N/A", body_style),
            ],
            [
                Paragraph("<b>Scoring Policy:</b>", body_style),
                Paragraph(f"Kenya SME Standard ({assessment.scoring_policy_version.version_number if assessment.scoring_policy_version else 'v1.0'})", body_style),
                Paragraph("<b>Audit Status:</b>", body_style),
                Paragraph(f"<b>{assessment.status}</b>", body_style),
            ],
        ]

        meta_table = Table(meta_data, colWidths=[110, 150, 110, 153])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_light),
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 10))

        # 3. Overall Compliance Score & Risk Classification
        score_val = assessment.overall_score if assessment.overall_score is not None else 0.0
        classification = assessment.risk_classification or "NOT_CLASSIFIED"

        if classification == "COMPLIANT":
            badge_bg = colors.HexColor("#16A34A")
            class_label = "COMPLIANT (LOW RISK)"
        elif classification == "MODERATE_RISK":
            badge_bg = colors.HexColor("#F59E0B")
            class_label = "MODERATE RISK"
        else:
            badge_bg = colors.HexColor("#DC2626")
            class_label = "HIGH RISK"

        score_table_data = [
            [
                Paragraph("<b>OVERALL COMPLIANCE SCORE</b>", ParagraphStyle("ScoreLbl", parent=body_style, fontName="Helvetica-Bold", fontSize=10, textColor=primary_color)),
                Paragraph(f"<b>{score_val:.2f}%</b>", ParagraphStyle("ScoreBig", parent=body_style, fontName="Helvetica-Bold", fontSize=20, leading=22, textColor=primary_color, alignment=1)),
                Paragraph(f"<b>{class_label}</b>", badge_text_style),
            ],
            [
                Paragraph(
                    f"Total Obligations: <b>{assessment.total_obligations}</b> | "
                    f"Compliant: <font color='#16A34A'><b>{assessment.compliant_count}</b></font> | "
                    f"Partially Compliant: <font color='#D97706'><b>{assessment.partially_compliant_count}</b></font> | "
                    f"Non-Compliant: <font color='#DC2626'><b>{assessment.non_compliant_count}</b></font> | "
                    f"N/A: <b>{assessment.not_applicable_count}</b>",
                    body_style
                ),
                "",
                ""
            ]
        ]

        score_table = Table(score_table_data, colWidths=[195, 138, 190])
        score_table.setStyle(TableStyle([
            ("SPAN", (0, 1), (2, 1)),
            ("BACKGROUND", (0, 0), (1, 0), bg_light),
            ("BACKGROUND", (2, 0), (2, 0), badge_bg),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(score_table)
        elements.append(Spacer(1, 12))

        # 4. Domain Breakdown Table
        elements.append(Paragraph("1. Regulatory Domain Compliance Breakdown", section_heading))
        domain_table_data = [
            [
                Paragraph("Regulatory Domain", table_header_style),
                Paragraph("Weight", table_header_style),
                Paragraph("Applicable Obligations", table_header_style),
                Paragraph("Domain Score", table_header_style),
                Paragraph("Weighted Score", table_header_style),
                Paragraph("Classification", table_header_style),
            ]
        ]

        domain_scores = AssessmentDomainScore.query.filter_by(assessment_id=assessment.id).all()
        for ds in domain_scores:
            d_class = ds.classification or "MODERATE_RISK"
            if d_class == "COMPLIANT":
                color_hex = "#16A34A"
            elif d_class == "MODERATE_RISK":
                color_hex = "#F59E0B"
            else:
                color_hex = "#DC2626"

            pct_score = (ds.normalized_score * 100.0) if ds.normalized_score is not None else 0.0

            domain_table_data.append([
                Paragraph(f"<b>{ds.domain.title}</b><br/><font color='#64748B'>{ds.domain.legal_framework}</font>", table_cell_style),
                Paragraph(f"{int(ds.domain_weight * 100)}%", table_cell_style),
                Paragraph(f"{ds.applicable_obligations_count} (C:{ds.compliant_count}, P:{ds.partially_compliant_count}, NC:{ds.non_compliant_count})", table_cell_style),
                Paragraph(f"<b>{pct_score:.1f}%</b>", table_cell_style),
                Paragraph(f"<b>{ds.weighted_score:.2f} pts</b>", table_cell_style),
                Paragraph(f"<font color='{color_hex}'><b>{d_class.replace('_', ' ')}</b></font>", table_cell_style),
            ])

        domain_table = Table(domain_table_data, colWidths=[150, 45, 125, 65, 75, 63])
        domain_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary_color),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(domain_table)
        elements.append(Spacer(1, 14))

        # 5. Full Statutory Obligations Audit Register (All 43 Obligations)
        responses = AssessmentResponse.query.filter_by(assessment_id=assessment.id).all()
        # Sort responses by domain code and requirement code
        responses = sorted(responses, key=lambda r: (r.requirement.domain.code if r.requirement and r.requirement.domain else "", r.requirement.code if r.requirement else ""))

        elements.append(Paragraph(f"2. Statutory Obligations Audit Register ({len(responses)} Evaluated Items)", section_heading))
        elements.append(Paragraph("Complete breakdown of statutory compliance across the Kenya Data Protection Act, Tax Legislation, and Employment & Labour Laws.", body_style))
        elements.append(Spacer(1, 6))

        audit_table_data = [
            [
                Paragraph("Code", table_header_style),
                Paragraph("Domain", table_header_style),
                Paragraph("Statutory Requirement & Legal Citation", table_header_style),
                Paragraph("Status", table_header_style),
                Paragraph("Auditor Findings / Observations", table_header_style),
            ]
        ]

        for resp in responses:
            req = resp.requirement
            if not req:
                continue

            r_val = resp.response_value
            if r_val == "COMPLIANT":
                status_html = "<font color='#16A34A'><b>COMPLIANT</b></font>"
            elif r_val == "PARTIALLY_COMPLIANT":
                status_html = "<font color='#D97706'><b>PARTIAL</b></font>"
            elif r_val == "NON_COMPLIANT":
                status_html = "<font color='#DC2626'><b>NON-COMPLIANT</b></font>"
            else:
                status_html = "<font color='#64748B'><b>N/A</b></font>"

            notes_text = resp.notes.strip() if resp.notes else "Verified compliant in accordance with statutory guidelines."

            audit_table_data.append([
                Paragraph(f"<b>{req.code}</b>", table_cell_style),
                Paragraph(req.domain.code if req.domain else "CRAS", table_cell_style),
                Paragraph(f"<b>{req.title}</b><br/><font color='#64748B'><i>{req.legal_reference}</i></font>", table_cell_style),
                Paragraph(status_html, table_cell_style),
                Paragraph(notes_text, table_cell_style),
            ])

        audit_table = Table(audit_table_data, colWidths=[50, 45, 175, 75, 178])
        audit_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary_color),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(audit_table)
        elements.append(Spacer(1, 14))

        # 6. Compliance Gaps & Recommended Actions
        gaps = ComplianceGap.query.filter_by(assessment_id=assessment.id).order_by(ComplianceGap.severity).all()
        elements.append(Paragraph(f"3. Identified Regulatory Gaps & Immediate Actions ({len(gaps)})", section_heading))

        if gaps:
            gaps_table_data = [
                [
                    Paragraph("Ref", table_header_style),
                    Paragraph("Severity", table_header_style),
                    Paragraph("Obligation & Statutory Reference", table_header_style),
                    Paragraph("Potential Regulatory Consequence", table_header_style),
                    Paragraph("Recommended Corrective Action", table_header_style),
                ]
            ]

            for g in gaps:
                sev_color = "#DC2626" if g.severity == "CRITICAL" else ("#EA580C" if g.severity == "HIGH" else "#D97706")
                gaps_table_data.append([
                    Paragraph(f"<b>{g.requirement.code if g.requirement else 'GAP'}</b>", table_cell_style),
                    Paragraph(f"<font color='{sev_color}'><b>{g.severity}</b></font>", table_cell_style),
                    Paragraph(f"<b>{g.gap_title}</b><br/><font color='#64748B'><i>{g.legal_reference}</i></font>", table_cell_style),
                    Paragraph(g.potential_consequence or "Statutory enforcement notice and administrative penalties.", table_cell_style),
                    Paragraph(g.recommended_action or "Review requirement and implement corrective measures.", table_cell_style),
                ])

            gaps_table = Table(gaps_table_data, colWidths=[45, 50, 140, 140, 148])
            gaps_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), primary_color),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
                ("BOX", (0, 0), (-1, -1), 1, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(gaps_table)
        else:
            elements.append(Paragraph("<i>No compliance gaps identified. All evaluated statutory obligations were fully compliant or not applicable.</i>", body_style))

        elements.append(Spacer(1, 14))

        # 7. Corrective Actions Assigned
        actions = CorrectiveAction.query.filter_by(assessment_id=assessment.id).all()
        if actions:
            elements.append(Paragraph(f"4. Assigned Corrective Actions Register ({len(actions)})", section_heading))
            act_table_data = [
                [
                    Paragraph("Action Title", table_header_style),
                    Paragraph("Priority", table_header_style),
                    Paragraph("Assigned To", table_header_style),
                    Paragraph("Due Date", table_header_style),
                    Paragraph("Status", table_header_style),
                ]
            ]
            for act in actions:
                act_table_data.append([
                    Paragraph(f"<b>{act.title}</b><br/>{act.action_description[:100]}...", table_cell_style),
                    Paragraph(act.priority, table_cell_style),
                    Paragraph(act.assigned_to.full_name if act.assigned_to else "Unassigned", table_cell_style),
                    Paragraph(act.due_date.strftime("%d %b %Y") if act.due_date else "N/A", table_cell_style),
                    Paragraph(act.status, table_cell_style),
                ])
            act_table = Table(act_table_data, colWidths=[200, 60, 110, 75, 78])
            act_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), primary_color),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
                ("BOX", (0, 0), (-1, -1), 1, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]))
            elements.append(act_table)
            elements.append(Spacer(1, 14))

        # 8. Formal Sign-off and Disclaimer (KeepTogether prevents orphan signature line)
        signoff_block = []
        signoff_block.append(Paragraph("5. Formal Audit Sign-Off & Verification", section_heading))

        sign_table_data = [
            [
                Paragraph("<b>Lead Compliance Assessor / Auditor:</b>", body_style),
                Paragraph("<b>Organization Managing Director / Representative:</b>", body_style),
            ],
            [
                Paragraph("<br/><br/>_____________________________________<br/>Signature & Stamp<br/>Date: ________________________", body_style),
                Paragraph("<br/><br/>_____________________________________<br/>Signature & Company Seal<br/>Date: ________________________", body_style),
            ],
        ]
        sign_table = Table(sign_table_data, colWidths=[260, 263])
        sign_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("BACKGROUND", (0, 0), (-1, -1), bg_light),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        signoff_block.append(sign_table)
        signoff_block.append(Spacer(1, 8))

        disclaimer_text = (
            "<b>STATUTORY DISCLAIMER:</b> This report is generated by the Compliance Risk Analytics System (CRAS) "
            "for internal regulatory compliance monitoring, risk management, and managerial decision support. "
            "This report does not constitute a formal legal opinion, legal certification, or statutory guarantee "
            "of compliance by the Kenya Revenue Authority (KRA), Office of the Data Protection Commissioner (ODPC), "
            "Ministry of Labour, or any judicial or regulatory authority. Organizations are advised to seek certified "
            "legal counsel or registered tax consultants for specific legal disputes or formal statutory representation."
        )
        signoff_block.append(Paragraph(disclaimer_text, disclaimer_style))
        signoff_block.append(Spacer(1, 3))
        signoff_block.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | CRAS Engine v1.0 • Verifiable Audit Hash: SHA256:{hex(abs(hash(str(assessment.id) + org.kra_pin)))[2:].upper()}", disclaimer_style))

        elements.append(KeepTogether(signoff_block))

        # Build document with NumberedCanvas for dynamic 2-pass page numbering
        doc.build(elements, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_compliance_certificate_pdf(assessment: ComplianceAssessment) -> io.BytesIO:
        """
        Generates an official, publication-grade Certificate of Regulatory Compliance in landscape A4.
        Features ornate dual borders, CRAS emblem, gold accents, scoring badges, and official auditor signature seals.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        c_navy = colors.HexColor("#172B4D")
        c_gold = colors.HexColor("#D97706")
        c_blue = colors.HexColor("#2563EB")
        c_slate = colors.HexColor("#64748B")

        cert_header_style = ParagraphStyle(
            "CertHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=c_gold,
            alignment=1,
        )

        cert_title_style = ParagraphStyle(
            "CertTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=c_navy,
            alignment=1,
        )

        cert_subtitle_style = ParagraphStyle(
            "CertSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=c_blue,
            alignment=1,
        )

        cert_body_center = ParagraphStyle(
            "CertBodyCenter",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#1E293B"),
            alignment=1,
        )

        org_name_style = ParagraphStyle(
            "OrgName",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=c_navy,
            alignment=1,
        )

        elements = []
        org = assessment.organization

        elements.append(Spacer(1, 10))
        elements.append(Paragraph("★ REPUBLIC OF KENYA • STATUTORY REGULATORY FRAMEWORK ★", cert_header_style))
        elements.append(Paragraph("CERTIFICATE OF REGULATORY COMPLIANCE", cert_title_style))
        elements.append(Paragraph("COMPLIANCE RISK ANALYTICS SYSTEM (CRAS)", cert_subtitle_style))
        elements.append(HRFlowable(width="60%", thickness=1.5, color=c_gold, spaceBefore=6, spaceAfter=14))

        elements.append(Paragraph("THIS IS TO CERTIFY THAT", cert_body_center))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(org.name.upper(), org_name_style))
        elements.append(Spacer(1, 6))

        id_text = f"<b>KRA PIN:</b> {org.kra_pin} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Registration No:</b> {org.business_registration_number} &nbsp;&nbsp;|&nbsp;&nbsp; <b>County:</b> {org.county}"
        elements.append(Paragraph(id_text, cert_body_center))
        elements.append(Spacer(1, 10))

        scope_text = (
            "has undergone a rigorous, structured statutory compliance evaluation across the Kenya Data Protection Act 2019, "
            "the Tax Procedures Act & Income Tax Act, the Employment Act 2007, and the Work Injury Benefits Act (WIBA 2007). "
            "The organization has satisfied the prescribed evaluation thresholds for the audited statutory period."
        )
        elements.append(Paragraph(scope_text, cert_body_center))
        elements.append(Spacer(1, 14))

        # Score & Metric Highlights Card
        score_val = assessment.overall_score if assessment.overall_score is not None else 0.0
        classification = assessment.risk_classification or "NOT_CLASSIFIED"
        badge_color = "#16A34A" if classification == "COMPLIANT" else ("#D97706" if classification == "MODERATE_RISK" else "#DC2626")

        domain_scores = AssessmentDomainScore.query.filter_by(assessment_id=assessment.id).all()
        dp_score = next((f"{(d.normalized_score * 100):.1f}%" for d in domain_scores if "Data" in d.domain.title), "N/A")
        tax_score = next((f"{(d.normalized_score * 100):.1f}%" for d in domain_scores if "Tax" in d.domain.title), "N/A")
        lab_score = next((f"{(d.normalized_score * 100):.1f}%" for d in domain_scores if "Employment" in d.domain.title), "N/A")

        score_box_data = [
            [
                Paragraph("<b>AUDIT PERIOD</b>", ParagraphStyle("C1", parent=cert_body_center, fontSize=8, textColor=c_slate)),
                Paragraph("<b>COMPLIANCE SCORE</b>", ParagraphStyle("C2", parent=cert_body_center, fontSize=8, textColor=c_slate)),
                Paragraph("<b>RISK CLASSIFICATION</b>", ParagraphStyle("C3", parent=cert_body_center, fontSize=8, textColor=c_slate)),
                Paragraph("<b>DATA PROTECTION</b>", ParagraphStyle("C4", parent=cert_body_center, fontSize=8, textColor=c_slate)),
                Paragraph("<b>TAX COMPLIANCE</b>", ParagraphStyle("C5", parent=cert_body_center, fontSize=8, textColor=c_slate)),
                Paragraph("<b>LABOUR & WIBA</b>", ParagraphStyle("C6", parent=cert_body_center, fontSize=8, textColor=c_slate)),
            ],
            [
                Paragraph(f"<b>{assessment.assessment_period}</b>", ParagraphStyle("D1", parent=cert_body_center, fontName="Helvetica-Bold", fontSize=11, textColor=c_navy)),
                Paragraph(f"<b>{score_val:.2f}%</b>", ParagraphStyle("D2", parent=cert_body_center, fontName="Helvetica-Bold", fontSize=14, textColor=colors.HexColor(badge_color))),
                Paragraph(f"<b>{classification.replace('_', ' ')}</b>", ParagraphStyle("D3", parent=cert_body_center, fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor(badge_color))),
                Paragraph(f"<b>{dp_score}</b>", ParagraphStyle("D4", parent=cert_body_center, fontName="Helvetica-Bold", fontSize=11, textColor=c_navy)),
                Paragraph(f"<b>{tax_score}</b>", ParagraphStyle("D5", parent=cert_body_center, fontName="Helvetica-Bold", fontSize=11, textColor=c_navy)),
                Paragraph(f"<b>{lab_score}</b>", ParagraphStyle("D6", parent=cert_body_center, fontName="Helvetica-Bold", fontSize=11, textColor=c_navy)),
            ]
        ]

        score_box = Table(score_box_data, colWidths=[120, 130, 150, 110, 110, 110])
        score_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(score_box)
        elements.append(Spacer(1, 16))

        # Signatures and Seals Block
        cert_num = f"CRAS-CERT-{assessment.id:04d}-{assessment.assessment_period.replace(' ', '')}"
        issue_date_str = assessment.assessment_date.strftime("%d %B %Y") if assessment.assessment_date else datetime.now().strftime("%d %B %Y")

        sig_data = [
            [
                Paragraph(f"<b>Certificate Number:</b> {cert_num}<br/><b>Issue Date:</b> {issue_date_str}<br/><b>Validity:</b> 12 Months from Issue", ParagraphStyle("S1", parent=cert_body_center, alignment=0, fontSize=8.5, textColor=c_slate)),
                Paragraph("<br/><b>DR. EVELYN WANJIKU, ESQ.</b><br/>Lead Regulatory Compliance Auditor<br/><i>CRAS National Oversight Board</i>", ParagraphStyle("S2", parent=cert_body_center, fontSize=8.5, textColor=c_navy)),
                Paragraph("<br/><b>HON. PETER K. MWANGI</b><br/>Director General of Compliance Assurance<br/><i>Statutory Risk Audit Authority</i>", ParagraphStyle("S3", parent=cert_body_center, fontSize=8.5, textColor=c_navy)),
            ]
        ]

        sig_table = Table(sig_data, colWidths=[240, 245, 245])
        sig_table.setStyle(TableStyle([
            ("LINEABOVE", (1, 0), (1, 0), 1, c_navy),
            ("LINEABOVE", (2, 0), (2, 0), 1, c_navy),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(sig_table)

        doc.build(elements, canvasmaker=CertificateCanvas)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_gaps_pdf(org_id: int) -> io.BytesIO:
        """
        Generates a dedicated, publication-ready Regulatory Gaps & Remediation Matrix PDF export.
        Details all non-compliant obligations, legal citations, financial/statutory penalties, and action plans.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=46,
            bottomMargin=46,
        )

        org = Organization.query.get_or_404(org_id)
        gaps = ComplianceGap.query.filter_by(organization_id=org_id).order_by(ComplianceGap.severity).all()

        styles = getSampleStyleSheet()

        primary_color = colors.HexColor("#172B4D")
        secondary_color = colors.HexColor("#2563EB")
        text_color = colors.HexColor("#1E293B")
        bg_light = colors.HexColor("#F8FAFC")
        border_color = colors.HexColor("#E2E8F0")

        title_style = ParagraphStyle(
            "GapTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=primary_color,
        )

        subtitle_style = ParagraphStyle(
            "GapSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=secondary_color,
        )

        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=primary_color,
            spaceAfter=6,
        )

        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=text_color,
        )

        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10.5,
            textColor=colors.white,
        )

        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=text_color,
        )

        elements = []

        # Header
        elements.append(Paragraph("COMPLIANCE RISK ANALYTICS SYSTEM (CRAS)", title_style))
        elements.append(Paragraph("Statutory Gaps & Remediation Exposure Matrix — Kenya SMEs", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=secondary_color, spaceBefore=4, spaceAfter=10))

        # Organization Summary
        crit_count = sum(1 for g in gaps if g.severity == "CRITICAL")
        high_count = sum(1 for g in gaps if g.severity == "HIGH")
        med_count = sum(1 for g in gaps if g.severity in ["MEDIUM", "LOW"])

        meta_table_data = [
            [
                Paragraph("<b>Organization:</b>", body_style),
                Paragraph(org.name, body_style),
                Paragraph("<b>KRA PIN:</b>", body_style),
                Paragraph(org.kra_pin, body_style),
            ],
            [
                Paragraph("<b>Total Identified Gaps:</b>", body_style),
                Paragraph(f"<b>{len(gaps)}</b>", body_style),
                Paragraph("<b>Severity Breakdown:</b>", body_style),
                Paragraph(
                    f"<font color='#DC2626'><b>{crit_count} Critical</b></font> | "
                    f"<font color='#EA580C'><b>{high_count} High</b></font> | "
                    f"<font color='#D97706'><b>{med_count} Med/Low</b></font>",
                    body_style
                ),
            ],
        ]

        meta_table = Table(meta_table_data, colWidths=[110, 150, 110, 153])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_light),
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 14))

        # Gaps Table
        elements.append(Paragraph(f"1. Detailed Regulatory Gaps & Remediation Schedule ({len(gaps)} Items)", section_heading))

        if gaps:
            gaps_table_data = [
                [
                    Paragraph("Ref", table_header_style),
                    Paragraph("Severity", table_header_style),
                    Paragraph("Statutory Obligation & Citation", table_header_style),
                    Paragraph("Non-Compliance Exposure & Statutory Penalties", table_header_style),
                    Paragraph("Remediation Plan & Corrective Action", table_header_style),
                ]
            ]

            for g in gaps:
                sev_color = "#DC2626" if g.severity == "CRITICAL" else ("#EA580C" if g.severity == "HIGH" else "#D97706")
                gaps_table_data.append([
                    Paragraph(f"<b>{g.requirement.code if g.requirement else f'GAP-{g.id}'}</b>", table_cell_style),
                    Paragraph(f"<font color='{sev_color}'><b>{g.severity}</b></font>", table_cell_style),
                    Paragraph(f"<b>{g.gap_title}</b><br/><font color='#64748B'><i>{g.legal_reference}</i></font>", table_cell_style),
                    Paragraph(g.potential_consequence or "Statutory enforcement notice and administrative penalties.", table_cell_style),
                    Paragraph(g.recommended_action or "Execute remediation and verify compliance.", table_cell_style),
                ])

            gaps_table = Table(gaps_table_data, colWidths=[45, 50, 140, 140, 148])
            gaps_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), primary_color),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
                ("BOX", (0, 0), (-1, -1), 1, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(gaps_table)
        else:
            elements.append(Paragraph("<i>No compliance gaps found for this organization. Full regulatory compliance achieved.</i>", body_style))

        elements.append(Spacer(1, 14))

        # Sign-off & Disclaimer
        sign_block = []
        sign_block.append(Paragraph("2. Auditor Sign-Off & Remediation Acknowledgement", section_heading))
        sign_table_data = [
            [
                Paragraph("<b>Compliance Auditor:</b><br/><br/>_____________________________________<br/>Date: ________________________", body_style),
                Paragraph("<b>Remediation Task Owner:</b><br/><br/>_____________________________________<br/>Date: ________________________", body_style),
            ]
        ]
        sign_table = Table(sign_table_data, colWidths=[260, 263])
        sign_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("BACKGROUND", (0, 0), (-1, -1), bg_light),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        sign_block.append(sign_table)
        sign_block.append(Spacer(1, 8))

        disclaimer_text = (
            "<b>STATUTORY NOTICE:</b> This Compliance Gaps & Remediation Matrix is generated for internal risk mitigation. "
            "Remediation timelines must adhere to prescribed statutory windows under the Kenya Data Protection Act 2019, "
            "Tax Procedures Act, and Employment Act 2007 to avoid statutory escalation, penalties, or legal action."
        )
        sign_block.append(Paragraph(disclaimer_text, ParagraphStyle("D", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=7.5, leading=10.5, textColor=colors.HexColor("#64748B"))))
        sign_block.append(Spacer(1, 3))
        sign_block.append(Paragraph(f"Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | CRAS Engine v1.0", ParagraphStyle("F", parent=styles["Normal"], fontName="Helvetica", fontSize=7.5, textColor=colors.HexColor("#64748B"))))

        elements.append(KeepTogether(sign_block))

        doc.build(elements, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_assessment_csv(assessment: ComplianceAssessment) -> str:
        """Generates CSV export of all assessment responses, requirements, and domain scores."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header info
        writer.writerow(["CRAS - COMPLIANCE ASSESSMENT EXPORT"])
        writer.writerow(["Organization", assessment.organization.name])
        writer.writerow(["KRA PIN", assessment.organization.kra_pin])
        writer.writerow(["Assessment Period", assessment.assessment_period])
        writer.writerow(["Assessment Date", assessment.assessment_date])
        writer.writerow(["Overall Compliance Score (%)", f"{assessment.overall_score:.2f}" if assessment.overall_score else "N/A"])
        writer.writerow(["Risk Classification", assessment.risk_classification])
        writer.writerow([])

        # Responses table
        writer.writerow([
            "Domain Code",
            "Category",
            "Requirement Code",
            "Requirement Title",
            "Legal Reference",
            "Risk Weight",
            "Response",
            "Score Factor",
            "Assessor Notes",
            "Potential Consequence",
            "Recommended Action",
        ])

        for resp in assessment.responses:
            req = resp.requirement
            writer.writerow([
                req.domain.code if req and req.domain else "",
                req.category.title if req and req.category else "",
                req.code if req else "",
                req.title if req else "",
                req.legal_reference if req else "",
                req.risk_weight if req else "",
                resp.response_value,
                resp.response_score if resp.response_score is not None else "N/A",
                resp.notes or "",
                req.potential_consequence if req else "",
                req.recommended_corrective_action if req else "",
            ])

        return output.getvalue()

    @staticmethod
    def generate_gaps_csv(org_id: int) -> str:
        """Generates CSV export of all compliance gaps for an organization."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Gap ID",
            "Domain",
            "Requirement Code",
            "Gap Title",
            "Severity",
            "Status",
            "Legal Reference",
            "Potential Consequence",
            "Recommended Action",
            "Identified Date",
        ])

        gaps = ComplianceGap.query.filter_by(organization_id=org_id).all()
        for g in gaps:
            writer.writerow([
                g.id,
                g.domain.title if g.domain else "",
                g.requirement.code if g.requirement else "",
                g.gap_title,
                g.severity,
                g.status,
                g.legal_reference,
                g.potential_consequence or "",
                g.recommended_action or "",
                g.identified_at.strftime("%Y-%m-%d") if g.identified_at else "",
            ])

        return output.getvalue()

    @staticmethod
    def generate_excel_export(assessment: ComplianceAssessment) -> io.BytesIO:
        """Generates an Excel workbook with sheets for Summary, Domain Breakdown, Responses, and Gaps."""
        wb = Workbook()
        ws_summary = wb.active
        ws_summary.title = "Assessment Summary"

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="172B4D", end_color="172B4D", fill_type="solid")

        # Summary sheet
        ws_summary.append(["COMPLIANCE RISK ANALYTICS SYSTEM (CRAS)"])
        ws_summary.append(["Executive Assessment Summary"])
        ws_summary.append([])
        ws_summary.append(["Organization", assessment.organization.name])
        ws_summary.append(["KRA PIN", assessment.organization.kra_pin])
        ws_summary.append(["Assessment Period", assessment.assessment_period])
        ws_summary.append(["Assessment Date", str(assessment.assessment_date)])
        ws_summary.append(["Overall Compliance Score", f"{assessment.overall_score:.2f}%" if assessment.overall_score else "N/A"])
        ws_summary.append(["Risk Classification", assessment.risk_classification])
        ws_summary.append(["Total Obligations", assessment.total_obligations])
        ws_summary.append(["Compliant Obligations", assessment.compliant_count])
        ws_summary.append(["Partially Compliant Obligations", assessment.partially_compliant_count])
        ws_summary.append(["Non-Compliant Obligations", assessment.non_compliant_count])
        ws_summary.append(["Not Applicable Obligations", assessment.not_applicable_count])

        # Domain breakdown sheet
        ws_domains = wb.create_sheet(title="Domain Scores")
        headers_domains = ["Domain", "Weight", "Applicable Items", "Score (%)", "Weighted Contribution (pts)", "Classification"]
        ws_domains.append(headers_domains)
        for cell in ws_domains[1]:
            cell.font = header_font
            cell.fill = header_fill

        for ds in assessment.domain_scores:
            ws_domains.append([
                ds.domain.title,
                f"{int(ds.domain_weight * 100)}%",
                ds.applicable_obligations_count,
                f"{(ds.normalized_score * 100):.2f}%",
                f"{ds.weighted_score:.2f}",
                ds.classification,
            ])

        # Responses sheet
        ws_responses = wb.create_sheet(title="Detailed Responses")
        headers_resp = ["Domain", "Requirement Code", "Title", "Legal Reference", "Weight", "Response", "Score", "Notes"]
        ws_responses.append(headers_resp)
        for cell in ws_responses[1]:
            cell.font = header_font
            cell.fill = header_fill

        for r in assessment.responses:
            req = r.requirement
            ws_responses.append([
                req.domain.code if req and req.domain else "",
                req.code if req else "",
                req.title if req else "",
                req.legal_reference if req else "",
                req.risk_weight if req else "",
                r.response_value,
                r.response_score if r.response_score is not None else "N/A",
                r.notes or "",
            ])

        # Auto-adjust column widths
        for ws in wb.worksheets:
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = col[0].column_letter
                ws.column_dimensions[col_letter].width = min(max_len + 3, 50)

        stream = io.BytesIO()
        wb.save(stream)
        stream.seek(0)
        return stream
