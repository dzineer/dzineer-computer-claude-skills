---
name: docker
description: Complete Docker mastery — containers, images, volumes, bind mounts, networking, port mapping, docker-compose, multi-stage builds, security hardening, data persistence, registries, orchestration, debugging, and production deployment patterns. Use when the user needs help with any Docker-related task.
trigger: When the user mentions Docker, containers, docker-compose, Dockerfile, container images, volumes, port mapping, container networking, or any containerization topic.
---

# Docker Skill — Complete Reference

You are a Docker expert. Apply this knowledge when helping users build, deploy, debug, secure, and manage Docker containers and infrastructure.

---

## 1. Core Concepts

### Container vs Image vs Volume vs Network

| Concept | What It Is | Lifecycle |
|---------|-----------|-----------|
| **Image** | Read-only template (layered filesystem) | Persists until deleted |
| **Container** | Running instance of an image | Ephemeral by default |
| **Volume** | Persistent storage managed by Docker | Persists independently of containers |
| **Bind Mount** | Host directory mounted into container | Lives on host filesystem |
| **Network** | Virtual network connecting containers | Persists until deleted |

### Container Lifecycle

```
Image --[docker run]--> Created --[start]--> Running --[stop]--> Stopped --[rm]--> Deleted
                                                  |
                                              [pause]--> Paused
```

---

## 2. Container Management

### Creating & Running Containers

```bash
# Basic run (foreground)
docker run ubuntu:24.04 echo "hello"

# Detached (background) with name
docker run -d --name myapp nginx:latest

# Interactive shell
docker run -it ubuntu:24.04 /bin/bash

# Auto-remove when stopped
docker run --rm -it alpine sh

# Run with environment variables
docker run -d \
  --name db \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=myapp \
  postgres:16

# Run with env file
docker run -d --env-file .env myapp

# Resource limits
docker run -d \
  --name app \
  --memory=512m \
  --cpus=1.5 \
  --memory-swap=1g \
  --pids-limit=100 \
  myapp

# Restart policies
docker run -d --restart=unless-stopped myapp  # Survives host reboot
docker run -d --restart=on-failure:5 myapp    # Retry 5 times on crash
docker run -d --restart=always myapp          # Always restart
docker run -d --restart=no myapp              # Never restart (default)
```

### Container Operations

```bash
# List running
docker ps

# List all (including stopped)
docker ps -a

# Stop gracefully (SIGTERM, then SIGKILL after 10s)
docker stop myapp

# Stop with custom timeout
docker stop -t 30 myapp

# Kill immediately (SIGKILL)
docker kill myapp

# Remove stopped container
docker rm myapp

# Force remove running container
docker rm -f myapp

# Remove all stopped containers
docker container prune

# Execute command in running container
docker exec -it myapp /bin/bash
docker exec myapp cat /etc/hosts

# View logs
docker logs myapp
docker logs -f myapp                    # Follow (tail)
docker logs --tail 100 myapp            # Last 100 lines
docker logs --since 2h myapp            # Last 2 hours
docker logs --until 2024-01-01 myapp    # Before date

# Inspect container details
docker inspect myapp
docker inspect --format='{{.State.Status}}' myapp
docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' myapp

# Container stats (live resource usage)
docker stats
docker stats myapp

# Copy files to/from container
docker cp myfile.txt myapp:/app/
docker cp myapp:/app/output.log ./

# View container filesystem changes
docker diff myapp

# Create image from container
docker commit myapp myapp-snapshot:v1

# Rename container
docker rename myapp myapp-old

# Pause/unpause (freezes processes via cgroups)
docker pause myapp
docker unpause myapp

# Wait for container to exit and return exit code
docker wait myapp

# View port mappings
docker port myapp
```

---

## 3. Port Mapping (Networking to Host)

### Port Mapping Patterns

