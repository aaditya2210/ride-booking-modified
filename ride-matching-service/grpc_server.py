import grpc
from concurrent import futures
import redis
import json
import os
import time
import sys
sys.path.append('/app/proto')

import ride_pb2
import ride_pb2_grpc
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "ride-redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


def get_redis():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


class RideServicer(ride_pb2_grpc.RideServiceServicer):
    def GetRide(self, request, context):
        r = get_redis()
        data = r.get(f"ride:{request.ride_id}")
        if not data:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Ride not found")
            return ride_pb2.RideResponse()

        ride = json.loads(data)
        return ride_pb2.RideResponse(
            ride_id=ride["ride_id"],
            rider_id=int(ride["rider_id"]),
            driver_id=str(ride.get("driver_id", "")),
            status=ride.get("status", "unknown"),
            price=float(ride.get("price", 0)),
            created_at=ride.get("created_at", "")
        )

    def ValidateRide(self, request, context):
        r = get_redis()
        data = r.get(f"ride:{request.ride_id}")

        # ── VALIDATION: Ride exists ──
        if not data:
            return ride_pb2.ValidateRideResponse(
                valid=False, message="Ride not found",
                ride_id=request.ride_id, price=0
            )

        ride = json.loads(data)

        # ── VALIDATION: User owns this ride ──
        if request.user_id != 0 and ride.get("rider_id") != request.user_id:
            return ride_pb2.ValidateRideResponse(
                valid=False,
                message="Unauthorized: this ride belongs to a different user",
                ride_id=request.ride_id,
                price=float(ride.get("price", 0))
            )

        # ── VALIDATION: Ride not already paid/completed ──
        if ride.get("status") in ("paid", "completed"):
            return ride_pb2.ValidateRideResponse(
                valid=False,
                message=f"Ride already {ride.get('status')}. Cannot process payment again.",
                ride_id=request.ride_id,
                price=float(ride.get("price", 0))
            )

        # ── VALIDATION: Ride must be in a payable state ──
        if ride.get("status") == "cancelled":
            return ride_pb2.ValidateRideResponse(
                valid=False,
                message="Ride has been cancelled. Cannot process payment.",
                ride_id=request.ride_id,
                price=float(ride.get("price", 0))
            )

        return ride_pb2.ValidateRideResponse(
            valid=True,
            message="Ride is valid for payment",
            ride_id=request.ride_id,
            price=float(ride.get("price", 0))
        )

    def UpdateRideStatus(self, request, context):
        r = get_redis()
        data = r.get(f"ride:{request.ride_id}")
        if not data:
            return ride_pb2.UpdateRideStatusResponse(success=False, message="Ride not found")

        ride = json.loads(data)
        ride["status"] = request.status
        ride["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        r.setex(f"ride:{request.ride_id}", 3600, json.dumps(ride))

        logger.info(f"Ride {request.ride_id} status updated to {request.status}")
        return ride_pb2.UpdateRideStatusResponse(success=True, message="Status updated")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    ride_pb2_grpc.add_RideServiceServicer_to_server(RideServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    logger.info("Ride Matching gRPC server started on port 50051")
    server.wait_for_termination()


if __name__ == '__main__':
    time.sleep(8)
    serve()
