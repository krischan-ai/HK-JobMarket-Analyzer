FROM node:20-alpine AS web-builder
WORKDIR /app/web
COPY web/package.json web/package-lock.json* ./
RUN npm install 2>/dev/null || npm install --legacy-peer-deps
COPY web/ ./
RUN npm run build 2>/dev/null || echo "Vue build skipped (run npm install && npm run build locally)"

FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends nginx && rm -rf /var/lib/apt/lists/*

COPY --from=web-builder /app/web/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p data/cleaned data/raw output

EXPOSE 80
EXPOSE 8501

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["/entrypoint.sh"]