```bash
# Map container port 80 to host port 8080
docker run -d -p 8080:80 nginx

# Map to specific host interface
docker run -d -p 127.0.0.1:8080:80 nginx          # Localhost only
docker run -d -p 0.0.0.0:8080:80 nginx             # All interfaces (default)
docker run -d -p 192.168.1.100:8080:80 nginx        # Specific IP

# Map UDP port
docker run -d -p 53:53/udp dns-server

# Map both TCP and UDP
docker run -d -p 53:53/tcp -p 53:53/udp dns-server

# Random host port (Docker picks an available port)
docker run -d -p 80 nginx
docker port <container>  # See what port was assigned

# Map multiple ports
docker run -d \
  -p 80:80 \
  -p 443:443 \
  -p 8080:8080 \
  nginx

# Port range
docker run -d -p 8000-8010:8000-8010 myapp

# Expose all ports defined in Dockerfile
docker run -d -P nginx   # Maps all EXPOSE'd ports to random host ports
```

### Port Mapping Security

```bash
# DANGEROUS: Binds to 0.0.0.0 (all interfaces, world-accessible)
docker run -d -p 8080:80 nginx

# SAFE: Binds to localhost only
docker run -d -p 127.0.0.1:8080:80 nginx

# WARNING: Docker modifies iptables directly, bypassing UFW/firewalld!
# To prevent Docker from exposing ports publicly:
# /etc/docker/daemon.json
{
  "iptables": false    # Caution: breaks container networking unless you manage iptables yourself
}

# Better approach: Always bind to 127.0.0.1 and use a reverse proxy
docker run -d -p 127.0.0.1:8080:80 nginx
# Then use Caddy/Nginx/Traefik as reverse proxy with proper TLS
```

---

## 4. Volumes & Data Persistence

### Volume Types

| Type | Syntax | Use Case |
|------|--------|----------|
| **Named Volume** | `-v mydata:/data` | Database storage, shared data |
| **Bind Mount** | `-v /host/path:/container/path` | Development, config files |
| **tmpfs Mount** | `--tmpfs /tmp` | Sensitive data, temp files |
| **Anonymous Volume** | `-v /data` | Temporary, auto-named |

### Named Volumes (Docker-Managed)

```bash
# Create a volume
docker volume create mydata

# Run with named volume
docker run -d \
  --name db \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16

# Volume persists after container is removed
docker rm -f db
docker run -d \
  --name db2 \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16
# Data is still there!

# List volumes
docker volume ls

# Inspect volume
docker volume inspect pgdata

# Remove volume
docker volume rm pgdata

# Remove all unused volumes
docker volume prune

# Remove all unused volumes including named ones
docker volume prune -a
```

### Bind Mounts (Host Directory)

```bash
# Mount host directory into container
docker run -d \
  --name app \
  -v /home/user/project:/app \
  node:20

# Mount current directory
docker run -d \
  --name app \
  -v $(pwd):/app \
  node:20

# Read-only bind mount (container cannot modify)
docker run -d \
  -v $(pwd)/config:/app/config:ro \
  myapp

# Mount single file
docker run -d \
  -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx

# Using --mount syntax (more explicit, recommended)
docker run -d \
  --mount type=bind,source=$(pwd)/data,target=/app/data \
  myapp

docker run -d \
  --mount type=bind,source=$(pwd)/config,target=/app/config,readonly \
  myapp
```

### tmpfs Mounts (In-Memory)

```bash
# tmpfs mount (never written to disk — for sensitive data)
docker run -d \
  --tmpfs /tmp:rw,noexec,nosuid,size=100m \
  myapp

# Using --mount syntax
docker run -d \
  --mount type=tmpfs,destination=/tmp,tmpfs-size=100m \
  myapp
```

### Volume Drivers (Remote/Cloud Storage)

```bash
# NFS volume
docker volume create \
  --driver local \
  --opt type=nfs \
  --opt o=addr=192.168.1.1,rw \
  --opt device=:/path/to/share \
  nfs-data

# CIFS/SMB volume
docker volume create \
  --driver local \
  --opt type=cifs \
  --opt device=//server/share \
  --opt o=username=user,password=pass \
  smb-data
```

### Persisting Everything — Complete Pattern

