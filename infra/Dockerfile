FROM python:3.12-slim
WORKDIR /work
COPY backend/requirements.txt /work/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend /work/backend
COPY web /work/web
COPY config /work/config
COPY scripts /work/scripts
RUN useradd -m -u 10001 swing && mkdir -p /work/data && chown -R swing:swing /work/data
USER swing
ENV SWING_DB_PATH=/work/data/swing.db SWING_DATA_MODE=demo SWING_HOST=0.0.0.0
EXPOSE 8000
CMD ["python","scripts/launch.py","--host","0.0.0.0","--port","8000"]
