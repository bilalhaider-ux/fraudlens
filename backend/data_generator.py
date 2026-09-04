import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
from models import TransactionEvaluationRequest

MERCHANTS_LEGIT = [
    ("Amazon.com", "retail", [15.0, 45.0, 89.0, 140.0, 230.0]),
    ("Apple Store", "electronics", [29.0, 99.0, 199.0, 799.0]),
    ("Starbucks Coffee", "food_dining", [4.50, 7.80, 12.50, 18.00]),
    ("Uber Technologies", "travel", [14.20, 22.50, 38.00, 65.00]),
    ("Netflix Premium", "entertainment", [15.99, 22.99]),
    ("Target Corp", "retail", [34.0, 68.50, 112.0, 185.0]),
    ("Whole Foods Market", "grocery", [45.0, 88.0, 135.0, 210.0]),
    ("Steam Games", "gaming", [19.99, 49.99, 69.99]),
    ("Nike Store Online", "retail", [85.0, 120.0, 160.0, 240.0]),
    ("Spotify US", "entertainment", [10.99, 16.99])
]

MERCHANTS_FRAUD_TARGETS = [
    ("CryptoEx Global", "crypto", [1200.0, 2400.0, 3800.0, 4950.0]),
    ("Binance Offshore", "crypto", [850.0, 1900.0, 3200.0, 4800.0]),
    ("Rolex Boutique NYC", "luxury", [3400.0, 4800.0, 5600.0]),
    ("Western Union Transfer", "money_transfer", [950.0, 1800.0, 2900.0]),
    ("Gucci Direct", "luxury", [1450.0, 2800.0, 4200.0]),
    ("BestBuy Electronics", "electronics", [899.0, 1499.0, 2499.0]),
    ("CardTest Digital Services", "gaming", [0.99, 1.49, 2.99, 4.99])
]

COUNTRIES = [
    ("US", "198.51.100.", 0),
    ("US", "172.56.21.", 50),
    ("US", "24.180.45.", 120),
    ("CA", "142.250.80.", 450),
    ("GB", "185.86.151.", 5500),
    ("DE", "194.25.0.", 6200),
    ("FR", "195.154.122.", 5800),
    ("NL", "84.17.45.", 6000),
    ("JP", "133.242.18.", 10800),
    ("SG", "103.28.248.", 14000),
    ("RU", "185.220.101.", 7500),
    ("NG", "197.210.45.", 9800),
    ("BR", "177.18.230.", 7600)
]

USER_PROFILES = [
    {"user_id": f"usr_{1000 + i}", "home_country": "US", "avg_spend": random.uniform(50, 140), "device": f"fp_dev_{1000+i}"}
    for i in range(50)
]