```bash
# Database with persistent data
docker run -d \
  --name postgres \
  -v pgdata:/var/lib/postgresql/data \
  -v $(pwd)/init.sql:/docker-entrypoint-initdb.d/init.sql:ro \
  -e POSTGRES_PASSWORD=secret \
  postgres:16

# App with persistent uploads, logs, and config
docker run -d \
  --name app \
  -v app-uploads:/app/uploads \
  -v app-logs:/app/logs \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  myapp

# Redis with persistent data
docker run -d \
  --name redis \
  -v redis-data:/data \
  redis:7 redis-server --appendonly yes

# Backup a volume
docker run --rm \
  -v pgdata:/source:ro \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/pgdata-$(date +%Y%m%d).tar.gz -C /source .

# Restore a volume
docker run --rm \
  -v pgdata:/target \
  -v $(pwd)/backups:/backup:ro \
  alpine tar xzf /backup/pgdata-20240101.tar.gz -C /target
```

---

## 5. Networking

### Network Types

| Driver | Description | Use Case |
|--------|-----------|----------|
| **bridge** | Default. Isolated network on single host | Most containers |
| **host** | Container shares host's network stack | Performance-critical, no isolation |
| **none** | No networking | Maximum isolation |
| **overlay** | Multi-host networking (Swarm) | Distributed apps |
| **macvlan** | Container gets its own MAC address | Legacy apps needing direct LAN access |
| **ipvlan** | Like macvlan but shares host MAC | When MAC limits exist |

### Bridge Networks (Default & Custom)

```bash
# Default bridge — containers communicate by IP only
docker run -d --name app1 nginx
docker run -d --name app2 nginx
# app1 can reach app2 by IP but NOT by name

# Custom bridge — enables DNS-based service discovery
docker network create mynet
docker run -d --name app1 --network mynet nginx
docker run -d --name app2 --network mynet nginx
# app1 can reach app2 by name: curl http://app2:80

# ALWAYS use custom bridge networks, never the default bridge

# Connect a running container to a network
docker network connect mynet existing-container

# Disconnect from a network
docker network disconnect mynet existing-container

# Container on multiple networks
docker run -d --name app --network frontend nginx
docker network connect backend app
# Now app can reach containers on both frontend and backend networks

# Inspect network
docker network inspect mynet

# List networks
docker network ls

# Remove network
docker network rm mynet

# Remove all unused networks
docker network prune
```

### Host Network (No Isolation)

```bash
# Container uses host's network directly — no port mapping needed
docker run -d --network host nginx
# Nginx is now on host's port 80 directly
# WARNING: No network isolation. Container sees all host interfaces.
```

### None Network (Complete Isolation)

```bash
# No networking at all
docker run -d --network none myapp
# Container has only loopback interface
```

### DNS & Service Discovery

```bash
# On custom bridge networks, containers resolve each other by name
docker network create app-net

docker run -d --name db --network app-net postgres:16
docker run -d --name api --network app-net \
  -e DATABASE_URL=postgresql://user:pass@db:5432/myapp \
  myapi

# Network aliases (multiple names for same container)
docker run -d --name postgres --network app-net --network-alias db --network-alias database postgres:16
# Both "db" and "database" resolve to this container
```

### Inter-Container Communication Patterns

```bash
# Frontend -> API -> Database (3-tier)
docker network create frontend
docker network create backend

docker run -d --name db --network backend postgres:16
docker run -d --name api --network backend --network frontend myapi
docker run -d --name web --network frontend -p 80:80 nginx
# web can reach api, api can reach db, web CANNOT reach db
```

---

## 6. Dockerfile — Building Images

### Dockerfile Reference

```dockerfile
# Always pin exact versions for reproducibility
FROM node:20.11-alpine AS base

# Labels for metadata
LABEL maintainer="you@example.com"
LABEL version="1.0"
LABEL description="My application"

# Set working directory
WORKDIR /app

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3000

# Arguments (build-time only)
ARG APP_VERSION=1.0.0

# Copy dependency files first (better layer caching)
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1001 appgroup && \
    adduser -u 1001 -G appgroup -s /bin/sh -D appuser

# Change ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port (documentation only, doesn't publish)
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

# Default command
CMD ["node", "server.js"]

# Or use ENTRYPOINT for containers that act as executables
# ENTRYPOINT ["node", "server.js"]
# CMD ["--port", "3000"]  # Default args, overridable
```

