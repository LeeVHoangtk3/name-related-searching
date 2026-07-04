# Stage 1: Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency definition files
COPY package*.json ./

# Install packages using clean install (npm ci) for optimal cache utilization
RUN npm ci

# Copy the rest of the source files and build the React SPA application
COPY . .
RUN npm run build

# Stage 2: Runtime stage with Nginx
FROM nginx:alpine

# Copy built static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Load the optimized frontend Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
