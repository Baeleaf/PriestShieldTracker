# Release updates

CurseForge project: 1805535. Repository: https://github.com/Baeleaf/PriestShieldTracker

## One-time connection

The project Source tab is set to GitHub and **new tagged commits only**.
The owner completed the GitHub push webhook setup on November 14, 2026. Verified:
correct CurseForge project endpoint with a configured token, Active enabled,
push events only, and SSL verification enabled. GitHub reported a successful
initial ping. The first public version is approved and tagged-release packaging has been used for 0.3.0. The project and source URL now use PriestShieldTracker.

For future setup or replacement:

1. Create a CurseForge API token at https://www.curseforge.com/account/api-tokens.
2. Open https://github.com/Baeleaf/PriestShieldTracker/settings/hooks/new.
3. Set Payload URL to `https://www.curseforge.com/api/projects/1805535/package?token=YOUR_TOKEN`.
4. Leave SSL verification enabled, keep **Just the push event**, and enable Active.
5. Add the webhook. Keep the token out of source files, screenshots, and release notes.

## Each release

Increment the version after every addon update, including local-only changes.
For local builds, use the next `beta.N` suffix and keep both importer versions
in sync with the main TOC. The settings footer reads the installed TOC version.

1. Install the upcoming release into the owner's local WoW Forever AddOns folder
   before publishing. Preserve character SavedVariables and local development
   files. Verify the installed runtime files against the release package, then
   finish local in-game checks and review the change. A version label alone is
   not proof that the installed files are current. This is the owner's standing
   release preference, confirmed November 16, 2026.
   After building the package, run `./scripts/install-local.ps1` to install and
   hash-check every packaged runtime file. It backs up changed files and leaves
   SavedVariables and development files alone. Do not publish if installation
   or verification is blocked; report the blocker first.
2. Update `## Version` in PriestShieldTracker.toc and add the changelog entry.
   Keep the small compatibility importer version in step with the main TOC.
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

The package contains the `PriestShieldTracker` runtime folder and a small legacy settings importer. It includes runtime Lua, media,
license notices, TOC, and changelog. Development files and large screenshots
are excluded by `.pkgmeta`.

Reference: https://support.curseforge.com/support/solutions/articles/9000197281-automatic-packaging