### Multi-Stage Builds (Smaller Images)

```dockerfile
# Stage 1: Build
FROM node:20 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Production (only the built artifacts)
FROM node:20-alpine AS production
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY --from=builder /app/dist ./dist

USER node
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

```dockerfile
# Go multi-stage (tiny final image)
FROM golang:1.22 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/server .

FROM scratch
COPY --from=builder /app/server /server
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
EXPOSE 8080
ENTRYPOINT ["/server"]
```

```dockerfile
# Rust multi-stage
FROM rust:1.77 AS builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs && cargo build --release && rm -rf src
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/myapp /usr/local/bin/myapp
USER nobody
EXPOSE 8080
CMD ["myapp"]
```

### Build Commands

```bash
# Build image
docker build -t myapp:latest .

# Build with specific Dockerfile
docker build -f Dockerfile.prod -t myapp:prod .

# Build with build args
docker build --build-arg APP_VERSION=2.0.0 -t myapp:2.0 .

# Build with no cache
docker build --no-cache -t myapp:latest .

# Build for specific platform
docker build --platform linux/amd64 -t myapp:latest .

# Multi-platform build (requires buildx)
docker buildx build --platform linux/amd64,linux/arm64 -t myapp:latest --push .

# Build and load into local Docker
docker buildx build --load -t myapp:latest .

# View build history / layers
docker history myapp:latest

# Tag an image
docker tag myapp:latest myregistry.com/myapp:v1.0

# Push to registry
docker push myregistry.com/myapp:v1.0
```

### .dockerignore

```
# .dockerignore
node_modules
npm-debug.log
.git
.gitignore
.env
.env.*
*.md
!README.md
docker-compose*.yml
Dockerfile*
.dockerignore
.vscode
.idea
coverage
.nyc_output
dist
build
tmp
```

### Layer Caching Best Practices

```dockerfile
# BAD: Busts cache on every code change
COPY . .
RUN npm install

# GOOD: Dependencies cached separately from code
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

# GOOD: Use cache mounts for package managers
RUN --mount=type=cache,target=/root/.npm npm ci
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
RUN --mount=type=cache,target=/root/.cargo/registry cargo build --release
```

---

## 7. Docker Compose

### docker-compose.yml Reference

```yaml
# docker-compose.yml
version: '3.8'  # Optional in modern Docker Compose

services:
  # Web application
  web:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        NODE_ENV: production
    image: myapp:latest
    container_name: myapp-web
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://user:pass@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    env_file:
      - .env
    volumes:
      - uploads:/app/uploads
      - ./config:/app/config:ro
    networks:
      - frontend
      - backend
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 256M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  # Database
  db:
    image: postgres:16-alpine
    container_name: myapp-db
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: myapp
    networks:
      - backend
    ports:
      - "127.0.0.1:5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d myapp"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis cache
  redis:
    image: redis:7-alpine
    container_name: myapp-redis
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    networks:
      - backend
    ports:
      - "127.0.0.1:6379:6379"
    restart: unless-stopped

  # Reverse proxy
  nginx:
    image: nginx:alpine
    container_name: myapp-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    networks:
      - frontend
    depends_on:
      - web
    restart: unless-stopped

  # Worker/background jobs
  worker:
    build: .
    command: node worker.js
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    volumes:
      - uploads:/app/uploads
    networks:
      - backend
    depends_on:
      - db
      - redis
    restart: unless-stopped
    deploy:
      replicas: 2

volumes:
  pgdata:
    driver: local
  redis-data:
    driver: local
  uploads:
    driver: local

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No external access — only inter-container
```

### Compose Commands

```bash
# Start all services (detached)
docker compose up -d

