FROM node:26-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY security-headers.conf /etc/nginx/security-headers.conf

# Run as the unprivileged `nginx` user (L-15). The container still has to
# bind port 80 — docker-compose maps 80:80 and the prod reverse proxy
# targets frontend:80 — and a non-root process can only bind a privileged
# port with CAP_NET_BIND_SERVICE. Grant exactly that one capability to the
# nginx binary (rather than running the whole master process as root) and
# hand the two runtime-writable paths to the user. `user nginx;` in the
# base image's nginx.conf becomes a harmless "ignored" warning once the
# master is unprivileged.
RUN apk add --no-cache libcap \
    && setcap 'cap_net_bind_service=+ep' /usr/sbin/nginx \
    && chown -R nginx:nginx /var/cache/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid
USER nginx

EXPOSE 80
# Informational only (nothing depends_on it): is nginx serving the SPA shell?
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
