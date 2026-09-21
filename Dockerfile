# CleanProof on Hugging Face Spaces (Docker SDK): one container serves the API, the built
# frontend and the local CLIP model at a single public https address.

# 1) Build the frontend
FROM node:20-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# API calls stay on the same address as the page
RUN rm -f .env && npm run build

# 2) Backend + AI model
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface \
    FRONTEND_DIST=/app/frontend_dist
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r backend/requirements.txt

# Download CLIP at build time so the app starts fast and needs no download at runtime
RUN python -c "from transformers import CLIPModel, CLIPProcessor; m='openai/clip-vit-base-patch32'; CLIPModel.from_pretrained(m); CLIPProcessor.from_pretrained(m)"

COPY backend/ backend/
COPY scripts/ scripts/
COPY data/demo/ data/demo/
COPY --from=frontend /build/dist /app/frontend_dist

# Spaces run the container as user 1000
RUN mkdir -p data/images && chown -R 1000:1000 /app
USER 1000

EXPOSE 7860
# DATA_DIR holds the database and uploaded photos. On Azure App Service it is set to /home/data,
# which survives restarts. Demo data is created only when there is no database yet.
ENV DATA_DIR=/app/data/cloud
CMD ["sh", "-c", "mkdir -p $DATA_DIR && export DATABASE_URL=sqlite:///$DATA_DIR/cleanproof.db IMAGES_DIR=$DATA_DIR/images && { [ -f $DATA_DIR/cleanproof.db ] || python scripts/reset_demo.py; } && python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 7860"]
