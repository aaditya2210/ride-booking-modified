FROM python:3.11-slim

WORKDIR /app

COPY ride-matching-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ride-matching-service/ .
COPY proto/ /app/proto/
RUN python -m grpc_tools.protoc -I/app/proto --python_out=/app/proto --grpc_python_out=/app/proto /app/proto/ride.proto

RUN echo '#!/bin/bash\npython grpc_server.py &\nuvicorn main:app --host 0.0.0.0 --port 8003' > start.sh && chmod +x start.sh

EXPOSE 8003 50051

CMD ["./start.sh"]
