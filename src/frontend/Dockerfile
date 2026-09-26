FROM node:22.14.0-alpine3.21 AS build

WORKDIR /app
RUN corepack enable
COPY src/frontend/package.json src/frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY src/frontend ./
RUN pnpm build

FROM nginx:1.27.4-alpine3.21
COPY infra/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
