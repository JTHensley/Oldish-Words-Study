#!/usr/bin/env python3
"""Mechanical checks for entries.csv, register.csv and grammar.csv.

Usage:
    python3 check.py --allow-file NAME [--allow-file NAME ...] [--allow-remove FILE:KEY ...]
    python3 check.py --dir PATH      # check the files in PATH
    python3 check.py --base REF      # compare against REF (default origin/main)
    python3 check.py --no-base       # debugging only: the run is then NOT a valid pre-merge run

The comparison with the base is required. If it cannot be done, that is an ERROR.
--allow-file NAME     (repeatable) a file this task may change. Any other changed file is an ERROR;
                      with no --allow-file, no changed file is allowed.
--allow-remove F:KEY  (repeatable) a row that this task may delete, e.g. entries.csv:3. Any other
                      removed row is an ERROR.

Exit status is 0 only if there are no errors. Warnings and notes do not fail the run.
Standard library only. Anyone (any assistant or person) can run it.

It checks structure and rules that a program can decide, and, for new or changed HIT quotes whose
source_url is on a fetchable site, that the quote appears on the page. It cannot check that a quote
is faithful to a source it cannot fetch, or that a tier was really the author's decision; those need
a person or a second reader.
"""
import argparse
import csv
import datetime
import html as htmllib
import io
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.parse
import urllib.request

# Sites whose pages this script will fetch to check a quote against. Edit this list to add more.
FETCHABLE_HOSTS = [
    "artflsrv04.uchicago.edu",
    "bosworthtoller.com",
]
FETCH_TIMEOUT_SECONDS = 20

ENTRIES_HEADER = ("id,term,modern_spelling,historical_spelling,era,date,status,job,definition,"
                  "usage_notes,quote,source,locator,found_by,last_verified_by,"
                  "last_verified_date,change_note,date_added,source_url").split(",")
REGISTER_HEADER = ("reg_id,entry,concepts,type,pos,entry_id,tier,status,chapter,era_range,"
                   "features,notes,date_added").split(",")
GRAMMAR_HEADER = "gram_id,entry,description,entry_id,chapter,era_range,notes,date_added".split(",")

ERA_RE = re.compile(r"^L?(OE|ME|EME|ModE)$")
STATUSES = {"HIT", "BUILD"}
TYPES = {"word", "phrase", "construction"}

USER_NAME = "User"

errors, warnings, notes = [], [], []
missing_dates = []  # ids of rows verified by someone other than "User" with no date


def err(msg):
    errors.append(msg)


def parse_date(s):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return None
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return None


def load(text_bytes, name):
    """Return (header, [(line_no, row_dict)]) or None. Records errors."""
    try:
        text = text_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        err(f"{name}: not valid UTF-8 ({e})")
        return None
    if text.startswith("﻿"):
        err(f"{name}: starts with a byte-order mark; save as plain UTF-8")
        text = text[1:]
    try:
        raw = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except csv.Error as e:
        err(f"{name}: not valid CSV ({e})")
        return None
    if not raw:
        err(f"{name}: file is empty")
        return None
    header = raw[0]
    rows = []
    for i, cells in enumerate(raw[1:], start=2):
        if cells == []:
            continue  # blank line
        if len(cells) != len(header):
            err(f"{name} record {i}: has {len(cells)} fields, header has {len(header)}")
            continue
        rows.append((i, dict(zip(header, cells))))
    return header, rows


