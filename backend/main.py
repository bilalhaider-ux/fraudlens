import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import (
    Transaction,
    TransactionEvaluationRequest,
    RiskLevel,
    TransactionStatus,
    RuleDefinition,
    InvestigationAction,
    AttackSimulationRequest,
    AnalyticsSummary,
    ReasonCode
)
from ml_engine import MLEngine
from rule_engine import RuleEngine
from data_generator import SyntheticDataGenerator
from ml_adapter import ml_pipeline_adapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fraud_lens")

app = FastAPI(
    title="FraudLens Intelligence API",
    description="Real-Time ML Fraud Detection, Anomaly Screening, and Rule Enforcement Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core State & Services
ml_engine = MLEngine()
rule_engine = RuleEngine()
data_generator = SyntheticDataGenerator()

transactions_db: List[Transaction] = []
MAX_TX_HISTORY = 1000

# Stream simulation state
stream_running = True
stream_interval_sec = 2.5
active_threat_level = "ELEVATED"

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_transaction(self, tx: Transaction):
        data = tx.model_dump()
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json({"type": "NEW_TRANSACTION", "payload": data})
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

    async def broadcast_metrics(self, metrics: Dict[str, Any]):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json({"type": "METRICS_UPDATE", "payload": metrics})
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()

def evaluate_transaction(req: TransactionEvaluationRequest) -> Transaction:
    start_time = time.perf_counter()
    
    # 1. Run Machine Learning Model & Isolation Forest
    ml_prob, anomaly_score, xai_reasons = ml_engine.evaluate(req)
    
    # 2. Run Dynamic Rule Engine
    triggered_rules, rule_reasons, rule_boost, enforced_action = rule_engine.evaluate(req)
    
    # 3. Combine scores into hybrid Risk Score (0..100)
    # ML prob gives 0..55, rule boost gives 0..65, anomaly gives 0..25
    base_ml_score = ml_prob * 55.0
    base_anomaly_score = anomaly_score * 20.0
    combined_score = base_ml_score + rule_boost + base_anomaly_score
    
    # Normalize score
    final_score = round(min(100.0, max(0.0, combined_score)), 1)
    
    # Determine Risk Level
    if final_score >= 88.0 or enforced_action == "AUTO_DECLINE":
        risk_level = RiskLevel.CRITICAL
    elif final_score >= 68.0:
        risk_level = RiskLevel.HIGH
    elif final_score >= 38.0:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW

    # Determine Decision Status
    if enforced_action == "AUTO_DECLINE" or risk_level == RiskLevel.CRITICAL:
        status = TransactionStatus.DECLINED
    elif risk_level == RiskLevel.HIGH or enforced_action == "FLAG_REVIEW":
        status = TransactionStatus.UNDER_REVIEW
    elif risk_level == RiskLevel.MEDIUM:
        status = TransactionStatus.UNDER_REVIEW
    else:
        status = TransactionStatus.APPROVED

    # Consolidate Reason Codes (deduplicating by factor name)
    seen_factors = set()
    all_reasons: List[ReasonCode] = []
    for r in rule_reasons + xai_reasons:
        if r.factor not in seen_factors:
            seen_factors.add(r.factor)
            all_reasons.append(r)

    latency = round((time.perf_counter() - start_time) * 1000, 2)
    
    tx = Transaction(
        id=f"tx_{uuid.uuid4().hex[:8]}",
        timestamp=datetime.utcnow().isoformat() + "Z",
        user_id=req.user_id,
        amount=req.amount,
        currency=req.currency,
        merchant=req.merchant,
        merchant_category=req.merchant_category,
        card_type=req.card_type,
        card_bin=req.card_bin or "411111",
        card_last4=req.card_last4 or "9824",
        ip_address=req.ip_address or "198.51.100.1",
        ip_country=req.ip_country or "US",
        billing_country=req.billing_country or "US",
        shipping_country=req.shipping_country or "US",
        device_fingerprint=req.device_fingerprint or "fp_default",
        device_type=req.device_type or "desktop",
        is_new_device=req.is_new_device or False,
        is_vpn_or_proxy=req.is_vpn_or_proxy or False,
        distance_from_billing_km=req.distance_from_billing_km or 0.0,
        velocity_1h=req.velocity_1h or 1,
        velocity_24h=req.velocity_24h or 1,
        avg_user_amount_30d=req.avg_user_amount_30d or 85.0,
        risk_score=final_score,
        risk_level=risk_level,
        status=status,
        ml_probability=round(ml_prob, 4),
        rule_score_boost=round(rule_boost, 1),
        triggered_rules=triggered_rules,
        reason_codes=all_reasons,
        notes=[],
        latency_ms=latency
    )
    
    transactions_db.insert(0, tx)
    if len(transactions_db) > MAX_TX_HISTORY:
        transactions_db.pop()
        
    return tx

# Pre-populate historical transactions on startup
def seed_initial_transactions():
    if len(transactions_db) == 0:
        logger.info("Seeding initial historical transactions...")
        for _ in range(35):
            req = data_generator.generate_legitimate_transaction()
            evaluate_transaction(req)
        # Add a few fraud cases
        for attack in ["account_takeover", "card_testing", "crypto_wash"]:
            req = data_generator.generate_fraud_transaction(attack)
            evaluate_transaction(req)

@app.on_event("startup")
async def startup_event():
    seed_initial_transactions()
    asyncio.create_task(background_stream_loop())

async def background_stream_loop():
    """Background simulator generating realistic transactions and pushing over WebSocket."""
    global stream_running, stream_interval_sec
    while True:
        try:
            if stream_running and len(manager.active_connections) > 0:
                # 88% chance legit, 12% chance random fraud
                if random.random() < 0.88:
                    req = data_generator.generate_legitimate_transaction()
                else:
                    req = data_generator.generate_fraud_transaction()
                
                tx = evaluate_transaction(req)
                await manager.broadcast_transaction(tx)
        except Exception as e:
            logger.error(f"Error in stream loop: {e}")
            
        await asyncio.sleep(stream_interval_sec)

import random

# ================= REST API ROUTES =================

@app.get("/api/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat(), "transactions_count": len(transactions_db)}

@app.post("/api/evaluate", response_model=Transaction)
def screen_transaction(req: TransactionEvaluationRequest):
    """Evaluates a raw transaction payload and returns full risk scoring result."""
    return evaluate_transaction(req)

@app.get("/api/transactions", response_model=List[Transaction])
def get_transactions(
    limit: int = 50,
    offset: int = 0,
    risk_level: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
):
    filtered = transactions_db
    if risk_level and risk_level != "ALL":
        filtered = [t for t in filtered if t.risk_level == risk_level]
    if status and status != "ALL":
        filtered = [t for t in filtered if t.status == status]
    if search:
        s = search.lower()
        filtered = [
            t for t in filtered
            if s in t.id.lower() or s in t.user_id.lower() or s in t.merchant.lower() or s in t.ip_address or s in t.card_last4
        ]
    return filtered[offset:offset + limit]

@app.get("/api/transactions/{tx_id}", response_model=Transaction)
def get_transaction_detail(tx_id: str):
    for tx in transactions_db:
        if tx.id == tx_id:
            return tx
    raise HTTPException(status_code=404, detail="Transaction not found")

@app.post("/api/transactions/{tx_id}/action", response_model=Transaction)
def perform_investigation_action(tx_id: str, action_req: InvestigationAction):
    for tx in transactions_db:
        if tx.id == tx_id:
            if action_req.action == "APPROVE":
                tx.status = TransactionStatus.MANUALLY_APPROVED
            elif action_req.action == "BLOCK":
                tx.status = TransactionStatus.MANUALLY_BLOCKED
            elif action_req.action == "ESCALATE":
                tx.status = TransactionStatus.UNDER_REVIEW
            
            note_entry = {
                "analyst": action_req.analyst_id,
                "action": action_req.action,
                "note": action_req.note or f"Action {action_req.action} applied by {action_req.analyst_id}",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            tx.notes.append(note_entry)
            return tx
            
    raise HTTPException(status_code=404, detail="Transaction not found")

@app.get("/api/rules", response_model=List[RuleDefinition])
def list_rules():
    return rule_engine.get_all_rules()

@app.post("/api/rules", response_model=RuleDefinition)
def create_rule(rule: RuleDefinition):
    if not rule.id:
        rule.id = f"RULE_{uuid.uuid4().hex[:4].upper()}"
    return rule_engine.add_rule(rule)

@app.patch("/api/rules/{rule_id}")
def toggle_rule(rule_id: str, updates: Dict[str, Any]):
    try:
        updated = rule_engine.update_rule(rule_id, updates)
        return updated
    except KeyError:
        raise HTTPException(status_code=404, detail="Rule not found")

@app.delete("/api/rules/{rule_id}")
def delete_rule(rule_id: str):
    success = rule_engine.delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"success": True, "deleted_rule_id": rule_id}

@app.get("/api/metrics", response_model=AnalyticsSummary)
def get_analytics():
    total = len(transactions_db)
    if total == 0:
        return AnalyticsSummary(
            total_screened=0, total_flagged=0, total_declined=0, total_approved=0,
            fraud_rate_pct=0.0, total_loss_prevented_usd=0.0, avg_scoring_latency_ms=1.1,
            active_threat_level="NOMINAL", risk_distribution={"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
            top_triggered_rules=[], category_breakdown=[], geo_distribution=[], hourly_trends=[]
        )

    flagged = sum(1 for t in transactions_db if t.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] or t.status == TransactionStatus.UNDER_REVIEW)
    declined = sum(1 for t in transactions_db if t.status in [TransactionStatus.DECLINED, TransactionStatus.MANUALLY_BLOCKED])
    approved = sum(1 for t in transactions_db if t.status in [TransactionStatus.APPROVED, TransactionStatus.MANUALLY_APPROVED])
    
    fraud_rate = round(((flagged + declined) / total) * 100, 2)
    prevented_loss = round(sum(t.amount for t in transactions_db if t.status in [TransactionStatus.DECLINED, TransactionStatus.MANUALLY_BLOCKED]), 2)
    avg_lat = round(sum(t.latency_ms for t in transactions_db) / total, 2)
    
    # Risk counts
    dist = {
        "LOW": sum(1 for t in transactions_db if t.risk_level == RiskLevel.LOW),
        "MEDIUM": sum(1 for t in transactions_db if t.risk_level == RiskLevel.MEDIUM),
        "HIGH": sum(1 for t in transactions_db if t.risk_level == RiskLevel.HIGH),
        "CRITICAL": sum(1 for t in transactions_db if t.risk_level == RiskLevel.CRITICAL),
    }

    # Category breakdown
    cats: Dict[str, Dict[str, Any]] = {}
    for t in transactions_db:
        c = t.merchant_category
        if c not in cats:
            cats[c] = {"category": c, "total_count": 0, "fraud_count": 0, "volume_usd": 0.0}
        cats[c]["total_count"] += 1
        cats[c]["volume_usd"] += t.amount
        if t.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            cats[c]["fraud_count"] += 1

    cat_list = sorted(list(cats.values()), key=lambda x: x["fraud_count"], reverse=True)

    # Geo distribution
    geos: Dict[str, int] = {}
    for t in transactions_db:
        g = t.ip_country
        geos[g] = geos.get(g, 0) + 1
    geo_list = [{"country": k, "count": v} for k, v in sorted(geos.items(), key=lambda x: x[1], reverse=True)]

    # Top triggered rules
    rules_stats = [
        {"id": r.id, "name": r.name, "count": r.trigger_count, "action": r.action}
        for r in sorted(rule_engine.get_all_rules(), key=lambda x: x.trigger_count, reverse=True)
    ]

    # Hourly mock trends
    hourly_trends = [
        {"hour": "00:00", "legit": 24, "fraud": 3},
        {"hour": "04:00", "legit": 12, "fraud": 5},
        {"hour": "08:00", "legit": 45, "fraud": 2},
        {"hour": "12:00", "legit": 88, "fraud": 6},
        {"hour": "16:00", "legit": 105, "fraud": 9},
        {"hour": "20:00", "legit": 76, "fraud": 7},
    ]

    threat_level = "CRITICAL" if fraud_rate > 25.0 else ("ELEVATED" if fraud_rate > 12.0 else "NOMINAL")

    return AnalyticsSummary(
        total_screened=total,
        total_flagged=flagged,
        total_declined=declined,
        total_approved=approved,
        fraud_rate_pct=fraud_rate,
        total_loss_prevented_usd=prevented_loss,
        avg_scoring_latency_ms=avg_lat,
        active_threat_level=threat_level,
        risk_distribution=dist,
        top_triggered_rules=rules_stats,
        category_breakdown=cat_list,
        geo_distribution=geo_list,
        hourly_trends=hourly_trends
    )

@app.post("/api/simulate/attack")
async def trigger_attack_simulation(sim: AttackSimulationRequest):
    """Generates an attack burst and evaluates each transaction in real-time."""
    batch = data_generator.generate_attack_batch(sim.attack_type, count=sim.count)
    results = []
    for req in batch:
        tx = evaluate_transaction(req)
        await manager.broadcast_transaction(tx)
        results.append(tx)
    return {
        "success": True,
        "attack_type": sim.attack_type,
        "count_generated": len(results),
        "flagged_count": sum(1 for t in results if t.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]),
        "transactions": results[:5]
    }

class StreamControlRequest(BaseModel):
    running: Optional[bool] = None
    interval_sec: Optional[float] = None

@app.post("/api/stream/control")
def control_stream(ctrl: StreamControlRequest):
    global stream_running, stream_interval_sec
    if ctrl.running is not None:
        stream_running = ctrl.running
    if ctrl.interval_sec is not None:
        stream_interval_sec = max(0.2, min(10.0, ctrl.interval_sec))
# ================= ML PIPELINE ARTIFACT ROUTES =================
@app.get("/api/ml/status")
def get_ml_artifacts_status():
    """Returns the discovery and loading status of dropped ML artifacts."""
    return ml_pipeline_adapter.get_artifact_status()

@app.get("/api/ml/graph")
def get_ml_graph_data():
    """Returns the pre-clustered subgraph or network topology data."""
    return ml_pipeline_adapter.get_graph_data()

@app.get("/api/ml/shap")
def get_ml_shap_data():
    """Returns global and local SHAP feature importance attributions."""
    return ml_pipeline_adapter.get_shap_importance()

@app.get("/api/ml/drift")
def get_ml_drift_data():
    """Returns the Time-Step 43 temporal and covariate drift monitor metrics."""
    return ml_pipeline_adapter.get_drift_monitor()

@app.get("/api/ml/alerts")
def get_ml_alerts_data():
    """Returns flagged high-risk alerts queue from alerts.json."""
    return ml_pipeline_adapter.get_alerts_data()

# ================= WEBSOCKET ROUTE =================

@app.websocket("/ws/transactions")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Can accept client commands e.g. ping
            try:
                msg = json.loads(data)
                if msg.get("action") == "PING":
                    await websocket.send_json({"type": "PONG", "timestamp": time.time()})
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
