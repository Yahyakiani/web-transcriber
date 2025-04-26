# frontend/web-transcriber/Dockerfile

# --- Builder Stage ---
# Use Node.js LTS version (check compatibility with your Next.js version if needed)
FROM node:18-alpine as builder

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock)
COPY package*.json ./
# If using yarn:
# COPY package.json yarn.lock ./

# Install dependencies
# Use --frozen-lockfile for CI/production builds
RUN npm install --frozen-lockfile
# If using yarn:
# RUN yarn install --frozen-lockfile

# Copy the rest of the application code
COPY . .

# Set build-time environment variables (if any are needed during build)
# Example: If NEXT_PUBLIC_BACKEND_URL needs to be baked in (not recommended for runtime flexibility)
# ARG NEXT_PUBLIC_BACKEND_URL
# ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL

# Build the Next.js application for production
# This runs `next build`
RUN npm run build
# If using yarn:
# RUN yarn build

# --- Runner Stage ---
# Use a smaller base image for the final stage
FROM node:18-alpine as runner

WORKDIR /app

# Set environment variables for production
ENV NODE_ENV=production
# Set the backend URL at runtime (more flexible than baking it in)
# This will be overridden by docker-compose or ECS environment variables
ENV NEXT_PUBLIC_BACKEND_URL=http://backend:8000

# Copy necessary files from the builder stage
COPY --from=builder /app/public ./public
# Copy standalone output (recommended for optimized production builds)
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static

# Expose the port Next.js runs on (default 3000)
EXPOSE 3000

# Create a non-root user for security
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs
USER nextjs

# Start the Next.js production server (using the standalone output)
# node server.js is the command for standalone output
CMD ["node", "server.js"]