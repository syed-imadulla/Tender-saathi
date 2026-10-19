# Stage 1: Build frontend application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package definitions and lockfile
COPY package.json package-lock.json ./
RUN npm ci

# Copy frontend source code
COPY . ./

# Build production bundle
RUN npm run build

# Stage 2: Production Nginx Server
FROM nginx:alpine

# Remove default nginx website
RUN rm -rf /usr/share/nginx/html/*

# Copy built artifacts from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
