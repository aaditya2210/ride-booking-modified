from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import json
import os
import time
import logging
import random
from shared.observability import configure_observability

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Pricing Service", version="1.0.0")
configure_observability(app, "pricing-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_HOST = os.getenv("REDIS_HOST", "pricing-redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


def get_redis():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


BASE_PRICES = {
    "standard": 15.0,
    "premium": 25.0,
    "xl": 35.0,
    "economy": 10.0,
}


def calculate_surge():
    hour = time.localtime().tm_hour
    if 7 <= hour <= 9 or 17 <= hour <= 19:
        return round(random.uniform(1.2, 1.8), 1)
    return 1.0


def calculate_total_price(ride_type: str, pickup: str, dropoff: str) -> dict:
    base = BASE_PRICES.get(ride_type, 15.0)
    surge = calculate_surge()
    distance_factor = random.uniform(0.8, 2.5)
    total = round(base * surge * distance_factor, 2)
    return {
        "base_price": base,
        "surge_multiplier": surge,
        "total_price": total,
        "currency": "USD"
    }


class PriceRequest(BaseModel):
    pickup: str = "Current Location"
    dropoff: str = "Destination"
    ride_type: str = "standard"


@app.on_event("startup")
async def startup():
    time.sleep(3)
    r = get_redis()
    r.set("pricing:surge_multiplier", "1.0")
    r.set("pricing:base_standard", "15.0")
    r.set("pricing:base_premium", "25.0")
    r.set("pricing:base_xl", "35.0")
    r.set("pricing:base_economy", "10.0")
    logger.info("Pricing service started successfully")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "pricing-service"}


@app.post("/pricing/calculate")
def calculate_price(request: PriceRequest):
    r = get_redis()
    cache_key = f"price:{request.ride_type}:{hash(request.pickup + request.dropoff)}"
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)
    
    result = calculate_total_price(request.ride_type, request.pickup, request.dropoff)
    r.setex(cache_key, 30, json.dumps(result))
    return result


@app.get("/pricing/surge")
def get_surge():
    r = get_redis()
    surge = float(r.get("pricing:surge_multiplier") or "1.0")
    return {"surge_multiplier": surge, "status": "normal" if surge <= 1.0 else "surge"}


@app.get("/pricing/rates")
def get_rates():
    r = get_redis()
    return {
        "rates": {
            ride_type: {
                "base_price": BASE_PRICES[ride_type],
                "surge_multiplier": calculate_surge(),
                "currency": "USD"
            }
            for ride_type in BASE_PRICES
        }
    }
