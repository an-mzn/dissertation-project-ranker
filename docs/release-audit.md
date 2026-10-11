# Release audit — 11 October 2026

The current public files are ready for an initial release, with no known failing
checks. This is an audit of the current files, not a guarantee against every bug.

## Fixes made during the audit

- Opening “Original university description” no longer submits a project choice.
- Completing all comparisons clears obsolete comparison cards; undo restores them.
- Malformed checkpoint structures and invalid saved settings now fall back to a
  valid backup, or report a recoverable error without overwriting the files.
- Invalid browser-action payloads return HTTP 400.
- Added the approved MIT license and automated Linux/Windows test configuration.
- Added concise troubleshooting and publishing guidance to the README.

## Verification completed

- All 25 tests pass in the existing environment and in a freshly installed
  environment using the documented requirements.
- Fresh dependencies pass `pip check`.
- A public-only copy, containing no personal archive, executes every notebook
  cell in a real Jupyter kernel. Browser-server startup and checkpoint creation
  succeed; automatic OS browser launch was suppressed during this check.
- Tests cover raw/enriched CSVs, optional metadata, invalid inputs, neutral and
  draft-informed scoring, Markdown escaping, choices, skip, undo, completion,
  checkpoint recovery, reruns, restoration, and browser HTTP actions.
- The export JavaScript passes syntax validation. Its CSV quoting and ranker
  compatibility were previously verified using a simulated university page.
- Personal original inputs and checkpoints remain byte-for-byte unchanged and
  restore the 73-project session with 146 processed comparisons.

## Privacy review

The files Git would publish contain no original project titles, personal saved
session content, email addresses, local home-directory paths, or common secret
patterns. Examples use fictional projects and supervisors. The public notebook
has no saved outputs or widget-state metadata.

`personal/`, `data/`, environments, caches, and session files are Git-ignored.
There are no commits or remotes, so no existing repository history to expose.
Ignored files still exist locally: publish through Git, rather than zipping the
whole working folder. Run tests and clear notebook outputs again after using
personal data and before publishing. New Git commits will expose the author
identity configured for those commits.

## Practical limits

- Installation and kernel execution were tested on macOS. Linux and Windows are
  configured for CI, but those jobs have not run yet. Python 3.10 is included in
  CI to check the documented minimum version.
- Browser HTTP behavior was exercised; visual layout and interaction in each
  browser/device still need manual testing.
- The export script depends on the supplied university website layout. The live
  university site was not accessed or tested; pagination and failures must be
  checked by the student.
- The app is a local notebook tool, not a hosted multi-user service. AI-generated
  descriptions and estimates remain optional and need student review.

No repository was published and no Git commit was created during this audit.
