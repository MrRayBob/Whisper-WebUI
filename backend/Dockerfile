ARG TORCH_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cu128

FROM debian:bookworm-slim AS builder

ARG TORCH_EXTRA_INDEX_URL

RUN apt-get update && \
    apt-get install -y curl git python3 python3-pip python3-venv && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* && \
    mkdir -p /Whisper-WebUI

WORKDIR /Whisper-WebUI

COPY backend/ backend/
COPY requirements.txt requirements.txt
COPY requirements-legacy.txt requirements-legacy.txt

RUN python3 -m venv venv && \
    . venv/bin/activate && \
    python3 -m pip install -U pip "setuptools<82" wheel && \
    python3 -m pip install -r backend/requirements-backend.txt --extra-index-url "$TORCH_EXTRA_INDEX_URL" && \
    python3 -m pip install --no-build-isolation -r requirements-legacy.txt


FROM debian:bookworm-slim AS runtime

RUN apt-get update && \
    apt-get install -y curl ffmpeg python3 && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

WORKDIR /Whisper-WebUI

COPY . .
COPY --from=builder /Whisper-WebUI/venv /Whisper-WebUI/venv

VOLUME [ "/Whisper-WebUI/models" ]
VOLUME [ "/Whisper-WebUI/outputs" ]
VOLUME [ "/Whisper-WebUI/backend" ]

ENV PATH="/Whisper-WebUI/venv/bin:$PATH"
ENV LD_LIBRARY_PATH=/Whisper-WebUI/venv/lib64/python3.11/site-packages/nvidia/cublas/lib:/Whisper-WebUI/venv/lib64/python3.11/site-packages/nvidia/cudnn/lib

ENTRYPOINT ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
