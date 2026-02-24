FROM node:20-alpine

WORKDIR /app

# Accept proxy args
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Set proxy environment variables if provided
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}

# Copy package files
COPY package*.json ./

# Configure npm proxy if HTTP_PROXY is set
RUN if [ -n "$HTTP_PROXY" ]; then \
        npm config set proxy $HTTP_PROXY && \
        npm config set https-proxy $HTTPS_PROXY; \
    fi

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Development command
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
