# Tiger Bytes — hardened publish pipeline

Publishes to tigertyagarajan.com used to be one-off patch scripts written
fresh each time, run live against `index.html`, and they kept failing:
pattern mismatches against a file that had changed since the script was
written, asserts on byte layout (a stray trailing newline killed the
Nov 8, 2026 cricket-essay publish's first run), and the recurring trap that
the live run was effectively the first real test of new code.

This folder replaces all of that with standing tooling. **In every future
publish, the only new things are data** — a small JSON spec, a card
fragment, and any new standalone content files. The code never changes.

## Files

| File | Role |
|---|---|
| `publish.py` | The patcher. Destined to live permanently in the repo at `tools/publish.py`, byte-identical across publishes. Pure Python 3 stdlib. |
| `rehearse.py` | Local pre-flight wrapper. Run before any dispatch; rehearses the exact code path against the exact live file. |
| `publish-workflow-template.yml` | The GitHub Actions shim. Uploaded unchanged to `.github/workflows/publish.yml` each publish; self-deletes in the publish commit, per the established pattern. |
| `tests/` | Specs, card fixtures, the live-file snapshot the tests ran against, the happy-path rehearsal report. |

## How a future publish flows

1. **Prepare data only.** Write the new standalone files (essay page, post
   pages, `assets/…` images — never inlined), the card fragment, and a spec:

   ```json
   {
     "file": "index.html",
     "anchor_text": "<article class=\"card\"><h3>Food, wine &amp; Lisbon</h3>",
     "position": "before",
     "card_file": "publish/card.html",
     "card_title": "The New Essay Title",
     "section_id": "beyond",
     "sentinels": ["What I stand for", "Beyond work", "</html>"]
   }
   ```

   (`anchor_regex` can replace `anchor_text`; `position` can be `after`.)

2. **Rehearse locally.**

   ```
   python3 rehearse.py --spec spec.json --card card.html \
       --file-list publish-files.txt [--new-page page.html=posts/slug.html]
   ```

   This fetches the *current* live `index.html`, stages `publish.py` + spec
   + card in a temp dir, runs the full dry-run (and proves it wrote
   nothing), applies to the copy, proves the result is a single pure
   insertion of exactly the card inside the intended section, and resolves
   every link in the card and new pages against the repo / the publish's
   file list. **Do not dispatch unless the rehearsal passes.** If it fails,
   fix the *data* (spec/card) offline — never debug live in the repo, in
   Tiger's inbox (GitHub emails him for every failed run; those emails stay
   on as the tripwire — the fix is preventing failures, not muting them).

3. **Upload the data files** to the repo by the established route (new
   standalone files + `publish/spec.json` + `publish/card.html`), then
   upload `publish-workflow-template.yml` — unchanged — as
   `.github/workflows/publish.yml`, and dispatch it. The shim runs
   `publish.py --dry-run`, then `--apply`, then makes **one** commit
   (patch + new files, shim and payload removed).

4. **Click-verify the live site.** Open the new page, click every link the
   publish touched, look at every photo. A green workflow is not proof;
   clicking is.

## Why this design kills each historical failure mode

| Historical failure | Killed by |
|---|---|
| Patch patterns matched against a remembered/stale layout | `rehearse.py` fetches the *current* live file; `publish.py` also re-validates everything at dispatch time inside the workflow. |
| Assert tripped on a stray trailing newline (Nov 8, 2026) | Anchors match on whitespace-normalised text; **no check anywhere asserts on trailing newlines or whole-file byte layout**. Post-patch checks are semantic (title count, sentinels, no new `data:` blobs, pure-insertion). Verified by Test 6 in `test-results.md`. |
| First-run-is-the-test (bespoke script's first real execution was live) | `--dry-run` runs the **complete** pipeline — patch plus every post-patch check — on an in-memory copy. The Nov 8 gap (a post-patch assert the rehearsal hadn't replicated) cannot recur: dry-run and apply share one code path, differing only in the final write. |
| Anchor matching the wrong place, or several places | Anchor must match **exactly once** after normalisation; 0 or 2+ matches is a refusal. Optional `section_id` containment pins the insertion inside the intended section. |
| Double-publish | Idempotency guard: if `card_title` already exists in the target, `publish.py` refuses (exit 3) — in dry-run and apply alike. |
| Media inlined as `data:` blobs (the 8 MB homepage, Oct 31) | Card fragments containing `data:image`/`data:application` are refused up front, and a post-patch check proves the patch added zero such strings. |
| Per-publish code drift | The workflow shim is byte-identical every time and contains no publish-specific logic; `publish.py` is versioned and permanent. Only the spec and content files change. |
| Unverifiable "it published" claims | `rehearse.py` proves pre-publish that the diff is one contiguous pure insertion of exactly the card; post-publish, the flow still ends with a human/agent click-verification of the live site. |

## Exit codes (publish.py)

- `0` success · `2` spec/IO error · `3` refusal (idempotency, anchor count,
  data: blob, bad card) · `4` post-patch verification failed.

`rehearse.py` exits non-zero if any of its checks fail.

## Tests

See `test-results.md` — happy path on the real live `index.html`
(124,485 bytes, fetched Nov 8, 2026), wrong-anchor refusal, double-publish
refusal, data-blob refusal, regex anchors, and the trailing-newline case.
All passed.
