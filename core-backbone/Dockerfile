FROM python:3.9-slim

WORKDIR /app

# Cài đặt thư viện cần thiết
RUN pip install --no-cache-dir paho-mqtt psycopg2-binary

# Copy mã nguồn
COPY mqtt_to_postgres_subscriber.py .

# Ép Python in log ra ngay lập tức
ENV PYTHONUNBUFFERED=1

CMD ["python", "mqtt_to_postgres_subscriber.py"]