# Start specific service
docker compose up -d web

# Build and start
docker compose up -d --build

# Stop all services
docker compose down

# Stop and remove volumes (DESTROYS DATA)
docker compose down -v

# Stop and remove images
docker compose down --rmi all

# View logs
docker compose logs
docker compose logs -f web
docker compose logs --tail 50 db

# Scale a service
docker compose up -d --scale worker=3

# Execute command in service
docker compose exec web bash
docker compose exec db psql -U user -d myapp

# Run one-off command
docker compose run --rm web npm test

# View service status
docker compose ps

# Restart a service
docker compose restart web

# Pull latest images
docker compose pull

# View compose config (merged/resolved)
docker compose config

# List all compose projects
docker compose ls
```

### Multiple Compose Files (Override Pattern)

```bash
# docker-compose.yml          — Base config
# docker-compose.override.yml — Dev overrides (auto-loaded)
# docker-compose.prod.yml     — Production overrides

# Dev (uses base + override automatically)
docker compose up -d

# Production (explicit file selection)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or use COMPOSE_FILE env
export COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml
docker compose up -d
```

```yaml
# docker-compose.override.yml (development)
services:
  web:
    build:
      target: development
    volumes:
      - .:/app                    # Hot reload with source mount
      - /app/node_modules         # Prevent overwriting node_modules
    ports:
      - "3000:3000"
      - "9229:9229"              # Debugger port
    environment:
      - NODE_ENV=development
    command: npm run dev
```

```yaml
# docker-compose.prod.yml (production)
services:
  web:
    image: registry.example.com/myapp:${VERSION}
    ports:
      - "127.0.0.1:3000:3000"
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
```

---

## 8. Security Hardening

### Container Security Fundamentals

```bash
# NEVER run as root inside containers
# In Dockerfile:
USER nonroot

# NEVER use --privileged unless absolutely necessary
docker run --privileged myapp  # BAD: Full host access

# Drop all capabilities, add only what's needed
docker run \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  myapp

# Read-only filesystem
docker run --read-only \
  --tmpfs /tmp \
  --tmpfs /run \
  myapp

# No new privileges (prevent setuid binaries)
docker run --security-opt=no-new-privileges:true myapp

# Limit syscalls with seccomp
docker run --security-opt seccomp=custom-profile.json myapp

# AppArmor profile
docker run --security-opt apparmor=docker-default myapp

# Resource limits (prevent DoS)
docker run \
  --memory=512m \
  --memory-swap=512m \
  --cpus=1.0 \
  --pids-limit=100 \
  --ulimit nofile=1024:1024 \
  myapp
```

### Image Security

```bash
# Use minimal base images
FROM alpine:3.19          # ~5MB
FROM distroless/static    # ~2MB (no shell!)
FROM scratch              # 0MB (static binaries only)

# Pin exact versions (NEVER use :latest in production)
FROM node:20.11.1-alpine3.19

# Scan images for vulnerabilities
docker scout cves myapp:latest
docker scout quickview myapp:latest

# Verify image signatures (Docker Content Trust)
export DOCKER_CONTENT_TRUST=1
docker pull myapp:latest  # Fails if unsigned

# Multi-stage builds to exclude build tools from final image
# (See Section 6)

# Don't store secrets in images!
# BAD:
ENV API_KEY=secret123
COPY .env /app/.env

# GOOD: Use runtime secrets
docker run -e API_KEY=secret123 myapp
# Or Docker secrets (Swarm):
echo "secret123" | docker secret create api_key -
```

### Docker Daemon Security

```json
// /etc/docker/daemon.json
{
  "icc": false,                    // Disable inter-container communication on default bridge
  "userland-proxy": false,         // Use iptables instead of userland proxy
  "no-new-privileges": true,       // Default no-new-privileges for all containers
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "live-restore": true,            // Containers survive daemon restart
  "userns-remap": "default",       // User namespace remapping
  "default-ulimits": {
    "nofile": { "Name": "nofile", "Hard": 64000, "Soft": 64000 }
  }
}
```

### Network Security

```bash
# Internal network (no external access)
docker network create --internal secure-net
# Containers on secure-net can talk to each other but NOT the internet

