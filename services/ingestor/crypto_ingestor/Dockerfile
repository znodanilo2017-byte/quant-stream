# Build stage
FROM rust:1.83-slim-bookworm AS builder

# Install only the packages needed to compile native dependencies.
RUN apt-get update && apt-get install -y \
    pkg-config libssl-dev libsasl2-dev cmake g++ libcurl4-openssl-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache dependencies to keep rebuilds fast.
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release && rm -rf src

# Build the actual ingestor binary.
COPY src ./src
RUN touch src/main.rs && cargo build --release

# Runtime stage
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates libssl3 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/target/release/crypto_ingestor .

CMD ["./crypto_ingestor"]