from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import mysql.connector
import os
import time
import logging
import grpc
import sys
sys.path.append('/app/proto')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Payment Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "payment-db"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "paymentdb"),
}

RIDE_SERVICE_GRPC = os.getenv("RIDE_SERVICE_GRPC", "ride-matching-service:50051")
DRIVER_SERVICE_GRPC = os.getenv("DRIVER_SERVICE_GRPC", "driver-service:50052")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8005")


def get_db():
    retries = 5
    for i in range(retries):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            return conn
        except Exception as e:
            if i < retries - 1:
                time.sleep(3)
            else:
                raise e


class PaymentCreate(BaseModel):
    rideId: str
    userId: int
    amount: float
    payment_method: str = "card"


@app.on_event("startup")
async def startup():
    time.sleep(8)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ride_id VARCHAR(100) NOT NULL,
            user_id INT NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            payment_method VARCHAR(50) DEFAULT 'card',
            status VARCHAR(50) DEFAULT 'pending',
            transaction_id VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_ride (ride_id)
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Payment service started successfully")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "payment-service"}


@app.post("/payments")
def create_payment(payment: PaymentCreate):
    import ride_pb2
    import ride_pb2_grpc
    import uuid

    # ── VALIDATION 1: Ride exists and user owns it (via gRPC) ──
    ride_price = payment.amount
    driver_id = None
    try:
        channel = grpc.insecure_channel(RIDE_SERVICE_GRPC)
        stub = ride_pb2_grpc.RideServiceStub(channel)
        response = stub.ValidateRide(
            ride_pb2.ValidateRideRequest(
                ride_id=payment.rideId,
                user_id=payment.userId,
                amount=payment.amount
            ),
            timeout=5
        )

        if not response.valid:
            # Surface the exact reason back to the frontend
            msg = response.message
            if "different user" in msg or "Unauthorized" in msg:
                raise HTTPException(status_code=403, detail=msg)
            elif "already paid" in msg or "already completed" in msg:
                raise HTTPException(status_code=400, detail=msg)
            elif "not found" in msg.lower():
                raise HTTPException(status_code=404, detail=msg)
            elif "cancelled" in msg:
                raise HTTPException(status_code=400, detail=msg)
            else:
                raise HTTPException(status_code=400, detail=msg)

        ride_price = response.price if response.price > 0 else payment.amount

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Could not validate ride via gRPC: {e}")
        # If gRPC is down, fall back — still do DB-level duplicate check below
        ride_price = payment.amount

    # ── VALIDATION 2: Duplicate payment check (DB-level) ──
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, status FROM payments WHERE ride_id = %s", (payment.rideId,))
    existing = cursor.fetchone()
    if existing:
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Payment already processed for ride {payment.rideId} (txn #{existing['id']})"
        )

    # ── Process payment ──
    transaction_id = f"txn-{str(uuid.uuid4())[:12]}"
    try:
        cursor.execute(
            """INSERT INTO payments (ride_id, user_id, amount, payment_method, status, transaction_id)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (payment.rideId, payment.userId, ride_price, payment.payment_method, "completed", transaction_id)
        )
        conn.commit()
        payment_id = cursor.lastrowid
    except mysql.connector.IntegrityError:
        # Race condition: duplicate ride_id caught by UNIQUE KEY
        conn.rollback()
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Payment already processed for this ride")
    finally:
        cursor.close()
        conn.close()

    # ── VALIDATION 3: Mark ride as paid (gRPC) ──
    try:
        channel = grpc.insecure_channel(RIDE_SERVICE_GRPC)
        stub = ride_pb2_grpc.RideServiceStub(channel)
        stub.UpdateRideStatus(
            ride_pb2.UpdateRideStatusRequest(ride_id=payment.rideId, status="paid"),
            timeout=3
        )
        logger.info(f"Ride {payment.rideId} marked as paid")
    except Exception as e:
        logger.warning(f"Could not update ride status: {e}")

    # ── VALIDATION 4: Free up the driver (gRPC) ──
    # Fetch driver_id from ride data so we can release the driver
    try:
        channel = grpc.insecure_channel(RIDE_SERVICE_GRPC)
        ride_stub = ride_pb2_grpc.RideServiceStub(channel)
        ride_data = ride_stub.GetRide(
            ride_pb2.GetRideRequest(ride_id=payment.rideId),
            timeout=3
        )
        driver_id = ride_data.driver_id
    except Exception as e:
        logger.warning(f"Could not fetch ride to get driver_id: {e}")

    if driver_id:
        try:
            driver_channel = grpc.insecure_channel(DRIVER_SERVICE_GRPC)
            driver_stub = ride_pb2_grpc.DriverServiceStub(driver_channel)
            release_resp = driver_stub.ReleaseDriver(
                ride_pb2.ReleaseDriverRequest(
                    driver_id=driver_id,
                    ride_id=payment.rideId
                ),
                timeout=3
            )
            if release_resp.success:
                logger.info(f"Driver {driver_id} released via gRPC after ride {payment.rideId}")
            else:
                logger.warning(f"Could not release driver {driver_id}: {release_resp.message}")
        except Exception as e:
            logger.warning(f"Could not free driver {driver_id} via gRPC: {e}")

    # ── Notify user ──
    try:
        import requests as req
        req.post(
            f"{NOTIFICATION_SERVICE_URL}/notify",
            json={
                "user_id": payment.userId,
                "ride_id": payment.rideId,
                "type": "payment_success",
                "message": f"Payment of ${ride_price:.2f} completed successfully! Transaction: {transaction_id}",
                "transaction_id": transaction_id
            },
            timeout=2
        )
    except Exception as e:
        logger.warning(f"Could not send notification: {e}")

    logger.info(f"Payment {transaction_id} processed for ride {payment.rideId} by user {payment.userId}")

    return {
        "payment_id": payment_id,
        "transaction_id": transaction_id,
        "status": "completed",
        "amount": ride_price,
        "ride_id": payment.rideId,
        "message": "Payment processed successfully. Driver is now available for new rides."
    }


@app.get("/payments")
def get_payments():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM payments ORDER BY created_at DESC")
    payments = cursor.fetchall()
    for p in payments:
        p["amount"] = float(p["amount"])
    cursor.close()
    conn.close()
    return {"payments": payments}


@app.get("/payments/{payment_id}")
def get_payment(payment_id: int):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM payments WHERE id = %s", (payment_id,))
    payment = cursor.fetchone()
    cursor.close()
    conn.close()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    payment["amount"] = float(payment["amount"])
    return payment


@app.get("/payments/user/{user_id}")
def get_user_payments(user_id: int):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM payments WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
    payments = cursor.fetchall()
    for p in payments:
        p["amount"] = float(p["amount"])
    cursor.close()
    conn.close()
    return {"payments": payments}
