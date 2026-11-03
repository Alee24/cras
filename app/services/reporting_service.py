import io
import csv
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.models.assessment import ComplianceAssessment, AssessmentDomainScore
from app.models.compliance_management import ComplianceGap, CorrectiveAction
from app.models.regulatory import RegulatoryRequirement


class ReportingService:
    @staticmethod
    def generate_assessment_pdf(assessment: ComplianceAssessment) -> io.BytesIO:
        """
        Generates a comprehensive, professionally styled PDF report for a ComplianceAssessment.
        Uses ReportLab with CRAS enterprise color palette:
        - Primary Navy: #172B4D
        - Secondary Blue: #2563EB
        - Green: #16A34A
        - Amber: #F59E0B
        - Red: #DC2626
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        # Custom styles
        primary_color = colors.HexColor("#172B4D")
        secondary_color = colors.HexColor("#2563EB")
        text_color = colors.HexColor("#1E293B")
        bg_light = colors.HexColor("#F8FAFC")
        border_color = colors.HexColor("#E2E8F0")

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=primary_color,
        )

        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=secondary_color,
        )

        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=primary_color,
            spaceAfter=6,
        )

        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=text_color,
        )

        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
        )

        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=text_color,
        )

        badge_text_style = ParagraphStyle(
            "BadgeText",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            textColor=colors.white,
            alignment=1, # Center
        )

        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748B"),
        )

        elements = []

        # 1. Header Banner
        org = assessment.organization
        elements.append(Paragraph("COMPLIANCE RISK ANALYTICS SYSTEM (CRAS)", title_style))
        elements.append(Paragraph("Regulatory Compliance & Risk Intelligence for SMEs in Kenya", subtitle_style))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=2, color=secondary_color, spaceBefore=2, spaceAfter=14))

        # 2. Executive Metadata Box
        meta_data = [
            [
                Paragraph("<b>Organization:</b>", body_style),
                Paragraph(org.name, body_style),
                Paragraph("<b>KRA PIN:</b>", body_style),
                Paragraph(org.kra_pin, body_style),
            ],
            [
                Paragraph("<b>Registration No:</b>", body_style),
                Paragraph(org.business_registration_number, body_style),
                Paragraph("<b>County:</b>", body_style),
                Paragraph(org.county, body_style),
            ],
            [
                Paragraph("<b>Assessment Period:</b>", body_style),
                Paragraph(assessment.assessment_period, body_style),
                Paragraph("<b>Assessment Date:</b>", body_style),
                Paragraph(assessment.assessment_date.strftime("%d %b %Y") if assessment.assessment_date else "N/A", body_style),
            ],
            [
                Paragraph("<b>Scoring Policy:</b>", body_style),
                Paragraph(f"Kenya SME Standard ({assessment.scoring_policy_version.version_number if assessment.scoring_policy_version else 'v1.0'})", body_style),
                Paragraph("<b>Status:</b>", body_style),
                Paragraph(f"<b>{assessment.status}</b>", body_style),
            ],
        ]

        meta_table = Table(meta_data, colWidths=[110, 150, 110, 150])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_light),
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 14))

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
                Paragraph("<b>OVERALL COMPLIANCE SCORE</b>", ParagraphStyle("ScoreLbl", parent=body_style, fontName="Helvetica-Bold", fontSize=11, textColor=primary_color)),
                Paragraph(f"<b>{score_val:.2f}%</b>", ParagraphStyle("ScoreBig", parent=body_style, fontName="Helvetica-Bold", fontSize=22, leading=24, textColor=primary_color, alignment=1)),
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

        score_table = Table(score_table_data, colWidths=[200, 140, 180])
        score_table.setStyle(TableStyle([
            ("SPAN", (0, 1), (2, 1)),
            ("BACKGROUND", (0, 0), (1, 0), bg_light),
            ("BACKGROUND", (2, 0), (2, 0), badge_bg),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(score_table)
        elements.append(Spacer(1, 16))

        # 4. Domain Breakdown Table
        elements.append(Paragraph("1. Regulatory Domain Compliance Breakdown", section_heading))
        domain_table_data = [
            [
                Paragraph("Regulatory Domain", table_header_style),
                Paragraph("Weight", table_header_style),
                Paragraph("Applicable Items", table_header_style),
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

        domain_table = Table(domain_table_data, colWidths=[150, 45, 125, 65, 75, 60])
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
        elements.append(Spacer(1, 16))

        # 5. Compliance Gaps & Recommended Actions
        gaps = ComplianceGap.query.filter_by(assessment_id=assessment.id).order_by(ComplianceGap.severity).all()
        elements.append(Paragraph(f"2. Identified Regulatory Gaps & Immediate Actions ({len(gaps)})", section_heading))

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

            gaps_table = Table(gaps_table_data, colWidths=[45, 50, 140, 140, 145])
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
            elements.append(Paragraph("<i>No compliance gaps identified. All evaluated obligations were compliant or not applicable.</i>", body_style))

        elements.append(Spacer(1, 16))

        # 6. Corrective Actions Assigned
        actions = CorrectiveAction.query.filter_by(assessment_id=assessment.id).all()
        if actions:
            elements.append(Paragraph(f"3. Assigned Corrective Actions ({len(actions)})", section_heading))
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
            act_table = Table(act_table_data, colWidths=[200, 60, 110, 75, 75])
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
            elements.append(Spacer(1, 16))

        # 7. Statutory Disclaimer
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1, color=border_color, spaceBefore=4, spaceAfter=8))
        disclaimer_text = (
            "<b>STATUTORY DISCLAIMER:</b> This report is generated by the Compliance Risk Analytics System (CRAS) "
            "for internal regulatory compliance monitoring, risk management, and managerial decision support. "
            "This report does not constitute a formal legal opinion, legal certification, or statutory guarantee "
            "of compliance by the Kenya Revenue Authority (KRA), Office of the Data Protection Commissioner (ODPC), "
            "Ministry of Labour, or any judicial or regulatory authority. Organizations are advised to seek certified "
            "legal counsel or registered tax consultants for specific legal disputes or formal statutory representation."
        )
        elements.append(Paragraph(disclaimer_text, disclaimer_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | CRAS Engine v1.0", disclaimer_style))

        # Build document
        doc.build(elements)
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
                req.domain.code,
                req.category.title if req.category else "",
                req.code,
                req.title,
                req.legal_reference,
                req.risk_weight,
                resp.response_value,
                resp.response_score if resp.response_score is not None else "N/A",
                resp.notes or "",
                req.potential_consequence or "",
                req.recommended_corrective_action or "",
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
                g.identified_at.strftime("%Y-%m-%d"),
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
            ws_responses.append([
                r.requirement.domain.code,
                r.requirement.code,
                r.requirement.title,
                r.requirement.legal_reference,
                r.requirement.risk_weight,
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
