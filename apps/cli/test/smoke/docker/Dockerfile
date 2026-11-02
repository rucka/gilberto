# #48 AC-9 clean-container smoke. Build from repo root:
#   docker build -f apps/cli/test/smoke/docker/Dockerfile -t gilberto-smoke .
#   docker run --rm gilberto-smoke parity
#   docker run --rm --network none gilberto-smoke npx
FROM node:22-slim AS build
RUN corepack enable && corepack prepare pnpm@10.33.2 --activate
WORKDIR /src
COPY . .
RUN pnpm install --frozen-lockfile && pnpm build \
  && mkdir /pack \
  && (cd apps/cli && pnpm pack --pack-destination /pack) \
  && (cd packages/vault-bootstrap && pnpm pack --pack-destination /pack)

FROM node:22-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 && rm -rf /var/lib/apt/lists/*
COPY --from=build /pack /pack
# gilberto lives in its own prefix, off PATH: the npx case runs with no gilberto anywhere.
# workspace CLI is 0.0.0; stamp an in-range version so the #48 skill accepts it (same as host smoke).
RUN npm i -g --prefix /opt/gb /pack/*.tgz \
  && cd /opt/gb/lib/node_modules/gilberto && npm pkg set version=0.1.0-smoke
COPY apps/cli/test/smoke /repo/apps/cli/test/smoke
COPY plugins/gilberto-core /repo/plugins/gilberto-core
ENV GILBERTO_BIN=/opt/gb/bin/gilberto
ENTRYPOINT ["bash", "/repo/apps/cli/test/smoke/docker/run.sh"]
