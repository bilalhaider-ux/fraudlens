import logging
from typing import List, Dict, Tuple, Any
from models import RuleDefinition, TransactionEvaluationRequest, ReasonCode

logger = logging.getLogger("fraud_lens.rules")

class RuleEngine:
    def __init__(self):
        self.rules: Dict[str, RuleDefinition] = {}
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        default_rules = [
            RuleDefinition(
                id="RULE_001",
                name="Extreme Transaction Value",
                description="Transaction amount exceeds $3,500.00 threshold",
                condition_type="AMOUNT_THRESHOLD",
                threshold_value=3500.0,
                action="FLAG_REVIEW",
                risk_weight=35.0,
                enabled=True,
                trigger_count=0
            ),
            RuleDefinition(
                id="RULE_002",
                name="Rapid Velocity Spike (1-Hour)",
                description="More than 4 transactions attempted within a 1-hour window",
                condition_type="VELOCITY_SPIKE",
                threshold_value=4,
                action="FLAG_REVIEW",
                risk_weight=40.0,
                enabled=True,
                trigger_count=0
            ),
            RuleDefinition(
                id="RULE_003",
                name="International Geolocation Mismatch",
                description="IP country differs from card billing country with high distance",
                condition_type="GEO_MISMATCH",
                threshold_value=None,
                action="FLAG_REVIEW",
                risk_weight=30.0,
                enabled=True,
                trigger_count=0
            ),
            RuleDefinition(
                id="RULE_004",
                name="Unrecognized Device High-Risk Purchase",
                description="New device fingerprint executing purchase > 3x average 30-day user spend",
                condition_type="NEW_DEVICE_HIGH_AMOUNT",
                threshold_value=3.0,
                action="FLAG_REVIEW",
                risk_weight=35.0,
                enabled=True,
                trigger_count=0
            ),
            RuleDefinition(
                id="RULE_005",
                name="High-Risk Merchant Category (Crypto/Offshore)",
                description="Transaction routed through cryptocurrency exchange or money transmitter",
                condition_type="HIGH_RISK_MCC",
                threshold_value="crypto,money_transfer",
                action="FLAG_REVIEW",
                risk_weight=25.0,
                enabled=True,
                trigger_count=0
            ),
            RuleDefinition(
                id="RULE_006",
                name="Anonymized Proxy / TOR Exit Node",
                description="Transaction initiated through a detected VPN, TOR, or commercial data center proxy",
                condition_type="VPN_PROXY_USAGE",
                threshold_value=None,
                action="FLAG_REVIEW",
                risk_weight=30.0,
                enabled=True,
                trigger_count=0
            ),
            RuleDefinition(
                id="RULE_007",
                name="Impossible Travel Velocity",
                description="Transaction location distance exceeds 1,500 km from user's origin",
                condition_type="IMPOSSIBLE_TRAVEL",
                threshold_value=1500.0,
                action="AUTO_DECLINE",
                risk_weight=50.0,
                enabled=True,
                trigger_count=0
            )
        ]
        for rule in default_rules:
            self.rules[rule.id] = rule

    def evaluate(self, req: TransactionEvaluationRequest) -> Tuple[List[str], List[ReasonCode], float, str]:
        """
        Evaluates the transaction against all enabled rules.
        Returns:
            - triggered_rule_names: List[str]
            - reason_codes: List[ReasonCode]
            - total_rule_boost: float (max 60)
            - enforced_action: str ("APPROVE", "FLAG_REVIEW", "AUTO_DECLINE")
        """
        triggered_rules = []
        reason_codes = []
        rule_boost = 0.0
        enforced_action = "APPROVE"

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            matched = False
            reason_text = ""

            if rule.condition_type == "AMOUNT_THRESHOLD":
                thresh = float(rule.threshold_value or 3500)
                if req.amount >= thresh:
                    matched = True
                    reason_text = f"Amount ${req.amount:,.2f} exceeds rule threshold (${thresh:,.2f})"

            elif rule.condition_type == "VELOCITY_SPIKE":
                thresh = int(rule.threshold_value or 4)
                if (req.velocity_1h or 1) >= thresh:
                    matched = True
                    reason_text = f"Velocity spike: {req.velocity_1h} transactions in 1 hour (limit: {thresh})"

            elif rule.condition_type == "GEO_MISMATCH":
                if req.ip_country and req.billing_country and req.ip_country.upper() != req.billing_country.upper():
                    matched = True
                    reason_text = f"Cross-border anomaly: IP in {req.ip_country} vs Billing in {req.billing_country}"

            elif rule.condition_type == "NEW_DEVICE_HIGH_AMOUNT":
                mult = float(rule.threshold_value or 3.0)
                avg = req.avg_user_amount_30d or 85.0
                if req.is_new_device and (req.amount > avg * mult):
                    matched = True
                    reason_text = f"New unrecognized device with order amount {req.amount/avg:.1f}x higher than baseline"

            elif rule.condition_type == "HIGH_RISK_MCC":
                high_risk_cats = [c.strip().lower() for c in str(rule.threshold_value).split(",")]
                if req.merchant_category.lower() in high_risk_cats:
                    matched = True
                    reason_text = f"High-risk merchant industry category: '{req.merchant_category}'"

            elif rule.condition_type == "VPN_PROXY_USAGE":
                if req.is_vpn_or_proxy:
                    matched = True
                    reason_text = "Transaction routed via anonymizing VPN / proxy / TOR endpoint"

            elif rule.condition_type == "IMPOSSIBLE_TRAVEL":
                thresh = float(rule.threshold_value or 1500.0)
                dist = req.distance_from_billing_km or 0.0
                if dist >= thresh:
                    matched = True
                    reason_text = f"Impossible travel speed: physical distance {dist:,.0f} km from primary origin"

            if matched:
                rule.trigger_count += 1
                triggered_rules.append(f"{rule.name} ({rule.id})")
                rule_boost += rule.risk_weight
                reason_codes.append(ReasonCode(
                    factor=rule.name,
                    impact=f"+{int(rule.risk_weight)}%",
                    direction="RISK_INCREASE",
                    description=reason_text
                ))
                if rule.action == "AUTO_DECLINE":
                    enforced_action = "AUTO_DECLINE"
                elif rule.action == "FLAG_REVIEW" and enforced_action != "AUTO_DECLINE":
                    enforced_action = "FLAG_REVIEW"

        # Cap total rule boost
        rule_boost = min(rule_boost, 65.0)
        return triggered_rules, reason_codes, rule_boost, enforced_action

    def get_all_rules(self) -> List[RuleDefinition]:
        return list(self.rules.values())

    def add_rule(self, rule: RuleDefinition) -> RuleDefinition:
        self.rules[rule.id] = rule
        return rule

    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> RuleDefinition:
        if rule_id not in self.rules:
            raise KeyError(f"Rule {rule_id} not found")
        rule = self.rules[rule_id]
        for key, val in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, val)
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False
