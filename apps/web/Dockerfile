FROM oven/bun:1.3.11-alpine AS build
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile --ignore-scripts
COPY . .
ARG PUBLIC_ORIGIN
ENV PUBLIC_ORIGIN=${PUBLIC_ORIGIN}
RUN test -n "$PUBLIC_ORIGIN" && bun run build

FROM oven/bun:1.3.11-alpine
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3000 BODY_SIZE_LIMIT=256K
WORKDIR /app
COPY --from=build /app/package.json /app/bun.lock ./
RUN bun install --production --frozen-lockfile --ignore-scripts
COPY --from=build /app/build ./build
USER bun
EXPOSE 3000
CMD ["bun", "build/index.js"]