# Encrypt overlay network traffic (Swarm)
docker network create --opt encrypted --driver overlay secure-overlay

# Restrict container egress with iptables
# Block container from reaching metadata service (cloud)
iptables -I DOCKER-USER -d 169.254.169.254 -j DROP
```

### Secrets Management

```yaml
# docker-compose.yml with secrets
services:
  db:
    image: postgres:16
    secrets:
      - db_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password

secrets:
  db_password:
    file: ./secrets/db_password.txt    # File-based
  # Or external (Swarm only):
  # db_password:
  #   external: true
```

### Security Checklist

- [ ] No containers running as root
- [ ] No `--privileged` flags
- [ ] All capabilities dropped, only required ones added back
- [ ] Read-only root filesystem where possible
- [ ] No secrets baked into images
- [ ] Images scanned for CVEs
- [ ] Base images pinned to specific versions
- [ ] Resource limits set (memory, CPU, PIDs)
- [ ] Ports bound to 127.0.0.1, not 0.0.0.0
- [ ] Internal networks for backend services
- [ ] Health checks configured
- [ ] Log limits configured
- [ ] Docker Content Trust enabled
- [ ] `no-new-privileges` set

---

## 9. Image Management

```bash
# List local images
docker images
docker images --filter dangling=true

# Remove image
docker rmi myapp:latest

# Remove dangling images (untagged)
docker image prune

# Remove ALL unused images
docker image prune -a

# Save image to tar
docker save myapp:latest | gzip > myapp-latest.tar.gz

# Load image from tar
docker load < myapp-latest.tar.gz

# Export container filesystem to tar
docker export mycontainer > container-fs.tar

# Import filesystem as image
docker import container-fs.tar myimage:imported

# View image layers and sizes
docker history myapp:latest --no-trunc

# Tag for registry
docker tag myapp:latest ghcr.io/user/myapp:v1.0.0

# Push to registry
docker push ghcr.io/user/myapp:v1.0.0

# Pull from registry
docker pull ghcr.io/user/myapp:v1.0.0

# Login to registry
docker login ghcr.io
docker login registry.example.com -u user -p token

# Build and push multi-platform
docker buildx create --use
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/user/myapp:v1.0.0 \
  --push .
```

---

## 10. Debugging & Troubleshooting

```bash
# Why did my container exit?
docker inspect --format='{{.State.ExitCode}}' myapp
docker inspect --format='{{.State.Error}}' myapp
docker logs myapp

# Common exit codes
# 0   = Normal exit
# 1   = Application error
# 137 = OOM killed (SIGKILL) — increase --memory
# 139 = Segfault (SIGSEGV)
# 143 = SIGTERM (normal stop)

# Check if OOM killed
docker inspect --format='{{.State.OOMKilled}}' myapp

# Debug a crashed container (override entrypoint)
docker run -it --entrypoint /bin/sh myapp:latest

# Debug networking
docker run --rm --network mynet nicolaka/netshoot
# Inside: dig db, curl api:3000, nslookup redis, tcpdump, ss -tulpn

# Inspect container processes
docker top myapp

# Filesystem usage
docker system df
docker system df -v

# Full system cleanup
docker system prune          # Remove stopped containers, unused networks, dangling images
docker system prune -a       # Also remove all unused images
docker system prune -a --volumes  # Also remove all unused volumes (CAREFUL!)

# View Docker events in real time
docker events
docker events --filter type=container

# View resource usage
docker stats --no-stream

# Check Docker daemon logs
journalctl -u docker.service

# Verify Docker installation
docker info
docker version
```

---

## 11. Docker Buildx & Multi-Platform

```bash
# Create a new builder
docker buildx create --name mybuilder --use

# List builders
docker buildx ls

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64,linux/arm/v7 \
  -t myapp:latest \
  --push .

# Build and load locally (single platform only)
docker buildx build --load -t myapp:latest .

