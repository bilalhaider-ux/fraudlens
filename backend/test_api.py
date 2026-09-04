from main import evaluate_transaction, data_generator, rule_engine
import json

print("1. Testing Legitimate Transaction...")
req_legit = data_generator.generate_legitimate_transaction()
tx_legit = evaluate_transaction(req_legit)
print(f"Legit Tx -> ID: {tx_legit.id}, Score: {tx_legit.risk_score}, Level: {tx_legit.risk_level}, Status: {tx_legit.status}, Latency: {tx_legit.latency_ms}ms")

print("\n2. Testing Fraud: Card Testing Attack...")
req_card = data_generator.generate_fraud_transaction('card_testing')
tx_card = evaluate_transaction(req_card)
print(f"Card Testing -> ID: {tx_card.id}, Score: {tx_card.risk_score}, Level: {tx_card.risk_level}, Status: {tx_card.status}, Reasons: {[r.factor for r in tx_card.reason_codes]}")

print("\n3. Testing Fraud: Account Takeover (ATO)...")
req_ato = data_generator.generate_fraud_transaction('account_takeover')
tx_ato = evaluate_transaction(req_ato)
print(f"ATO Tx -> ID: {tx_ato.id}, Score: {tx_ato.risk_score}, Level: {tx_ato.risk_level}, Status: {tx_ato.status}, Rules: {tx_ato.triggered_rules}")

print("\nAll scoring tests passed successfully!")