class SyntheticDataGenerator:
    def __init__(self):
        self.user_history: Dict[str, List[datetime]] = {}

    def generate_legitimate_transaction(self) -> TransactionEvaluationRequest:
        user = random.choice(USER_PROFILES)
        merchant, category, amounts = random.choice(MERCHANTS_LEGIT)
        amount = round(random.choice(amounts) * random.uniform(0.85, 1.25), 2)
        
        # IP & Country consistent with user
        ip_country = user["home_country"]
        distance_km = round(random.uniform(0, 80), 1)
        ip = f"198.51.{random.randint(10, 250)}.{random.randint(2, 254)}"
        
        # Low velocity
        velocity_1h = random.choice([1, 1, 1, 2])
        velocity_24h = velocity_1h + random.choice([0, 1, 2])

        return TransactionEvaluationRequest(
            user_id=user["user_id"],
            amount=amount,
            currency="USD",
            merchant=merchant,
            merchant_category=category,
            card_type=random.choice(["credit", "credit", "debit"]),
            card_bin=random.choice(["453201", "542418", "411111", "378282"]),
            card_last4=str(random.randint(1000, 9999)),
            ip_address=ip,
            ip_country=ip_country,
            billing_country=user["home_country"],
            shipping_country=user["home_country"],
            device_fingerprint=user["device"],
            device_type=random.choice(["desktop", "mobile", "mobile"]),
            is_new_device=False,
            is_vpn_or_proxy=False,
            distance_from_billing_km=distance_km,
            velocity_1h=velocity_1h,
            velocity_24h=velocity_24h,
            avg_user_amount_30d=round(user["avg_spend"], 2)
        )

    def generate_fraud_transaction(self, attack_type: str = "random") -> TransactionEvaluationRequest:
        user = random.choice(USER_PROFILES)
        
        if attack_type == "random":
            attack_type = random.choice(["card_testing", "account_takeover", "impossible_travel", "crypto_wash", "botnet_surge"])

        if attack_type == "card_testing":
            # Rapid micro transactions
            amount = round(random.uniform(0.80, 4.99), 2)
            merchant, category, _ = MERCHANTS_FRAUD_TARGETS[-1] # CardTest / gaming
            return TransactionEvaluationRequest(
                user_id=user["user_id"],
                amount=amount,
                currency="USD",
                merchant=merchant,
                merchant_category=category,
                card_type="credit",
                card_bin="411111",
                card_last4=str(random.randint(1000, 9999)),
                ip_address=f"185.220.101.{random.randint(10, 250)}",
                ip_country="RU",
                billing_country="US",
                shipping_country="US",
                device_fingerprint=f"fp_bot_worker_{random.randint(1, 10)}",
                device_type="bot_emulator",
                is_new_device=True,
                is_vpn_or_proxy=True,
                distance_from_billing_km=7600.0,
                velocity_1h=random.randint(8, 22),
                velocity_24h=random.randint(15, 45),
                avg_user_amount_30d=round(user["avg_spend"], 2)
            )

        elif attack_type == "account_takeover":
            # Sudden high amount from new device & distant geo
            amount = round(random.uniform(2200.0, 4850.0), 2)
            merchant, category, _ = random.choice(MERCHANTS_FRAUD_TARGETS[:5])
            foreign_country, ip_prefix, dist = random.choice(COUNTRIES[6:])
            return TransactionEvaluationRequest(
                user_id=user["user_id"],
                amount=amount,
                currency="USD",
                merchant=merchant,
                merchant_category=category,
                card_type="credit",
                card_bin="542418",
                card_last4=str(random.randint(1000, 9999)),
                ip_address=f"{ip_prefix}{random.randint(2, 254)}",
                ip_country=foreign_country,
                billing_country="US",
                shipping_country=foreign_country,
                device_fingerprint=f"fp_hacked_new_{random.randint(100, 999)}",
                device_type="desktop",
                is_new_device=True,
                is_vpn_or_proxy=random.choice([True, False]),
                distance_from_billing_km=float(dist),
                velocity_1h=random.randint(2, 4),
                velocity_24h=random.randint(3, 7),
                avg_user_amount_30d=round(user["avg_spend"], 2)
            )

        elif attack_type == "impossible_travel":
            amount = round(random.uniform(350.0, 1800.0), 2)
            merchant = "Luxury Hub Paris"
            category = "luxury"
            return TransactionEvaluationRequest(
                user_id=user["user_id"],
                amount=amount,
                currency="USD",
                merchant=merchant,
                merchant_category=category,
                card_type="credit",
                card_bin="378282",
                card_last4=str(random.randint(1000, 9999)),
                ip_address=f"195.154.122.{random.randint(10, 250)}",
                ip_country="FR",
                billing_country="US",
                shipping_country="FR",
                device_fingerprint=f"fp_spoofed_{random.randint(50, 99)}",
                device_type="mobile",
                is_new_device=True,
                is_vpn_or_proxy=False,
                distance_from_billing_km=5800.0,
                velocity_1h=random.randint(4, 6),
                velocity_24h=random.randint(5, 9),
                avg_user_amount_30d=round(user["avg_spend"], 2)
            )

        elif attack_type == "crypto_wash":
            amount = round(random.uniform(1800.0, 4900.0), 2)
            merchant = "CryptoEx Global"
            category = "crypto"
            return TransactionEvaluationRequest(
                user_id=user["user_id"],
                amount=amount,
                currency="USD",
                merchant=merchant,
                merchant_category=category,
                card_type="debit",
                card_bin="453201",
                card_last4=str(random.randint(1000, 9999)),
                ip_address=f"185.86.151.{random.randint(10, 250)}",
                ip_country="GB",
                billing_country="US",
                shipping_country="US",
                device_fingerprint=f"fp_tor_exit_{random.randint(1, 30)}",
                device_type="desktop",
                is_new_device=True,
                is_vpn_or_proxy=True,
                distance_from_billing_km=5500.0,
                velocity_1h=random.randint(5, 12),
                velocity_24h=random.randint(10, 25),
                avg_user_amount_30d=round(user["avg_spend"], 2)
            )

        else: # botnet_surge
            amount = round(random.uniform(49.0, 299.0), 2)
            return TransactionEvaluationRequest(
                user_id=f"usr_bot_{random.randint(10, 99)}",
                amount=amount,
                currency="USD",
                merchant="Apple Store Online",
                merchant_category="electronics",
                card_type="credit",
                card_bin="411111",
                card_last4=str(random.randint(1000, 9999)),
                ip_address=f"103.28.248.{random.randint(10, 250)}",
                ip_country="SG",
                billing_country="US",
                shipping_country="SG",
                device_fingerprint="fp_bot_cluster_v3",
                device_type="bot_emulator",
                is_new_device=True,
                is_vpn_or_proxy=True,
                distance_from_billing_km=14000.0,
                velocity_1h=random.randint(10, 30),
                velocity_24h=random.randint(20, 60),
                avg_user_amount_30d=45.0
            )

    def generate_attack_batch(self, attack_type: str, count: int = 10) -> List[TransactionEvaluationRequest]:
        return [self.generate_fraud_transaction(attack_type) for _ in range(count)]
