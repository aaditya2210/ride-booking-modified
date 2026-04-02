from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
import os
import time
import logging
import grpc
from concurrent import futures
import sys
sys.path.append('/app/proto')
from shared.observability import configure_observability

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Driver Service", version="1.0.0")
configure_observability(app, "driver-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://driver-db:27017/driverdb")


def get_db():
    client = MongoClient(MONGO_URI)
    return client.driverdb


class DriverCreate(BaseModel):
    name: str
    email: str
    phone: str
    vehicle: str
    license_plate: str


def serialize_driver(driver):
    driver["_id"] = str(driver["_id"])
    return driver


@app.on_event("startup")
async def startup():
    time.sleep(5)
    db = get_db()
    count = db.drivers.count_documents({})
    if count == 0:
        sample_drivers = [
            {
                "name": "David Kumar",
                "email": "david@example.com",
                "phone": "+1555000001",
                "vehicle": "Toyota Camry 2022",
                "license_plate": "ABC-1234",
                "rating": 4.8,
                "available": True,
                "total_rides": 247,
            },
            {
                "name": "Emma Rodriguez",
                "email": "emma@example.com",
                "phone": "+1555000002",
                "vehicle": "Honda Civic 2023",
                "license_plate": "XYZ-5678",
                "rating": 4.9,
                "available": True,
                "total_rides": 512,
            },
            {
                "name": "Frank Lee",
                "email": "frank@example.com",
                "phone": "+1555000003",
                "vehicle": "Ford Escape 2021",
                "license_plate": "DEF-9012",
                "rating": 4.7,
                "available": False,
                "total_rides": 183,
            },
        ]
        db.drivers.insert_many(sample_drivers)
    logger.info("Driver service started successfully")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "driver-service"}


@app.get("/drivers")
def get_drivers():
    db = get_db()
    drivers = [serialize_driver(d) for d in db.drivers.find()]
    return {"drivers": drivers}


@app.get("/drivers/available")
def get_available_drivers():
    db = get_db()
    drivers = [serialize_driver(d) for d in db.drivers.find({"available": True})]
    return {"drivers": drivers}


@app.get("/drivers/{driver_id}")
def get_driver(driver_id: str):
    db = get_db()
    try:
        driver = db.drivers.find_one({"_id": ObjectId(driver_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid driver ID")
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return serialize_driver(driver)


@app.post("/drivers", status_code=201)
def create_driver(driver: DriverCreate):
    db = get_db()
    doc = driver.dict()
    doc["rating"] = 5.0
    doc["available"] = True
    doc["total_rides"] = 0
    result = db.drivers.insert_one(doc)
    return {"id": str(result.inserted_id), "message": "Driver created successfully"}


@app.put("/drivers/{driver_id}/availability")
def update_availability(driver_id: str, available: bool):
    db = get_db()
    try:
        db.drivers.update_one(
            {"_id": ObjectId(driver_id)},
            {"$set": {"available": available}}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid driver ID")
    return {"message": "Availability updated"}


@app.get("/drivers/grpc/available")
def get_available_for_grpc():
    """Internal endpoint used by gRPC server"""
    db = get_db()
    drivers = [serialize_driver(d) for d in db.drivers.find({"available": True}).limit(5)]
    return {"drivers": drivers}
