from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class TransactionStatus(str, Enum):
    APPROVED = "APPROVED"
    UNDER_REVIEW = "UNDER_REVIEW"
    DECLINED = "DECLINED"
    MANUALLY_APPROVED = "MANUALLY_APPROVED"
    MANUALLY_BLOCKED = "MANUALLY_BLOCKED"

class ReasonCode(BaseModel):
    factor: str
    impact: str
    direction: str = "RISK_INCREASE"  # RISK_INCREASE or RISK_DECREASE
    description: str

class Transaction(BaseModel):
    id: str
    timestamp: str
    user_id: str
    amount: float
    currency: str = "USD"
    merchant: str
    merchant_category: str
    card_type: str = "credit"
    card_bin: str
    card_last4: str
    ip_address: str
    ip_country: str
    billing_country: str
    shipping_country: str
    device_fingerprint: str
    device_type: str
    is_new_device: bool = False
    is_vpn_or_proxy: bool = False
    distance_from_billing_km: float = 0.0
    velocity_1h: int = 1
    velocity_24h: int = 1
    avg_user_amount_30d: float = 85.0
    
    # ML & Rule Scoring results
    risk_score: float = 0.0  # 0.0 to 100.0
    risk_level: RiskLevel = RiskLevel.LOW
    status: TransactionStatus = TransactionStatus.APPROVED
    ml_probability: float = 0.0
    rule_score_boost: float = 0.0
    triggered_rules: List[str] = []
    reason_codes: List[ReasonCode] = []
    notes: List[Dict[str, Any]] = []
    latency_ms: float = 1.2

class TransactionEvaluationRequest(BaseModel):
    user_id: str
    amount: float
    currency: str = "USD"
    merchant: str
    merchant_category: str
    card_type: str = "credit"
    card_bin: Optional[str] = "453201"
    card_last4: Optional[str] = "1234"
    ip_address: Optional[str] = "198.51.100.12"
    ip_country: Optional[str] = "US"
    billing_country: Optional[str] = "US"
    shipping_country: Optional[str] = "US"
    device_fingerprint: Optional[str] = "fp_default_99"
    device_type: Optional[str] = "desktop"
    is_new_device: Optional[bool] = False
    is_vpn_or_proxy: Optional[bool] = False
    distance_from_billing_km: Optional[float] = 0.0
    velocity_1h: Optional[int] = 1
    velocity_24h: Optional[int] = 1
    avg_user_amount_30d: Optional[float] = 85.0

class RuleDefinition(BaseModel):
    id: str
    name: str
    description: str
    condition_type: str  # AMOUNT_THRESHOLD, GEO_MISMATCH, VELOCITY_SPIKE, HIGH_RISK_MCC, NEW_DEVICE_HIGH_AMOUNT, VPN_PROXY_USAGE, IMPOSSIBLE_TRAVEL
    threshold_value: Optional[Any] = None
    action: str = "FLAG_REVIEW"  # FLAG_REVIEW, AUTO_DECLINE, STEP_UP_AUTH
    risk_weight: float = 25.0
    enabled: bool = True
    trigger_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class InvestigationAction(BaseModel):
    transaction_id: str
    action: str  # APPROVE, DECLINE, ESCALATE, ADD_NOTE
    analyst_id: str = "analyst_sarah"
    note: Optional[str] = None

class AttackSimulationRequest(BaseModel):
    attack_type: str  # card_testing, account_takeover, impossible_travel, botnet_surge, crypto_wash
    count: int = 15
    intensity: str = "HIGH"  # LOW, MEDIUM, HIGH

class AnalyticsSummary(BaseModel):
    total_screened: int
    total_flagged: int
    total_declined: int
    total_approved: int
    fraud_rate_pct: float
    total_loss_prevented_usd: float
    avg_scoring_latency_ms: float
    active_threat_level: str
    risk_distribution: Dict[str, int]
    top_triggered_rules: List[Dict[str, Any]]
    category_breakdown: List[Dict[str, Any]]
    geo_distribution: List[Dict[str, Any]]
    hourly_trends: List[Dict[str, Any]]
