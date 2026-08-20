FROM python:3.11-slim

WORKDIR /app

# curl saja yang perlu diinstall (untuk debugging manual konektivitas ke
# minio/postgres dari dalam container). build-essential & libpq-dev SENGAJA
# tidak dipasang: requirements.txt pakai psycopg2-binary (bukan psycopg2),
# yang sudah membawa libpq versi compiled di dalam wheel-nya -- jadi tidak
# perlu compiler sama sekali. Ini yang bikin apt-get install jadi 130+ detik
# di build sebelumnya; tanpa build-essential harusnya turun ke belasan detik.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: mode interaktif. Di-override oleh docker-compose.yaml
# ("command: [\"python\", \"main.py\", \"auto\"]") untuk automation.
CMD ["python", "main.py"]

