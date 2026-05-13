FROM python:3.12-slim
WORKDIR /app

# Install deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bundle the prebuilt SQLite into the image. ~210 MB, well under Cloud Run's
# 32 GB image limit. The DB is read-only so this is safe.
COPY bcad.db /app/bcad.db
COPY comp_engine.py pdf_packet.py api.py /app/

ENV PORT=8080
ENV DB_PATH=/app/bcad.db
EXPOSE 8080

# Single uvicorn worker is fine — SQLite read concurrency handles this well
# and Cloud Run will scale by adding instances, not threads.
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
