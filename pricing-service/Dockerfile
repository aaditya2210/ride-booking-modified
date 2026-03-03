FROM python:3.11-slim

WORKDIR /app

COPY pricing-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pricing-service/ .
COPY proto/ /app/proto/
RUN python -m grpc_tools.protoc -I/app/proto --python_out=/app/proto --grpc_python_out=/app/proto /app/proto/ride.proto

RUN echo '#!/bin/bash\npython grpc_server.py &\nuvicorn main:app --host 0.0.0.0 --port 8006' > start.sh && chmod +x start.sh

EXPOSE 8006 50053

CMD ["./start.sh"]
