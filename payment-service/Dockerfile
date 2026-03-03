FROM python:3.11-slim

WORKDIR /app

COPY payment-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY payment-service/ .
COPY proto/ /app/proto/
RUN python -m grpc_tools.protoc -I/app/proto --python_out=/app/proto --grpc_python_out=/app/proto /app/proto/ride.proto

EXPOSE 8004

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
