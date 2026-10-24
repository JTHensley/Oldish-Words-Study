#!/usr/bin/env python3
"""Mechanical checks for entries.csv and register.csv.

Usage:
    python3 check.py                 # check the files next to this script
    python3 check.py --dir PATH      # check the files in PATH
    python3 check.py --base REF      # also compare against REF (default origin/main)
    python3 check.py --no-base       # skip the comparison

Exit status is 0 only if there are no errors. Warnings and notes do not fail the run.
Standard library only. Anyone (any assistant or person) can run it.

It checks structure and rules that a program can decide. It cannot check that a quote is
faithful to its source, that a tier was really the author's decision, or the style rule on
archaic verb endings; those need a person or a second reader.
"""
import argparse
import csv
import datetime
import io
import os
import re
import subprocess
import sys

ENTRIES_HEADER = ("id,term,modern_spelling,historical_spelling,era,date,status,job,definition,"
                  "usage_notes,quote,source,locator,found_by,last_verified_by,"
                  "last_verified_date,change_note,date_added").split(",")
REGISTER_HEADER = ("reg_id,concept,option,type,entry_id,tier,status,chapter,decided_by,"
                   "decided_date,notes,date_added").split(",")

ERA_RE = re.compile(r"^L?(OE|ME|EME|ModE)$")
STATUSES = {"HIT", "BUILD"}
TYPES = {"word", "phrase", "construction"}
# Archaic second-person forms must not appear outside a quotation (README rule).
ARCHAIC_RE = re.compile(r"\b(thee|thou|thy|thine|ye)\b", re.IGNORECASE)

errors, warnings, notes = [], [], []


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


def check_archaic(name, who, r, cols):
    for c in cols:
        m = ARCHAIC_RE.search(r.get(c, ""))
        if m:
            err(f"{name} {who}: archaic form '{m.group(0)}' in {c} (not allowed outside a quotation)")


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
        if r["last_verified_by"] and not r["last_verified_date"]:
            err(f"{name} {who}: last_verified_by is set but last_verified_date is empty")
        if r["last_verified_date"] and not r["last_verified_by"]:
            err(f"{name} {who}: last_verified_date is set but last_verified_by is empty")
        if r["change_note"] and not r["last_verified_by"]:
            err(f"{name} {who}: change_note is set but the row is not marked verified")
        check_archaic(name, who, r, ["term", "modern_spelling", "historical_spelling", "job",
                                     "definition", "usage_notes", "change_note"])
    verified = [i for i, r in ids.items() if r["last_verified_by"]]
    if verified:
        notes.append("entries.csv: rows marked verified (a person must have opened the source "
                     "and compared the quote): " + ", ".join(verified))
    return ids


def check_register(header, rows, entry_ids):
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
        for c in ("concept", "option"):
            if not r[c]:
                err(f"{name} {who}: {c} is empty")
        if r["type"] not in TYPES:
            err(f"{name} {who}: type '{r['type']}' must be word, phrase or construction")
        if r["entry_id"] and r["entry_id"] not in entry_ids:
            err(f"{name} {who}: entry_id '{r['entry_id']}' matches no id in entries.csv")
        if not parse_date(r["date_added"]):
            err(f"{name} {who}: date_added '{r['date_added']}' is not a valid YYYY-MM-DD date")
        check_dates(name, who, r, ["decided_date"])
        check_archaic(name, who, r, ["notes"])
        if r["tier"]:
            tiered.append(r["reg_id"])
            if not (r["decided_by"] and r["decided_date"]):
                warnings.append(f"{name} {who}: tier is set but decided_by / decided_date is empty")
        if r["status"] and not (r["decided_by"] and r["decided_date"]):
            warnings.append(f"{name} {who}: status is set but decided_by / decided_date is empty")
    if tiered:
        notes.append("register.csv: rows with a tier set (only the author may decide a tier; "
                     "confirm each came from the author): reg_id " + ", ".join(tiered))


def git_show(directory, ref, fname):
    try:
        out = subprocess.run(["git", "-C", directory, "show", f"{ref}:{fname}"],
                             capture_output=True, check=True)
        return out.stdout
    except (OSError, subprocess.CalledProcessError):
        return None


def compare(directory, ref, fname, key, new_rows, protected, review):
    """Report rows added / removed / changed relative to ref. Returns False if base unavailable."""
    base_bytes = git_show(directory, ref, fname)
    if base_bytes is None:
        return False
    try:
        base_raw = list(csv.reader(io.StringIO(base_bytes.decode("utf-8"), newline="")))
    except (UnicodeDecodeError, csv.Error):
        notes.append(f"{fname}: could not read the {ref} version for comparison")
        return True
    if not base_raw:
        return True
    bh = base_raw[0]
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
        warnings.append(f"{fname}: rows removed compared with {ref}: " + ", ".join(removed))
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
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--no-base", action="store_true")
    a = ap.parse_args()

    ebytes = read_file(os.path.join(a.dir, "entries.csv"))
    rbytes = read_file(os.path.join(a.dir, "register.csv"))
    e = load(ebytes, "entries.csv") if ebytes is not None else None
    r = load(rbytes, "register.csv") if rbytes is not None else None
    entry_ids = check_entries(*e) if e else {}
    if r:
        check_register(r[0], r[1], entry_ids)

    if not a.no_base:
        done = []
        if e and e[0] == ENTRIES_HEADER:
            done.append(compare(a.dir, a.base, "entries.csv", "id", e[1],
                                protected={"id", "found_by", "date_added"},
                                review={"term", "era", "date", "status", "quote", "source", "locator"}))
        if r and r[0] == REGISTER_HEADER:
            done.append(compare(a.dir, a.base, "register.csv", "reg_id", r[1],
                                protected={"reg_id", "date_added"},
                                review={"concept", "option", "type", "entry_id", "tier", "status",
                                        "decided_by", "decided_date"}))
        if done and not all(done):
            warnings.append(f"could not read {a.base} from git, so the comparison with the previous "
                            f"version was skipped (try: git fetch origin, or use --base REF)")

    for n in notes:
        print("NOTE   ", n)
    for w in warnings:
        print("WARNING", w)
    for x in errors:
        print("ERROR  ", x)
    print()
    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s).")
        print("Not checked by this script: quote fidelity against the source, who decided a tier, "
              "and archaic -est/-eth verb endings.")
        return 1
    print(f"OK: no errors, {len(warnings)} warning(s).")
    print("Not checked by this script: quote fidelity against the source, who decided a tier, "
          "and archaic -est/-eth verb endings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
