from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import json
import uuid
import os
import time
import logging
import grpc
import sys
sys.path.append('/app/proto')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ride Matching Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_HOST = os.getenv("REDIS_HOST", "ride-redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
DRIVER_SERVICE_GRPC = os.getenv("DRIVER_SERVICE_GRPC", "driver-service:50052")
PRICING_SERVICE_GRPC = os.getenv("PRICING_SERVICE_GRPC", "pricing-service:50053")


def get_redis():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def get_driver_channel():
    return grpc.insecure_channel(DRIVER_SERVICE_GRPC)


def get_pricing_channel():
    return grpc.insecure_channel(PRICING_SERVICE_GRPC)


class RideRequest(BaseModel):
    riderId: int
    pickup: str = "Current Location"
    dropoff: str = "Destination"
    ride_type: str = "standard"


@app.on_event("startup")
async def startup():
    time.sleep(3)
    r = get_redis()
    r.ping()
    logger.info("Ride matching service started successfully")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "ride-matching-service"}


@app.post("/ride/request")
def request_ride(request: RideRequest):
    import ride_pb2
    import ride_pb2_grpc

    r = get_redis()
    ride_id = f"ride-{str(uuid.uuid4())[:8]}"

    # ── VALIDATION 1: Check for available drivers via gRPC ──
    driver_id = None
    driver_name = None

    try:
        channel = get_driver_channel()
        stub = ride_pb2_grpc.DriverServiceStub(channel)
        response = stub.GetAvailableDrivers(
            ride_pb2.GetAvailableDriversRequest(limit=1),
            timeout=3
        )

        # ── VALIDATION 2: No available drivers → reject ──
        if not response.drivers:
            raise HTTPException(
                status_code=503,
                detail="No drivers available at the moment. Please try again shortly."
            )

        driver = response.drivers[0]
        driver_id = driver.driver_id
        driver_name = driver.name

        # Mark driver as busy
        assign_response = stub.AssignDriver(
            ride_pb2.AssignDriverRequest(ride_id=ride_id, driver_id=driver_id),
            timeout=3
        )
        if not assign_response.success:
            raise HTTPException(
                status_code=503,
                detail="Driver became unavailable. Please try again."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Driver service gRPC error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Driver service unavailable. Please try again shortly."
        )

    # Get price via gRPC
    price = 25.0
    try:
        channel = get_pricing_channel()
        stub = ride_pb2_grpc.PricingServiceStub(channel)
        price_response = stub.CalculatePrice(
            ride_pb2.PriceRequest(
                pickup=request.pickup,
                dropoff=request.dropoff,
                ride_type=request.ride_type
            ),
            timeout=3
        )
        price = price_response.total_price
    except Exception as e:
        logger.warning(f"Could not reach pricing service via gRPC: {e}")

    ride_data = {
        "ride_id": ride_id,
        "rider_id": request.riderId,
        "driver_id": driver_id,
        "driver_name": driver_name,
        "pickup": request.pickup,
        "dropoff": request.dropoff,
        "ride_type": request.ride_type,
        "status": "matched",
        "price": price,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    r.setex(f"ride:{ride_id}", 3600, json.dumps(ride_data))
    logger.info(f"Ride {ride_id} created for rider {request.riderId}, driver {driver_id}")

    return {
        "ride_id": ride_id,
        "status": "matched",
        "driver": {"id": driver_id, "name": driver_name},
        "price": price,
        "estimated_arrival": "5 minutes",
        "message": "Ride matched successfully"
    }


@app.get("/ride/{ride_id}")
def get_ride(ride_id: str):
    r = get_redis()
    data = r.get(f"ride:{ride_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Ride not found")
    return json.loads(data)


@app.put("/ride/{ride_id}/status")
def update_ride_status(ride_id: str, status: str):
    r = get_redis()
    data = r.get(f"ride:{ride_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Ride not found")
    ride = json.loads(data)
    ride["status"] = status
    ride["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    r.setex(f"ride:{ride_id}", 3600, json.dumps(ride))
    return {"message": "Status updated", "status": status}


@app.get("/rides")
def list_rides():
    r = get_redis()
    keys = r.keys("ride:*")
    rides = []
    for key in keys:
        data = r.get(key)
        if data:
            rides.append(json.loads(data))
    return {"rides": rides}


@app.get("/ride/{ride_id}/validate")
def validate_ride(ride_id: str, user_id: int = 0, amount: float = 0):
    """Internal endpoint for payment validation"""
    r = get_redis()
    data = r.get(f"ride:{ride_id}")
    if not data:
        return {"valid": False, "message": "Ride not found"}
    ride = json.loads(data)

    if user_id != 0 and ride["rider_id"] != user_id:
        return {"valid": False, "message": "User does not match ride"}

    if ride.get("status") in ("paid", "completed"):
        return {"valid": False, "message": f"Ride already {ride.get('status')}"}

    return {
        "valid": True,
        "message": "Ride is valid",
        "ride_id": ride_id,
        "price": ride.get("price", 0),
        "driver_id": ride.get("driver_id"),
    }
