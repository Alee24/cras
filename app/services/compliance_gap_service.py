from app.models.base import db, utcnow
from app.models.assessment import ComplianceAssessment, AssessmentResponse
from app.models.compliance_management import ComplianceGap, CorrectiveAction


class ComplianceGapService:
    @classmethod
    def sync_gaps_for_assessment(cls, assessment: ComplianceAssessment) -> int:
        """
        Scans all responses in an assessment and generates or updates ComplianceGaps
        for any NON_COMPLIANT or PARTIALLY_COMPLIANT obligation.
        """
        created_or_updated = 0
        responses = AssessmentResponse.query.filter_by(assessment_id=assessment.id).all()

        for resp in responses:
            val = resp.response_value
            if val in (AssessmentResponse.RESPONSE_NON_COMPLIANT, AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT):
                req = resp.requirement
                
                # Determine severity
                if val == AssessmentResponse.RESPONSE_NON_COMPLIANT:
                    if req.risk_weight >= 3.0:
                        severity = ComplianceGap.SEVERITY_CRITICAL
                    elif req.risk_weight >= 2.0:
                        severity = ComplianceGap.SEVERITY_HIGH
                    else:
                        severity = ComplianceGap.SEVERITY_MEDIUM
                else: # PARTIALLY_COMPLIANT
                    if req.risk_weight >= 3.0:
                        severity = ComplianceGap.SEVERITY_HIGH
                    else:
                        severity = ComplianceGap.SEVERITY_MEDIUM

                gap_title = f"{'Partial Compliance' if val == AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT else 'Non-Compliance'}: {req.title}"
                gap_desc = (
                    f"Requirement '{req.code}' ({req.title}) was assessed as {val.replace('_', ' ').title()}. "
                    f"Requirement summary: {req.plain_description}"
                )
                if resp.notes:
                    gap_desc += f" Assessor Notes: {resp.notes}"

                gap = ComplianceGap.query.filter_by(
                    organization_id=assessment.organization_id,
                    assessment_id=assessment.id,
                    requirement_id=req.id,
                ).first()

                if not gap:
                    gap = ComplianceGap(
                        organization_id=assessment.organization_id,
                        assessment_id=assessment.id,
                        requirement_id=req.id,
                        domain_id=req.domain_id,
                        gap_title=gap_title,
                        gap_description=gap_desc,
                        legal_reference=req.legal_reference,
                        potential_consequence=req.potential_consequence,
                        recommended_action=req.recommended_corrective_action,
                        severity=severity,
                        status=ComplianceGap.STATUS_OPEN,
                        identified_at=utcnow(),
                    )
                    db.session.add(gap)
                    created_or_updated += 1
                else:
                    gap.gap_title = gap_title
                    gap.gap_description = gap_desc
                    gap.severity = severity
                    gap.potential_consequence = req.potential_consequence
                    gap.recommended_action = req.recommended_corrective_action
                    created_or_updated += 1

        db.session.commit()
        return created_or_updated

