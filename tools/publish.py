#!/usr/bin/env python3
"""
publish.py — the standing, versioned patcher for the Tiger Bytes site.

Repo location: tools/publish.py (this file is byte-identical every publish;
only the JSON spec and the content files change).

Core operation: insert one card (an HTML fragment read from a file) into a
page (usually index.html) immediately BEFORE or AFTER an anchor, driven by a
small JSON spec:

    {
      "file": "index.html",
      "anchor_text": "<article class=\"card\"><h3>Food, wine &amp; Lisbon</h3>",
      "anchor_regex": null,
      "position": "before",
      "card_file": "publish/card.html",
      "card_title": "What Cricket Has Taught Me About Leadership",
      "section_id": "beyond",
      "sentinels": ["What I stand for", "Beyond work", "</html>"]
    }

Exactly one of anchor_text / anchor_regex must be given. Paths in the spec
are resolved relative to the current working directory (the repo root in CI,
the rehearsal dir locally).

Design rules (each one kills a historical publish failure):
  * Anchor matching is whitespace-tolerant: runs of whitespace/newlines in
    both the document and the anchor collapse to a single space before
    matching. Nothing ever asserts on exact trailing newlines or on the
    byte layout of the whole file.
  * The anchor must match EXACTLY ONCE after normalisation. Zero or 2+
    matches = refuse. A patch is never applied "somewhere plausible".
  * Idempotency guard: if card_title is already present in the target file,
    refuse. A double-publish is impossible.
  * --dry-run runs the FULL pipeline — patch in memory, then every
    post-patch check — and writes nothing. --apply re-runs the identical
    pipeline and only then writes. There is no check that exists in apply
    but not in dry-run (that gap caused the Nov 8, 2026 failure, where a
    post-patch assert tripped on a stray trailing newline during the live
    run even though the rehearsal had "passed").
  * Post-patch checks are semantic, not byte-based: card_title present
    exactly once afterwards; every sentinel string still present; the patch
    adds zero 'data:image' / 'data:application' strings (media is never
    inlined); the insertion is a pure insertion of exactly the card text;
    if section_id is given, the insertion point lies inside that section.

Exit codes:
  0  success
  2  spec / IO error
  3  refusal (idempotency, anchor count, data: blob, bad card fragment)
  4  post-patch verification failed

Pure Python 3 standard library. No dependencies.
"""

import argparse
import json
import os
import re
import sys
import tempfile

DATA_MARKERS = ("data:image", "data:application")


# --------------------------------------------------------------------------
# Whitespace-tolerant matching
# --------------------------------------------------------------------------

def normalise_with_map(text):
    """Collapse every run of whitespace to a single space.

    Returns (collapsed_text, pos) where pos[i] is the index in the original
    text of collapsed character i. Leading whitespace produces no leading
    space; a collapsed space maps to the first whitespace char of its run.
    """
    chars = []
    pos = []
    prev_space = True  # strip leading whitespace
    for i, ch in enumerate(text):
        if ch.isspace():
            if not prev_space:
                chars.append(" ")
                pos.append(i)
                prev_space = True
        else:
            chars.append(ch)
            pos.append(i)
            prev_space = False
    return "".join(chars), pos


def normalise(text):
    return normalise_with_map(text)[0]


def find_anchor(text, spec):
    """Return (start, end) original-text offsets of the unique anchor match.

    Raises Refusal if the anchor matches zero or more than one time.
    """
    collapsed, pos = normalise_with_map(text)
    spans = []
    if spec.get("anchor_text"):
        needle = normalise(spec["anchor_text"]).strip()
        if not needle:
            raise Refusal("anchor_text is empty after whitespace normalisation")
        start = 0
        while True:
            j = collapsed.find(needle, start)
            if j < 0:
                break
            spans.append((j, j + len(needle)))
            start = j + 1
    else:
        # anchor_regex is matched against the whitespace-normalised text;
        # whitespace runs inside the pattern collapse to a single space.
        pattern = re.sub(r"\s+", " ", spec["anchor_regex"])
        spans = [(m.start(), m.end()) for m in re.finditer(pattern, collapsed)]
    if len(spans) == 0:
        raise Refusal("anchor matched 0 times (after whitespace normalisation); refusing")
    if len(spans) > 1:
        raise Refusal(
            "anchor matched %d times (after whitespace normalisation); "
            "refusing — the anchor must be unique" % len(spans)
        )
    a, b = spans[0]
    return pos[a], pos[b - 1] + 1


class Refusal(Exception):
    """A guard refused the publish (exit 3)."""


class VerifyFailure(Exception):
    """A post-patch semantic check failed (exit 4)."""


# --------------------------------------------------------------------------
# Pipeline (shared verbatim by --dry-run and --apply)
# --------------------------------------------------------------------------

