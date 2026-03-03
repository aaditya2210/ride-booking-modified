import grpc
from concurrent import futures
import time
import sys
import os
sys.path.append('/app/proto')

import ride_pb2
import ride_pb2_grpc
from pymongo import MongoClient
from bson import ObjectId
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://driver-db:27017/driverdb")


def get_db():
    client = MongoClient(MONGO_URI)
    return client.driverdb


class DriverServicer(ride_pb2_grpc.DriverServiceServicer):
    def GetAvailableDrivers(self, request, context):
        db = get_db()
        limit = request.limit if request.limit > 0 else 5
        drivers_docs = list(db.drivers.find({"available": True}).limit(limit))

        drivers = []
        for d in drivers_docs:
            drivers.append(ride_pb2.Driver(
                driver_id=str(d["_id"]),
                name=d.get("name", ""),
                vehicle=d.get("vehicle", ""),
                rating=float(d.get("rating", 5.0)),
                available=d.get("available", True)
            ))

        logger.info(f"GetAvailableDrivers: returning {len(drivers)} drivers")
        return ride_pb2.GetAvailableDriversResponse(drivers=drivers)

    def AssignDriver(self, request, context):
        db = get_db()
        try:
            # Only assign if still available (prevents race conditions)
            result = db.drivers.update_one(
                {"_id": ObjectId(request.driver_id), "available": True},
                {"$set": {"available": False, "current_ride": request.ride_id}}
            )
            if result.modified_count > 0:
                logger.info(f"Driver {request.driver_id} assigned to ride {request.ride_id}")
                return ride_pb2.AssignDriverResponse(success=True, message="Driver assigned successfully")
            return ride_pb2.AssignDriverResponse(
                success=False,
                message="Driver not found or no longer available"
            )
        except Exception as e:
            logger.error(f"AssignDriver error: {e}")
            return ride_pb2.AssignDriverResponse(success=False, message=str(e))

    def ReleaseDriver(self, request, context):
        """Called after payment to free driver for new rides"""
        db = get_db()
        try:
            result = db.drivers.update_one(
                {"_id": ObjectId(request.driver_id)},
                {
                    "$set": {"available": True, "current_ride": None},
                    "$inc": {"total_rides": 1}
                }
            )
            if result.modified_count > 0:
                logger.info(f"Driver {request.driver_id} released, ride {request.ride_id} completed")
                return ride_pb2.ReleaseDriverResponse(success=True, message="Driver released successfully")
            return ride_pb2.ReleaseDriverResponse(success=False, message="Driver not found")
        except Exception as e:
            logger.error(f"ReleaseDriver error: {e}")
            return ride_pb2.ReleaseDriverResponse(success=False, message=str(e))


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    ride_pb2_grpc.add_DriverServiceServicer_to_server(DriverServicer(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    logger.info("Driver gRPC server started on port 50052")
    server.wait_for_termination()


if __name__ == '__main__':
    time.sleep(8)
    serve()
