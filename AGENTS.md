# AGENTS.md

How to work in this repo. It follows the app-repo standard in
[iT3E/app-repo-template](https://github.com/iT3E/app-repo-template), which
manages most of the repo setup (`.copier-answers.yml` lists the release);
tnwks-ops is the reference for anything not covered there.

## What this is

The image of the host server of the tnwks agent platform: the upstream
`ssh-mcp` at a pinned tag and commit, built with no change of code
(`README.md`). The Python part is the image test only. CI builds the image
`ghcr.io/it3e/<this repo>`, which is public, and pushes it on release tags
only. tnwks-ops deploys it, one pod at each site, behind the central MCP
gateway. Never change the code of the upstream server here: a change of
the image is a change of `UPSTREAM_COMMIT`, the base digest or the tests.

## Change workflow

- Every change goes through a PR, squash-merged. Never push to `main`.
  GitHub Free has no rulesets on private repos, so nothing enforces this
  except you: merge with `gh-merge-safe.sh <pr> iT3E/<this repo>`, which
  refuses unless every check passed. Renovate merges its own PRs only when
  every check is green (`ignoreTests: false`).
- Install the hooks once per clone: `task precommit:init`.
- Add a Changie fragment (`changie new`, under `.changes/unreleased/`) or
  label the PR `skip-changelog` (docs, CI-only, chores). Merging fragments
  cuts a release: `release.yaml` tags `vX.Y.Z` and builds `:X.Y.Z`. Kinds:
  Fixed/Security are a patch, Added/Changed/Deprecated/Removed a minor,
  Breaking a major.
- Renovate PRs carry no fragment. A merged one that changed what goes into
  the image (dependencies, the Dockerfile) releases a patch by itself
  (`auto-fragment`, "Dependency updates"); template and CI-only updates
  release nothing. A PR by a person always brings its own fragment.
- Image tags: only a release tag pushes, as `:<version>` and
  `:sha-<short>`; `main` builds without pushing. tnwks-ops pins
  `:<version>@sha256`, so a release reaches the cluster only when a
  tnwks-ops PR moves that pin.
- Checks: `build.yaml` (compileall, the Docker build and its tests), `privacy`, `betterleaks`, `changelog`,
  `actionlint` (workflow changes only), and the labeler. Locally: `task test`.
- The workflows are thin callers of the reusable workflows in
  iT3E/github-workflows, pinned by the template, and the files listed in
  app-repo-template's README are managed by Copier. Change them there; a
  template release reaches this repo as a
  `copier update` PR (Renovate, label `renovate/template`, merged by
  Renovate when green, or `task template:update`). A local edit to a managed file survives
  updates, but keep those rare.

## Privacy

The image is public, and the same rules as tnwks-ops apply here: no family
names (first names, nicknames, surname), personal email addresses, schools,
ages, addresses or anything else that says who is who. That covers files,
paths, commit messages, your git identity, PR and issue titles and bodies,
comments and reviews.

- `bin/privacy-check` checks the tnwks-ops denylist. CI reads it from the
  `PRIVACY_TERMS` secret (`task privacy:sync` refreshes it); locally it
  reads `$PRIVACY_TERMS` or a tnwks-ops checkout at `../tnwks-ops`.
- Before posting a PR body, comment or review, write it to a file, run
  `bin/privacy-check --text < file`, and post with `--body-file`.
- Exceptions (`.github/privacy-allow`, `privacy:allow` on a line) are the
  owner's call. Don't add one to get a PR through.
- Never put a credential in a file or doc. Secrets are SOPS Secrets in
  tnwks-ops and reach the service as env vars.

## Writing

Plain prose, short sentences. No emdashes in new prose (use a comma, colon
or parentheses). No AI-attribution trailers in commits.
