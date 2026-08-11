# Production image for the SOC-AGENTS Next.js console.
# Three-stage build: dependency install, production build, then a minimal
# runtime that copies only the pruned production artifacts and runs as
# a non-root user.
FROM node:22-alpine AS deps
WORKDIR /app
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend ./
RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production

# Only production dependencies are carried into the runtime image.
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/package.json ./package.json
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# Non-root execution: Next.js refuses to start as root without extra flags,
# and running unprivileged is a baseline hardening requirement.
RUN addgroup --system --gid 1001 soc && adduser --system --uid 1001 --ingroup soc soc \
    && chown -R soc:soc /app
USER soc

EXPOSE 3000

HEALTHCHECK --interval=20s --timeout=5s --retries=5 \
    CMD wget -qO- "http://localhost:3000/" || exit 1

CMD ["npm", "run", "start"]
