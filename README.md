# tnwks-host-mcp

The image of the host server of the tnwks agent platform: the upstream MCP
server [`ssh-mcp`](https://github.com/tufantunc/ssh-mcp) (MIT) at its tag
`v2.26.0`, built from that commit with the steps of its own Dockerfile and
no change of code. The project publishes a Dockerfile and no image, so this
repo builds it, tests it and publishes it on its release tags; tnwks-ops
pins the digest.

## The image

- **The source.** The `source` stage takes the upstream repository at the
  full commit of the tag (`UPSTREAM_COMMIT` in the `Dockerfile`), so the
  build gets those bytes or fails. The two stages after it are the stages
  of the upstream Dockerfile at that commit: the same base, `node:22-slim`
  pinned by digest, the same `npm ci --ignore-scripts` and build. Only the
  `COPY` sources name the source stage. The image also gets the upstream
  `LICENSE` and OCI labels with the upstream version and commit.
- **The user.** uid 65532, as upstream. The pod runs it with a read-only
  root file system and no capability.
- **Nothing secret.** No key, token, host key or config is in the image.
  The pod mounts the SSH key of the agent account and the config, and
  gives the bearer token of the HTTP mode.
- **A new upstream release.** Renovate does not follow the upstream tag.
  A person reads the change, sets `UPSTREAM_COMMIT` to the full commit of
  the new tag, updates the base digest as upstream does, and updates
  `tools/ssh-mcp.json` from the image. Then the tests run.

## Tests

`bin/image-test <image>` (CI runs it on each built image before any push)
runs `tests/test_image.py` with Docker and python3 only. It starts the
server as in its pod: HTTP mode with a bearer token, its own approval off,
`--hostKeyMode=strict` with a pinned host key, and a read-only root. Its
one target is a fake host (`tests/sshd`) with a normal user, on an internal
network. The keys and the token are made for the run and deleted after it.
It checks:

- the image is the upstream tag and commit, and runs as uid 65532;
- a call with no token or another token gets 401;
- a Host header outside `--allowedHosts` gets 403;
- the server lists the tools of `tools/ssh-mcp.json`, no more and no less;
- a listed read runs as the normal user, who can not read a root file;
- a host key that is not the pinned one gets no connection.

The tool rule of the central MCP gateway, which names the tools that the
agent gets, is in tnwks-ops, not here.

## Workflow

This repo follows the app-repo standard in
[iT3E/app-repo-template](https://github.com/iT3E/app-repo-template), with
CI from [iT3E/github-workflows](https://github.com/iT3E/github-workflows);
`AGENTS.md` has the short version.

- Changes go through PRs, never straight to `main`. Merge only when every
  check is green (`gh-merge-safe.sh <pr> iT3E/tnwks-host-mcp`).
- `task precommit:init` installs the hooks: betterleaks, the privacy
  denylist (staged files, git identity, commit message) and ruff format.
- Each PR adds a Changie fragment (`changie new`) or carries the
  `skip-changelog` label. Merging fragments cuts a release (`vX.Y.Z` tag,
  GitHub Release, image `:X.Y.Z`).
- Renovate keeps dependencies current. Patch, digest and non-0.x minor
  updates merge themselves once CI is green; majors wait for review on the
  Renovate Dashboard issue. Template releases arrive as their own
  `renovate/template` PRs.
