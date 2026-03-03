import grpc
from concurrent import futures
import time
import sys
import os
import random
sys.path.append('/app/proto')

import ride_pb2
import ride_pb2_grpc
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_PRICES = {
    "standard": 15.0,
    "premium": 25.0,
    "xl": 35.0,
    "economy": 10.0,
}


class PricingServicer(ride_pb2_grpc.PricingServiceServicer):
    def CalculatePrice(self, request, context):
        base = BASE_PRICES.get(request.ride_type, 15.0)
        
        hour = time.localtime().tm_hour
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            surge = round(random.uniform(1.2, 1.8), 1)
        else:
            surge = 1.0
        
        distance_factor = random.uniform(0.8, 2.5)
        total = round(base * surge * distance_factor, 2)
        
        return ride_pb2.PriceResponse(
            base_price=base,
            surge_multiplier=surge,
            total_price=total,
            currency="USD"
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    ride_pb2_grpc.add_PricingServiceServicer_to_server(PricingServicer(), server)
    server.add_insecure_port('[::]:50053')
    server.start()
    logger.info("Pricing gRPC server started on port 50053")
    server.wait_for_termination()


if __name__ == '__main__':
    time.sleep(5)
    serve()
