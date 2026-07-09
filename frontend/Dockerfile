FROM node:22.18.0-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

FROM nginx:1.29.3-alpine

ENV SEEKPHONY_PUBLIC_API_BASE_URL=http://localhost:8000

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/docker-entrypoint.sh /docker-entrypoint.d/40-seekphony-config.sh
RUN chmod +x /docker-entrypoint.d/40-seekphony-config.sh
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
