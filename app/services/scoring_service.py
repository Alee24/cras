from typing import Dict, Any, Tuple, List
from app.models.base import db, utcnow
from app.models.regulatory import RegulatoryDomain, RegulatoryRequirement
from app.models.scoring import ScoringPolicyVersion
from app.models.assessment import ComplianceAssessment, AssessmentResponse, AssessmentDomainScore


class ScoringValidationError(Exception):
    """Raised when an assessment cannot be scored due to missing or invalid responses."""
    pass


class ScoringEngine:
    """
    Deterministic Compliance and Risk Scoring Engine.
    
    Formula:
        Overall Compliance Score = SUM(Wi * Ci) * 100
        where:
            Wi = Weight assigned to regulatory domain i (SUM Wi = 1.0)
            Ci = Domain compliance score, normalized between 0.0 and 1.0
            
    Domain Compliance Score (Ci):
        Ci = SUM(risk_weight_k * response_score_k) / SUM(risk_weight_k)
        for all applicable requirements k in domain i.
        
    Response Score Mapping:
        COMPLIANT = 1.0
        PARTIALLY_COMPLIANT = 0.5
        NON_COMPLIANT = 0.0
        NOT_APPLICABLE = Excluded from both numerator and denominator
        NOT_ASSESSED = Raises ScoringValidationError; never silently treated as compliant!
    """

    @classmethod
    def calculate_assessment_scores(
        cls, assessment: ComplianceAssessment, policy_version: ScoringPolicyVersion
    ) -> Dict[str, Any]:
        """
        Calculates domain scores and overall composite compliance score.
        Validates that no unanswered obligations remain.
        """
        domain_weights = policy_version.domain_weights
        response_score_map = policy_version.response_scores

        # Ensure all requirements for active domains have a response
        domains = RegulatoryDomain.query.filter_by(is_active=True).all()
        responses = {r.requirement_id: r for r in assessment.responses}

        total_obligations = 0
        compliant_count = 0
        partially_compliant_count = 0
        non_compliant_count = 0
        not_applicable_count = 0
        not_assessed_count = 0

        unanswered_reqs: List[str] = []

        domain_results = []
        composite_score = 0.0
        total_active_weight = 0.0

        for domain in domains:
            weight = domain_weights.get(domain.code, 0.0)
            reqs = RegulatoryRequirement.query.filter_by(domain_id=domain.id, is_active=True).all()
            
            domain_applicable_weight = 0.0
            domain_weighted_points = 0.0
            domain_compliant_cnt = 0
            domain_partially_cnt = 0
            domain_non_compliant_cnt = 0
            domain_na_cnt = 0

            for req in reqs:
                total_obligations += 1
                resp = responses.get(req.id)
                
                if not resp or resp.response_value == AssessmentResponse.RESPONSE_NOT_ASSESSED or not resp.response_value:
                    not_assessed_count += 1
                    unanswered_reqs.append(f"[{domain.code}] {req.code}: {req.title}")
                    continue

                val = resp.response_value
                if val == AssessmentResponse.RESPONSE_COMPLIANT:
                    compliant_count += 1
                    domain_compliant_cnt += 1
                    score_factor = response_score_map.get("COMPLIANT", 1.0)
                    resp.response_score = score_factor
                    domain_applicable_weight += req.risk_weight
                    domain_weighted_points += (req.risk_weight * score_factor)

                elif val == AssessmentResponse.RESPONSE_PARTIALLY_COMPLIANT:
                    partially_compliant_count += 1
                    domain_partially_cnt += 1
                    score_factor = response_score_map.get("PARTIALLY_COMPLIANT", 0.5)
                    resp.response_score = score_factor
                    domain_applicable_weight += req.risk_weight
                    domain_weighted_points += (req.risk_weight * score_factor)

                elif val == AssessmentResponse.RESPONSE_NON_COMPLIANT:
                    non_compliant_count += 1
                    domain_non_compliant_cnt += 1
                    score_factor = response_score_map.get("NON_COMPLIANT", 0.0)
                    resp.response_score = score_factor
                    domain_applicable_weight += req.risk_weight
                    domain_weighted_points += (req.risk_weight * score_factor)

                elif val == AssessmentResponse.RESPONSE_NOT_APPLICABLE:
                    not_applicable_count += 1
                    domain_na_cnt += 1
                    resp.response_score = None
                    # Excluded from both numerator and denominator!

            # Domain normalization
            if domain_applicable_weight > 0:
                normalized_score = domain_weighted_points / domain_applicable_weight # Ci between 0.0 and 1.0
            else:
                # All obligations were Not Applicable
                normalized_score = 1.0

            # Scale to 0 - 100 for domain classification
            domain_percentage = normalized_score * 100.0
            domain_classification = policy_version.classify_score(domain_percentage)
            weighted_contrib = weight * normalized_score * 100.0

            composite_score += weighted_contrib
            total_active_weight += weight

            domain_results.append({
                "domain": domain,
                "domain_id": domain.id,
                "weight": weight,
                "raw_score": round(domain_weighted_points, 4),
                "normalized_score": round(normalized_score, 4),
                "weighted_score": round(weighted_contrib, 2),
                "percentage": round(domain_percentage, 2),
                "classification": domain_classification,
                "applicable_count": len(reqs) - domain_na_cnt,
                "compliant_count": domain_compliant_cnt,
                "partially_compliant_count": domain_partially_cnt,
                "non_compliant_count": domain_non_compliant_cnt,
                "not_applicable_count": domain_na_cnt,
            })

        if not_assessed_count > 0:
            raise ScoringValidationError(
                f"Assessment has {not_assessed_count} unassessed obligation(s). "
                f"Every obligation must be explicitly assessed (Compliant, Partially Compliant, Non-Compliant, or Not Applicable). "
                f"Unanswered items: {', '.join(unanswered_reqs[:5])}..."
            )

        # Normalize composite score if total weights slightly deviate from 1.0
        final_overall_score = composite_score / total_active_weight if total_active_weight > 0 else 0.0
        final_overall_score = max(0.0, min(100.0, round(final_overall_score, 2)))
        overall_classification = policy_version.classify_score(final_overall_score)

        return {
            "overall_score": final_overall_score,
            "risk_classification": overall_classification,
            "total_obligations": total_obligations,
            "compliant_count": compliant_count,
            "partially_compliant_count": partially_compliant_count,
            "non_compliant_count": non_compliant_count,
            "not_applicable_count": not_applicable_count,
            "not_assessed_count": 0,
            "domain_results": domain_results,
        }

    @classmethod
    def apply_and_persist_scores(
        cls, assessment: ComplianceAssessment, policy_version: ScoringPolicyVersion
    ) -> Dict[str, Any]:
        """Calculates and persists domain scores and assessment score to database."""
        result = cls.calculate_assessment_scores(assessment, policy_version)

        assessment.overall_score = result["overall_score"]
        assessment.risk_classification = result["risk_classification"]
        assessment.total_obligations = result["total_obligations"]
        assessment.compliant_count = result["compliant_count"]
        assessment.partially_compliant_count = result["partially_compliant_count"]
        assessment.non_compliant_count = result["non_compliant_count"]
        assessment.not_applicable_count = result["not_applicable_count"]
        assessment.not_assessed_count = 0
        assessment.scoring_policy_version_id = policy_version.id

        # Update or create AssessmentDomainScore records
        for d_res in result["domain_results"]:
            dom_score = AssessmentDomainScore.query.filter_by(
                assessment_id=assessment.id, domain_id=d_res["domain_id"]
            ).first()
            if not dom_score:
                dom_score = AssessmentDomainScore(
                    assessment_id=assessment.id,
                    domain_id=d_res["domain_id"],
                    raw_score=d_res["raw_score"],
                    normalized_score=d_res["normalized_score"],
                    domain_weight=d_res["weight"],
                    weighted_score=d_res["weighted_score"],
                    classification=d_res["classification"],
                    applicable_obligations_count=d_res["applicable_count"],
                    compliant_count=d_res["compliant_count"],
                    partially_compliant_count=d_res["partially_compliant_count"],
                    non_compliant_count=d_res["non_compliant_count"],
                    not_applicable_count=d_res["not_applicable_count"],
                )
                db.session.add(dom_score)
            else:
                dom_score.raw_score = d_res["raw_score"]
                dom_score.normalized_score = d_res["normalized_score"]
                dom_score.domain_weight = d_res["weight"]
                dom_score.weighted_score = d_res["weighted_score"]
                dom_score.classification = d_res["classification"]
                dom_score.applicable_obligations_count = d_res["applicable_count"]
                dom_score.compliant_count = d_res["compliant_count"]
                dom_score.partially_compliant_count = d_res["partially_compliant_count"]
                dom_score.non_compliant_count = d_res["non_compliant_count"]
                dom_score.not_applicable_count = d_res["not_applicable_count"]

        db.session.commit()
        return result