# Inspect builder
docker buildx inspect mybuilder

# Use QEMU for cross-platform emulation
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
```

---

## 12. Registry Operations

### Private Registry

```bash
# Run local registry
docker run -d \
  -p 5000:5000 \
  --name registry \
  -v registry-data:/var/lib/registry \
  registry:2

# Tag and push to local registry
docker tag myapp:latest localhost:5000/myapp:latest
docker push localhost:5000/myapp:latest

# Pull from local registry
docker pull localhost:5000/myapp:latest

# List images in registry
curl http://localhost:5000/v2/_catalog
curl http://localhost:5000/v2/myapp/tags/list
```

### Common Registries

| Registry | URL | Auth |
|----------|-----|------|
| Docker Hub | docker.io | `docker login` |
| GitHub Container Registry | ghcr.io | `docker login ghcr.io -u USER --password-stdin` |
| AWS ECR | *.dkr.ecr.*.amazonaws.com | `aws ecr get-login-password \| docker login` |
| Google GCR | gcr.io | `gcloud auth configure-docker` |
| Azure ACR | *.azurecr.io | `az acr login --name myregistry` |

---

## 13. Docker Init & Dev Environments

```bash
# Generate Dockerfile and compose.yaml for your project
docker init

# Dev Containers (VS Code)
# .devcontainer/devcontainer.json
{
  "name": "My Dev",
  "dockerComposeFile": "../docker-compose.yml",
  "service": "web",
  "workspaceFolder": "/app",
  "customizations": {
    "vscode": {
      "extensions": ["dbaeumer.vscode-eslint"]
    }
  }
}
```

---

## 14. Production Patterns

### Health Checks + Graceful Shutdown

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

# In your app: handle SIGTERM for graceful shutdown
# Node.js example:
# process.on('SIGTERM', () => { server.close(); process.exit(0); });
```

### Zero-Downtime Deployment (Compose)

```bash
# Rolling update with compose
docker compose up -d --no-deps --build web

# Blue-green with Traefik labels
# Deploy new version alongside old, switch traffic, remove old
```

### Logging Best Practices

```yaml
services:
  web:
    logging:
      driver: json-file
      options:
        max-size: "10m"      # Rotate at 10MB
        max-file: "3"        # Keep 3 rotated files
        tag: "{{.Name}}"     # Tag with container name

# For production, use centralized logging:
# driver: fluentd
# driver: gelf
# driver: syslog
```

### Docker in CI/CD

```yaml
# GitHub Actions
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

---

## 15. Quick Reference — Common Recipes

### Dev Database

```bash
# PostgreSQL
docker run -d --name pg -p 5432:5432 \
  -e POSTGRES_PASSWORD=dev \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16

# MySQL
docker run -d --name mysql -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=dev \
  -v mysqldata:/var/lib/mysql \
  mysql:8

# MongoDB
docker run -d --name mongo -p 27017:27017 \
  -v mongodata:/data/db \
  mongo:7

# Redis
docker run -d --name redis -p 6379:6379 \
  -v redisdata:/data \
  redis:7 redis-server --appendonly yes
```

### Full Stack (Node + Postgres + Redis + Nginx)

```bash
docker network create app
docker run -d --name db --network app \
  -v pgdata:/var/lib/postgresql/data \
  -e POSTGRES_PASSWORD=secret postgres:16
docker run -d --name redis --network app \
  -v redisdata:/data redis:7
docker run -d --name api --network app \
  -e DATABASE_URL=postgresql://postgres:secret@db:5432/postgres \
  -e REDIS_URL=redis://redis:6379 myapi
docker run -d --name web --network app \
  -p 80:80 -v ./nginx.conf:/etc/nginx/nginx.conf:ro nginx
```

### Cleanup Everything

```bash
# Nuclear option — remove everything
docker stop $(docker ps -aq)
docker system prune -a --volumes

# Selective cleanup
docker container prune   # Stopped containers
docker image prune -a    # Unused images
docker volume prune      # Unused volumes
docker network prune     # Unused networks
```
