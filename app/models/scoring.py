import json
from app.models.base import db, utcnow


class ScoringPolicy(db.Model):
    __tablename__ = "scoring_policies"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True) # STANDARD_SME_KENYA
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    versions = db.relationship("ScoringPolicyVersion", backref="policy", cascade="all, delete-orphan", order_by="desc(ScoringPolicyVersion.version_number)", lazy="selectin")

    def __repr__(self):
        return f"<ScoringPolicy {self.code}>"


class ScoringPolicyVersion(db.Model):
    __tablename__ = "scoring_policy_versions"

    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey("scoring_policies.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = db.Column(db.String(20), nullable=False) # e.g. "v1.0"
    
    # Weights for domains: DATA_PROTECTION=0.35, TAX=0.35, LABOUR=0.30 (Sum = 1.0)
    domain_weights_json = db.Column(db.Text, nullable=False, default='{"DATA_PROTECTION": 0.35, "TAX": 0.35, "LABOUR": 0.30}')
    
    # Response score mapping: COMPLIANT=1.0, PARTIALLY_COMPLIANT=0.5, NON_COMPLIANT=0.0
    response_scores_json = db.Column(db.Text, nullable=False, default='{"COMPLIANT": 1.0, "PARTIALLY_COMPLIANT": 0.5, "NON_COMPLIANT": 0.0}')
    
    # RAG boundaries: 0-49.99 High Risk, 50-79.99 Moderate Risk, 80-100 Compliant
    rag_thresholds_json = db.Column(db.Text, nullable=False, default='{"high_risk_max": 49.99, "moderate_risk_max": 79.99, "compliant_min": 80.0}')

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("policy_id", "version_number", name="uq_policy_version"),
    )

    @property
    def domain_weights(self) -> dict:
        try:
            return json.loads(self.domain_weights_json)
        except Exception:
            return {"DATA_PROTECTION": 0.35, "TAX": 0.35, "LABOUR": 0.30}

    @domain_weights.setter
    def domain_weights(self, value: dict):
        self.domain_weights_json = json.dumps(value)

    @property
    def response_scores(self) -> dict:
        try:
            return json.loads(self.response_scores_json)
        except Exception:
            return {"COMPLIANT": 1.0, "PARTIALLY_COMPLIANT": 0.5, "NON_COMPLIANT": 0.0}

    @response_scores.setter
    def response_scores(self, value: dict):
        self.response_scores_json = json.dumps(value)

    @property
    def rag_thresholds(self) -> dict:
        try:
            return json.loads(self.rag_thresholds_json)
        except Exception:
            return {"high_risk_max": 49.99, "moderate_risk_max": 79.99, "compliant_min": 80.0}

    @rag_thresholds.setter
    def rag_thresholds(self, value: dict):
        self.rag_thresholds_json = json.dumps(value)

    def classify_score(self, score: float) -> str:
        """
        Classify compliance score into RAG category:
        0 - 49.99: High Risk (Red)
        50 - 79.99: Moderate Risk (Amber)
        80 - 100: Compliant (Green)
        """
        if score is None:
            return "NOT_CLASSIFIED"
        thresh = self.rag_thresholds
        if score <= thresh.get("high_risk_max", 49.99):
            return "HIGH_RISK"
        elif score <= thresh.get("moderate_risk_max", 79.99):
            return "MODERATE_RISK"
        else:
            return "COMPLIANT"

    def __repr__(self):
        return f"<ScoringPolicyVersion {self.version_number}>"
