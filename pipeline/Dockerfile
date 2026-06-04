# LAYER 1: Base image và thư viện hệ thống (Ít thay đổi nhất)
FROM nvidia/cuda:11.8.0-base-ubuntu22.04

RUN sed -i 's/archive.ubuntu.com/mirrors.edge.kernel.org/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.edge.kernel.org/g' /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip python3-dev libgl1 libglib2.0-0 libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip3 install --no-cache-dir --upgrade pip

# LAYER 2: Cài đặt Torch (Nặng nhất, cực kỳ ít thay đổi)
# Nếu bạn không sửa dòng này, Docker sẽ KHÔNG BAO GIỜ tải lại Torch
RUN pip3 install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu118

# LAYER 3: Các thư viện Python khác (Ít thay đổi)
RUN pip3 install --no-cache-dir \
    ultralytics celery[redis] minio requests psycopg2-binary Pillow paho-mqtt \
    "nvidia-modelopt[torch]"

# LAYER 4: Copy Code (Hay thay đổi nhất - Để ở cuối cùng)
# Chỉ khi bạn sửa file trong folder pipeline, Docker mới chạy lại từ đây
COPY . /app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["celery", "-A", "pipeline.celery_app", "worker", "--loglevel=info"]