def run_pipeline(spec):
    """Run the full patch + verification pipeline in memory.

    Returns a report dict. Raises Refusal / VerifyFailure / ValueError.
    """
    target_path = spec["file"]
    card_path = spec["card_file"]
    card_title = spec["card_title"]
    position = spec.get("position", "after")

    if position not in ("before", "after"):
        raise ValueError("spec.position must be 'before' or 'after'")
    if bool(spec.get("anchor_text")) == bool(spec.get("anchor_regex")):
        raise ValueError("spec must give exactly one of anchor_text / anchor_regex")
    if not card_title:
        raise ValueError("spec.card_title is required")

    with open(target_path, encoding="utf-8") as fh:
        original = fh.read()
    with open(card_path, encoding="utf-8") as fh:
        card = fh.read()

    report = {
        "file": target_path,
        "card_file": card_path,
        "card_title": card_title,
        "position": position,
        "size_before": len(original.encode("utf-8")),
    }

    # --- Card fragment hygiene -------------------------------------------
    lowered = card.lower()
    for marker in DATA_MARKERS:
        if marker in lowered:
            raise Refusal(
                "card fragment contains a '%s' blob — media/documents are "
                "never inlined into a page; ship them as standalone files" % marker
            )
    title_in_card = card.count(card_title)
    if title_in_card != 1:
        raise Refusal(
            "card_title must appear exactly once in the card fragment; "
            "found %d" % title_in_card
        )

    # --- Idempotency guard -------------------------------------------------
    if card_title in original:
        raise Refusal(
            "card_title %r is already present in %s — this looks like a "
            "double-publish; refusing" % (card_title, target_path)
        )

    # --- Locate anchor (whitespace-tolerant, must be unique) ---------------
    a_start, a_end = find_anchor(original, spec)
    insert_at = a_start if position == "before" else a_end
    report["anchor_offset"] = [a_start, a_end]
    report["insert_offset"] = insert_at
    report["insert_line"] = original.count("\n", 0, insert_at) + 1

    # --- Optional section containment --------------------------------------
    section_id = spec.get("section_id")
    if section_id:
        sec = re.search(
            r'<section[^>]*\bid="%s"[^>]*>' % re.escape(section_id), original
        )
        if not sec:
            raise Refusal("section_id %r not found in %s" % (section_id, target_path))
        sec_end = original.find("</section>", sec.end())
        if sec_end < 0:
            raise Refusal("section %r has no closing </section>" % section_id)
        if not (sec.start() <= insert_at <= sec_end):
            raise Refusal(
                "insertion point (offset %d) is not inside section #%s "
                "(%d..%d); refusing" % (insert_at, section_id, sec.start(), sec_end)
            )
        report["section_id"] = section_id

    # --- Patch (pure insertion of exactly the card text) --------------------
    patched = original[:insert_at] + card + original[insert_at:]
    report["size_after"] = len(patched.encode("utf-8"))
    report["size_delta"] = report["size_after"] - report["size_before"]

    # --- Post-patch semantic verification -----------------------------------
    checks = {}

    n_title = patched.count(card_title)
    checks["card_title_present_exactly_once"] = n_title == 1
    if n_title != 1:
        raise VerifyFailure(
            "after patching, card_title appears %d times (expected exactly 1)" % n_title
        )

    sentinels = spec.get("sentinels", [])
    norm_patched = normalise(patched)
    missing = [s for s in sentinels if normalise(s) not in norm_patched]
    checks["sentinels_present"] = not missing
    checks["sentinels_checked"] = sentinels
    if missing:
        raise VerifyFailure("sentinel strings missing after patch: %r" % missing)

    for marker in DATA_MARKERS:
        before_n = original.lower().count(marker)
        after_n = patched.lower().count(marker)
        checks["no_new_%s" % marker.replace(":", "_")] = after_n == before_n
        if after_n != before_n:
            raise VerifyFailure(
                "patch changed the count of '%s' strings (%d -> %d); "
                "inlined media is forbidden" % (marker, before_n, after_n)
            )

    # Pure-insertion proof: removing the inserted card restores the original.
    checks["pure_insertion"] = (
        patched[:insert_at] == original[:insert_at]
        and patched[insert_at + len(card):] == original[insert_at:]
        and patched[insert_at:insert_at + len(card)] == card
    )
    if not checks["pure_insertion"]:
        raise VerifyFailure("patched text is not a pure insertion of the card")

    report["checks"] = checks
    report["patched"] = patched
    return report


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--spec", required=True, help="path to the JSON publish spec")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true",
                      help="run the full pipeline + all checks, write nothing")
    mode.add_argument("--apply", action="store_true",
                      help="run the full pipeline + all checks, then write")
    args = ap.parse_args(argv)

    try:
        with open(args.spec, encoding="utf-8") as fh:
            spec = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print("ERROR: cannot read spec %s: %s" % (args.spec, exc), file=sys.stderr)
        return 2

    try:
        report = run_pipeline(spec)
    except Refusal as exc:
        print("REFUSED: %s" % exc, file=sys.stderr)
        return 3
    except VerifyFailure as exc:
        print("VERIFY FAILED: %s" % exc, file=sys.stderr)
        return 4
    except (ValueError, OSError, KeyError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    patched = report.pop("patched")
    mode_name = "dry-run" if args.dry_run else "apply"
    print("publish.py [%s] OK" % mode_name)
    print("  file:          %s" % report["file"])
    print("  card:          %s (%r)" % (report["card_file"], report["card_title"]))
    print("  position:      %s anchor at chars %d..%d (line %d)"
          % (report["position"], report["anchor_offset"][0],
             report["anchor_offset"][1], report["insert_line"]))
    if "section_id" in report:
        print("  section:       #%s (insertion verified inside)" % report["section_id"])
    print("  size:          %d -> %d bytes (delta %+d)"
          % (report["size_before"], report["size_after"], report["size_delta"]))
    for name, ok in report["checks"].items():
        if isinstance(ok, bool):
            print("  check %-36s %s" % (name, "PASS" if ok else "FAIL"))
    print("RESULT " + json.dumps({k: v for k, v in report.items()
                                  if k != "checks"}, sort_keys=True))

    if args.apply:
        # Atomic write: temp file in the same directory, then replace.
        target = report["file"]
        directory = os.path.dirname(os.path.abspath(target))
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".publish-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(patched)
            os.replace(tmp, target)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        print("  wrote:         %s" % target)
    else:
        print("  wrote:         nothing (dry-run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
