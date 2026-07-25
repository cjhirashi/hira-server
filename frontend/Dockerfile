FROM node:20-alpine AS base

WORKDIR /app

COPY package*.json ./
RUN npm ci

# ── Imagen de desarrollo ────────────────────────────────────────────────────
FROM base AS development

COPY . .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ── Imagen de producción (build estático) ───────────────────────────────────
FROM base AS builder

COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS production

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
