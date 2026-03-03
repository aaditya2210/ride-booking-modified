FROM python:3.11-slim

WORKDIR /app

COPY driver-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY driver-service/ .
COPY proto/ /app/proto/
RUN python -m grpc_tools.protoc -I/app/proto --python_out=/app/proto --grpc_python_out=/app/proto /app/proto/ride.proto

RUN chmod +x start.sh

EXPOSE 8002 50052

CMD ["./start.sh"]