def read_file(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError as e:
        err(f"{os.path.basename(path)}: cannot read ({e})")
        return None


def check_dates(name, who, r, cols):
    for c in cols:
        v = r.get(c, "")
        if v and not parse_date(v):
            err(f"{name} {who}: {c} '{v}' is not a valid YYYY-MM-DD date")


def check_entries(header, rows):
    name = "entries.csv"
    if header != ENTRIES_HEADER:
        err(f"{name}: header row is not exactly the expected one.\n    expected: {','.join(ENTRIES_HEADER)}\n    found:    {','.join(header)}")
        return {}
    ids = {}
    for line, r in rows:
        who = f"id {r['id'] or '(blank)'} (record {line})"
        if not r["id"]:
            err(f"{name} record {line}: id is empty")
        elif r["id"] in ids:
            err(f"{name} {who}: duplicate id")
        else:
            ids[r["id"]] = r
        if not r["term"]:
            err(f"{name} {who}: term is empty")
        if r["status"] not in STATUSES:
            err(f"{name} {who}: status '{r['status']}' must be HIT or BUILD")
        if r["status"] == "HIT":
            for c in ("quote", "source", "locator"):
                if not r[c].strip():
                    err(f"{name} {who}: HIT row has empty {c}")
        if not ERA_RE.match(r["era"]):
            err(f"{name} {who}: era '{r['era']}' must be OE, ME, EME or ModE (optional L prefix)")
        if not r["found_by"]:
            err(f"{name} {who}: found_by is empty")
        if not parse_date(r["date_added"]):
            err(f"{name} {who}: date_added '{r['date_added']}' is not a valid YYYY-MM-DD date")
        check_dates(name, who, r, ["last_verified_date"])
        if r["last_verified_by"] and r["last_verified_by"] != USER_NAME and not r["last_verified_date"]:
            err(f"{name} {who}: last_verified_by is '{r['last_verified_by']}' but last_verified_date "
                f"is empty (a date is required unless last_verified_by is exactly '{USER_NAME}')")
            missing_dates.append(f"{name} id {r['id']}")
        if r["last_verified_date"] and not r["last_verified_by"]:
            err(f"{name} {who}: last_verified_date is set but last_verified_by is empty")
        if r["change_note"] and not r["last_verified_by"]:
            err(f"{name} {who}: change_note is set but the row is not marked verified")
    verified = [i for i, r in ids.items() if r["last_verified_by"]]
    if verified:
        notes.append("entries.csv: rows marked verified (a person must have opened the source "
                     "and compared the quote): " + ", ".join(verified))
    return ids


def check_register(header, rows, entry_ids, gram_ids):
    name = "register.csv"
    if header != REGISTER_HEADER:
        err(f"{name}: header row is not exactly the expected one.\n    expected: {','.join(REGISTER_HEADER)}\n    found:    {','.join(header)}")
        return
    seen = set()
    tiered = []
    for line, r in rows:
        who = f"reg_id {r['reg_id'] or '(blank)'} (record {line})"
        if not r["reg_id"]:
            err(f"{name} record {line}: reg_id is empty")
        elif r["reg_id"] in seen:
            err(f"{name} {who}: duplicate reg_id")
        seen.add(r["reg_id"])
        for c in ("concepts", "entry"):
            if not r[c]:
                err(f"{name} {who}: {c} is empty")
        if r["type"] not in TYPES:
            err(f"{name} {who}: type '{r['type']}' must be word, phrase or construction")
        if r["entry_id"] and r["entry_id"] not in entry_ids:
            err(f"{name} {who}: entry_id '{r['entry_id']}' matches no id in entries.csv")
        if not parse_date(r["date_added"]):
            err(f"{name} {who}: date_added '{r['date_added']}' is not a valid YYYY-MM-DD date")
        if gram_ids is not None:
            for v in r["features"].split(";"):
                v = v.strip()
                if v and v not in gram_ids:
                    err(f"{name} {who}: features value '{v}' matches no gram_id in grammar.csv")
        if r["tier"]:
            tiered.append(r["reg_id"])
    if tiered:
        notes.append("register.csv: rows with a tier set (only the author may decide a tier; "
                     "confirm each came from the author): reg_id " + ", ".join(tiered))


def check_grammar(header, rows, entry_ids):
    """Returns the set of gram_ids, or None if the header is wrong (already an ERROR)."""
    name = "grammar.csv"
    if header != GRAMMAR_HEADER:
        err(f"{name}: header row is not exactly the expected one.\n    expected: {','.join(GRAMMAR_HEADER)}\n    found:    {','.join(header)}")
        return None
    seen = set()
    for line, r in rows:
        who = f"gram_id {r['gram_id'] or '(blank)'} (record {line})"
        if not r["gram_id"]:
            err(f"{name} record {line}: gram_id is empty")
        elif r["gram_id"] in seen:
            err(f"{name} {who}: duplicate gram_id")
        seen.add(r["gram_id"])
        if r["entry_id"] and r["entry_id"] not in entry_ids:
            err(f"{name} {who}: entry_id '{r['entry_id']}' matches no id in entries.csv")
        if not parse_date(r["date_added"]):
            err(f"{name} {who}: date_added '{r['date_added']}' is not a valid YYYY-MM-DD date")
    return seen


def git_show(directory, ref, fname):
    try:
        out = subprocess.run(["git", "-C", directory, "show", f"{ref}:{fname}"],
                             capture_output=True, check=True)
        return out.stdout
    except (OSError, subprocess.CalledProcessError):
        return None


def file_absent_in_base(directory, ref, fname):
    """True only if ref resolves to a commit and fname is not in its tree."""
    try:
        subprocess.run(["git", "-C", directory, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
                       capture_output=True, check=True)
        out = subprocess.run(["git", "-C", directory, "ls-tree", "--full-tree", "--name-only", ref, "--", fname],
                             capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return False
    return out.strip() == b""


def compare(directory, ref, fname, key, new_rows, protected, review, allow_remove, absent_ok=False):
    """Report rows added / removed / changed relative to ref.

    Returns the base rows as {key: row dict}, or None if the comparison could not be done
    (which is recorded as an ERROR).
    """
    base_bytes = git_show(directory, ref, fname)
    if base_bytes is None and absent_ok and file_absent_in_base(directory, ref, fname):
        keys = [r[key] for _, r in new_rows]
        notes.append(f"{fname} compared with {ref}: file is not in {ref}, so all rows are new"
                     + (f"; added {key}: " + ", ".join(keys) if keys else " (no rows)"))
        return {}
    if base_bytes is None:
        err(f"{fname}: cannot compare with {ref}: could not read {fname} at {ref} "
            f"(no git, no {ref}, or the file is missing there; try: git fetch origin)")
        return None
    try:
        base_raw = list(csv.reader(io.StringIO(base_bytes.decode("utf-8"), newline="")))
    except (UnicodeDecodeError, csv.Error) as e:
        err(f"{fname}: cannot compare with {ref}: the {ref} version is unreadable ({e})")
        return None
    if not base_raw:
        err(f"{fname}: cannot compare with {ref}: the {ref} version is empty")
        return None
    bh = base_raw[0]
    if key not in bh:
        err(f"{fname}: cannot compare with {ref}: the {ref} version has no '{key}' column")
        return None
    old = {}
    for cells in base_raw[1:]:
        if len(cells) == len(bh):
            d = dict(zip(bh, cells))
            old[d.get(key, "")] = d
    new = {r[key]: r for _, r in new_rows}
    added = [k for k in new if k not in old]
    removed = [k for k in old if k not in new]
    changed = []
    for k in new:
        if k in old:
            diffs = [c for c in new[k] if c in old[k] and new[k][c] != old[k][c]]
            if diffs:
                changed.append((k, diffs))
    lines = []
    if added:
        lines.append(f"added {key}: " + ", ".join(added))
    if removed:
        lines.append(f"REMOVED {key}: " + ", ".join(removed))
        for k in removed:
            if (fname, k) in allow_remove:
                allow_remove_used.add((fname, k))
                notes.append(f"{fname} {key} {k}: row removed, allowed by --allow-remove {fname}:{k}")
            else:
                err(f"{fname} {key} {k}: row exists in {ref} but was removed "
                    f"(if the task names this deletion, use --allow-remove {fname}:{k})")
    for k, diffs in changed:
        lines.append(f"changed {key} {k}: " + ", ".join(diffs))
        for c in diffs:
            if c in protected:
                err(f"{fname} {key} {k}: protected field '{c}' was changed "
                    f"('{old[k][c]}' -> '{new[k][c]}')")
            elif c in review:
                warnings.append(f"{fname} {key} {k}: existing {c} changed "
                                f"('{old[k][c]}' -> '{new[k][c]}'); confirm this was intended "
                                f"(a correction needs a change_note)")
    notes.append(f"{fname} compared with {ref}: " + ("; ".join(lines) if lines else "no row changes"))
    return old


allow_remove_used = set()


def check_changed_files(directory, ref, allow_files):
    """Every file that differs from the merge-base with ref must be named with --allow-file."""
    def git(*args):
        return subprocess.run(["git", "-C", directory, *args], capture_output=True,
                              check=True).stdout.decode("utf-8", "replace")
    try:
        mb = git("merge-base", ref, "HEAD").strip()
        changed = set(x for x in git("diff", "--name-only", "--relative", "-z", mb).split("\0") if x)
        changed |= set(x for x in git("ls-files", "--others", "--exclude-standard", "-z").split("\0") if x)
    except (OSError, subprocess.CalledProcessError) as e:
        detail = getattr(e, "stderr", b"")
        detail = detail.decode("utf-8", "replace").strip() if detail else str(e)
        err(f"could not list the files changed compared with {ref}: {detail}")
        return
    changed = sorted(changed)
    notes.append(f"files changed compared with {ref}: " + (", ".join(changed) if changed else "(none)"))
    for f in changed:
        if f not in allow_files:
            err(f"changed file '{f}' is not allowed (use --allow-file {f} only if the task says "
                f"this file may change)")


# ---- quote fetch-and-match -------------------------------------------------------------------

def norm_ws(s):
    """NFC-normalise and collapse all whitespace to single spaces."""
    return " ".join(unicodedata.normalize("NFC", s).split())


def json_strings(value):
    """Every string value in a parsed JSON document, at any depth, in document order."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from json_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from json_strings(v)


def page_source(body):
    """If the body is JSON, the string values joined by single spaces (this decodes \\n, \\" and
    \\uXXXX escapes); otherwise the body itself, treated as HTML."""
    try:
        parsed = json.loads(body)
    except ValueError:
        return body
    return " ".join(json_strings(parsed))


def page_texts(page_html):
    """Plain-text versions of a page: tags -> a space, and tags -> nothing (for inline markup)."""
    page_html = page_source(page_html)
    s = re.sub(r"(?is)<(script|style)\b.*?</\1\s*>", " ", page_html)
    s = re.sub(r"(?s)<!--.*?-->", " ", s)
    return [norm_ws(htmllib.unescape(re.sub(r"(?s)<[^>]*>", repl, s))) for repl in (" ", "")]


def quote_pieces(quote):
    """Split on '...' or the ellipsis character; each non-empty piece must appear on the page."""
    return [p for p in (norm_ws(x) for x in re.split(r"\.\.\.|…", quote)) if p]


def page_text_length(page_html):
    """Number of characters of page text that match_quote searches (tags replaced by spaces)."""
    return len(page_texts(page_html)[0])


def match_quote(quote, page_html):
    """Return (True, []) if the quote appears in the page text, else (False, [missing pieces])."""
    pieces = quote_pieces(quote)
    if not pieces:
        return False, ["(the quote has no text to match)"]
    best = None
    for text in page_texts(page_html):
        missing = [p for p in pieces if p not in text]
        if not missing:
            return True, []
        if best is None or len(missing) < len(best):
            best = missing
    return False, best


def fetch_page(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Oldish-Words-Study check.py)"})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_SECONDS) as resp:
        data = resp.read()
    return data.decode("utf-8")


def is_web_address(u):
    return u.startswith("http://") or u.startswith("https://")


def check_source_urls(rows, base_old):
    """source_url rules for entries.csv; fetches and matches quotes where it can."""
    name = "entries.csv"
    if base_old is None:
        return  # the comparison failed; that is already an ERROR
    unrecorded = []
    for line, r in rows:
        if r["status"] != "HIT":
            continue
        who = f"id {r['id']} (record {line})"
        url = r["source_url"]
        old = base_old.get(r["id"])
        is_new = old is None or old.get("quote") != r["quote"]
        needs = is_new and r["found_by"] != USER_NAME
        if not needs:
            if not is_new and not url:
                unrecorded.append(r["id"])
            elif url and not is_web_address(url):
                warnings.append(f"{name} {who}: source_url '{url}' does not start with http:// or https://")
            continue
        if not url:
            err(f"{name} {who}: new or changed HIT quote needs source_url (the exact address opened "
                f"to find the quote)")
            continue
        if not is_web_address(url):
            err(f"{name} {who}: source_url '{url}' must start with http:// or https://")
            continue
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        if host not in FETCHABLE_HOSTS:
            notes.append(f"{name} {who}: host {host} is not machine-checkable, needs a person to compare "
                         f"the quote with {url}")
            continue
        try:
            page = fetch_page(url)
        except Exception as e:  # network, timeout, HTTP error, bad encoding
            err(f"{name} {who}: quote could not be checked: fetching {url} failed ({type(e).__name__}: {e})")
            continue
        ok, missing = match_quote(r["quote"], page)
        if ok:
            notes.append(f"{name} {who}: quote found on {url}")
        else:
            shown = "; ".join("'" + (m if len(m) <= 80 else m[:77] + "...") + "'" for m in missing)
            err(f"{name} {who}: quote not found on {url} (missing: {shown}; "
                f"{page_text_length(page)} characters of page text were searched)")
    if unrecorded:
        notes.append(f"{name}: existing HIT rows with a blank source_url: " + ", ".join(unrecorded))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--no-base", action="store_true",
                    help="debugging only; adds an ERROR because the run is not a valid pre-merge run")
    ap.add_argument("--allow-file", action="append", default=[], metavar="NAME",
                    help="a file the task may change (repeatable)")
    ap.add_argument("--allow-remove", action="append", default=[], metavar="FILE:KEY",
                    help="a row the task may delete, e.g. entries.csv:3 (repeatable)")
    a = ap.parse_args()

    allow_remove = set()
    for spec in a.allow_remove:
        fname, sep, key = spec.rpartition(":")
        if not sep or not fname or not key:
            err(f"--allow-remove '{spec}' must look like FILE:KEY, for example entries.csv:3")
        else:
            allow_remove.add((fname, key))

    ebytes = read_file(os.path.join(a.dir, "entries.csv"))
    rbytes = read_file(os.path.join(a.dir, "register.csv"))
    gbytes = read_file(os.path.join(a.dir, "grammar.csv"))
    e = load(ebytes, "entries.csv") if ebytes is not None else None
    r = load(rbytes, "register.csv") if rbytes is not None else None
    g = load(gbytes, "grammar.csv") if gbytes is not None else None
    entry_ids = check_entries(*e) if e else {}
    gram_ids = check_grammar(g[0], g[1], entry_ids) if g else None
    if r:
        check_register(r[0], r[1], entry_ids, gram_ids)

    base_entries = None
    if a.no_base:
        err("--no-base was used: no comparison with the base was made, so this run is not a valid "
            "pre-merge run")
    else:
        if e and e[0] == ENTRIES_HEADER:
            base_entries = compare(a.dir, a.base, "entries.csv", "id", e[1],
                                   protected={"id", "found_by", "date_added"},
                                   review={"term", "era", "date", "status", "quote", "source", "locator",
                                           "source_url"},
                                   allow_remove=allow_remove)
        else:
            err("entries.csv: the comparison with the base was not made because the file did not "
                "load or its header is wrong")
        if r and r[0] == REGISTER_HEADER:
            compare(a.dir, a.base, "register.csv", "reg_id", r[1],
                    protected={"reg_id", "date_added"},
                    review={"entry", "concepts", "type", "entry_id", "tier", "status", "features"},
                    allow_remove=allow_remove)
        else:
            err("register.csv: the comparison with the base was not made because the file did not "
                "load or its header is wrong")
        if g and g[0] == GRAMMAR_HEADER:
            compare(a.dir, a.base, "grammar.csv", "gram_id", g[1],
                    protected={"gram_id", "date_added"},
                    review={"entry", "description", "entry_id"},
                    allow_remove=allow_remove, absent_ok=True)
        else:
            err("grammar.csv: the comparison with the base was not made because the file did not "
                "load or its header is wrong")
        check_changed_files(a.dir, a.base, set(a.allow_file))
        for fname, key in sorted(allow_remove - allow_remove_used):
            warnings.append(f"--allow-remove {fname}:{key} was given but that row was not removed")

    if e and e[0] == ENTRIES_HEADER:
        check_source_urls(e[1], base_entries)

    for n in notes:
        print("NOTE   ", n)
    for w in warnings:
        print("WARNING", w)
    for x in errors:
        print("ERROR  ", x)
    if missing_dates:
        print()
        print("MISSING DATES:")
        for m in missing_dates:
            print("  " + m)
        print("Stop and report this list. Do not fill in the dates.")
    print()
    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s).")
        print("Not checked by this script: quote fidelity for sources it cannot fetch, who decided a tier.")
        return 1
    print(f"OK: no errors, {len(warnings)} warning(s).")
    print("Not checked by this script: quote fidelity for sources it cannot fetch, who decided a tier.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
