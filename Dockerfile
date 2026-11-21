# The host server of the tnwks agent platform: the upstream server ssh-mcp
# at its tag v2.26.0, built from its source with the steps of its own
# Dockerfile and no change of code (Design Doc of effort 0003, section
# 4.2.6, "The host server"). No key, token or config is in the image: the
# pod mounts them at run time.
#
# The source comes from the upstream repository at the full commit of the
# tag, so the build gets those bytes or fails. The two stages below are the
# stages of the upstream Dockerfile at that commit, with the same base
# pinned by digest; only the COPY sources name the source stage.
ARG UPSTREAM_COMMIT=e31e99b9184ba6b3dd7b65ceb717c7620ddbd828

FROM scratch AS source
ARG UPSTREAM_COMMIT
ADD --keep-git-dir=false https://github.com/tufantunc/ssh-mcp.git#${UPSTREAM_COMMIT} /

FROM node:22-slim@sha256:43ac6c60b8f89723f746e8a92ce91abd5017e627ce1ddfe4238355d3a30b772c AS builder
WORKDIR /app
COPY --from=source /package.json /package-lock.json ./
# As upstream: the prepare script needs the sources, and the build runs
# below. It also skips the optional native crypto binding of ssh2.
RUN npm ci --ignore-scripts
COPY --from=source /tsconfig.json ./
COPY --from=source /src/ ./src/
RUN npm run build

FROM node:22-slim@sha256:43ac6c60b8f89723f746e8a92ce91abd5017e627ce1ddfe4238355d3a30b772c
ARG UPSTREAM_COMMIT
ARG VERSION=dev
ARG REVISION=unknown
LABEL org.opencontainers.image.title="tnwks-host-mcp" \
      org.opencontainers.image.description="The ssh-mcp server v2.26.0, built from its tag with no change of code" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.base.name="docker.io/library/node:22-slim" \
      io.github.tnwks.upstream.source="https://github.com/tufantunc/ssh-mcp" \
      io.github.tnwks.upstream.version="v2.26.0" \
      io.github.tnwks.upstream.revision="${UPSTREAM_COMMIT}"
WORKDIR /app

RUN groupadd -r -g 65532 appgroup && useradd -r -u 65532 -g appgroup appuser

COPY --from=builder /app/build ./build
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=source /config.default.toml ./config.default.toml
COPY --from=source /LICENSE ./LICENSE

RUN mkdir -p /home/appuser/.config/ssh-mcp && \
    chmod 700 /home/appuser/.config /home/appuser/.config/ssh-mcp && \
    chown -R appuser:appgroup /home/appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "process.exit(0)" || exit 1

ENV NODE_ENV=production
ENV SSH_MCP_DISABLE_MAIN=0

ENTRYPOINT ["node", "build/index.js"]
