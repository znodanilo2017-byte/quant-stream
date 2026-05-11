# 1. Етап збірки (Builder)
FROM rust:1.83-slim-bookworm AS builder

# Встановлюємо лише найнеобхідніше для компіляції C-бібліотек
RUN apt-get update && apt-get install -y \
    pkg-config libssl-dev libsasl2-dev cmake g++ libcurl4-openssl-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Кешуємо залежності (це економить 90% часу)
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release && rm -rf src

# Збираємо реальний код
COPY src ./src
RUN touch src/main.rs && cargo build --release

# 2. Етап запуску (Runtime) — щоб образ важив 100МБ, а не 2ГБ
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates libssl3 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/target/release/crypto_ingestor .

CMD ["./crypto_ingestor"]