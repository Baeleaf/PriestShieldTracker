# Release updates

CurseForge project: 1805535. Repository: https://github.com/Baeleaf/SoulShield

## One-time connection

The project Source tab is set to GitHub and **new tagged commits only**.
GitHub also needs an active push webhook. On November 14, 2026, the repository's
Webhooks page contained no hooks, so automatic delivery is not connected yet.

1. Create a CurseForge API token at https://www.curseforge.com/account/api-tokens.
2. Open https://github.com/Baeleaf/SoulShield/settings/hooks/new.
3. Set Payload URL to `https://www.curseforge.com/api/projects/1805535/package?token=YOUR_TOKEN`.
4. Leave SSL verification enabled, keep **Just the push event**, and enable Active.
5. Add the webhook. Keep the token out of source files, screenshots, and release notes.

This requires the owner's credential setup. Do not create an experimental tag just
to test it while the first public file is under review.

## Each release

1. Finish local in-game checks and review the change.
2. Update `## Version` in SoulShield.toc and add the changelog entry.
3. Run `python tests/check.py` and `python scripts/package.py --tag vX.Y.Z`.
4. Commit and push the code, then push a new `vX.Y.Z` tag at that commit.
5. GitHub Actions builds and attaches the installable ZIP to a GitHub release.
   CurseForge's own packager independently receives the push webhook and builds
   the same code using `.pkgmeta`. There is no second automatic CurseForge upload.
6. Confirm a successful webhook delivery under GitHub Settings > Webhooks, a
   completed CurseForge build, and the correct file version/game version.
   Moderation can still delay visibility.

Use `vX.Y.Z-alpha.N` or `vX.Y.Z-beta.N` with the same TOC version (without `v`)
for prereleases. Avoid moving published tags; fix forward with a new version.
The CurseForge webhook is independent of GitHub Actions: it does not wait for
the GitHub tests, so local checks must pass before pushing a release tag.

The package keeps the `SoulShield` folder name and includes runtime Lua, media,
license notices, TOC, and changelog. Development files and large screenshots
are excluded by `.pkgmeta`.

Reference: https://support.curseforge.com/support/solutions/articles/9000197281-automatic-packaging
