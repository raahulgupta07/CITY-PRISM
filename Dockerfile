# Stage 1: build the screens (SvelteKit, single-page app).
FROM node:22-alpine AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY svelte.config.js vite.config.ts tsconfig.json ./
COPY src ./src
COPY static ./static
COPY shared ./shared
RUN npm run build

# Stage 2: one Python image serves the API and the built screens.
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/backend/data \
    FRONTEND_BUILD_DIR=/app/build
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /app/build /app/build
RUN useradd --create-home --uid 1000 prism \
    && mkdir -p /app/backend/data && chown -R prism:prism /app/backend/data
USER prism
VOLUME ["/app/backend/data"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/health').status==200 else 1)"
# One worker: SQLite works best with a single writer process.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--proxy-headers"]
