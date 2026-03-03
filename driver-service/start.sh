#!/bin/bash
# Start gRPC server in background
python grpc_server.py &
# Start FastAPI
uvicorn main:app --host 0.0.0.0 --port 8002
