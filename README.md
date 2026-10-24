# Oldish-Words-Study
Historical English Research Database

A small research database of historically attested English words and phrases (Old, Middle, Early Modern and Modern English), kept for a novelist's constructed register.

- `entries.csv` holds the data, one row per entry.
- `register.csv` holds the Wōdlund register (see below), one row per option.
- `index.html` is a single self-contained page that loads `entries.csv` and `register.csv` from the same folder and lets you search and filter them. A switch at the top moves between the Evidence view and the Wōdlund register view. It makes no other network calls. Browsers block `fetch` on `file://` pages, so view it through a web server (for example `python3 -m http.server`) rather than by double-clicking.

## Columns

| Column | Meaning |
|---|---|
| `id` | Unique number for the entry. |
| `term` | The word or phrase as studied. |
| `modern_spelling` | Modernised spelling, if one is supplied. |
| `historical_spelling` | Spelling as it appears in the historical record, if supplied. |
| `era` | `OE` Old English, `ME` Middle English, `EME` Early Modern English, `ModE` Modern English. Prefix `L` for a late period (for example `LME`). |
| `date` | Date or date range of the attestation, as given by the source. |
| `status` | `HIT` or `BUILD` (see below). |
| `job` | What the term does in a sentence or scene (for example, declaring someone an outlaw). |
| `definition` | Meaning, only where a source or the researcher states it. |
| `usage_notes` | Notes on use. |
| `quote` | The attested passage, copied exactly. |
| `source` | The named work or dictionary the quote comes from. |
| `locator` | Where in the source: record number, entry, chapter, page or similar. |
| `found_by` | Who first added the entry. Never overwritten. |
| `last_verified_by` | Name of the most recent person who verified the entry against its source (for example Claude, Grok, ChatGPT or the user). Empty until someone has. |
| `last_verified_date` | Date of that verification, `YYYY-MM-DD`. Empty until verified. Required whenever `last_verified_by` is set, except when `last_verified_by` is exactly `User`, where it may be blank or filled. |
| `change_note` | Short note on what a verifier corrected. Empty if nothing was changed. |
| `date_added` | Date the row was added, `YYYY-MM-DD`. |
| `source_url` | The exact web address that was opened to find the quote. Always the last column. Required for a new or changed HIT quote unless `found_by` is exactly `User`. Empty for rows added before this column existed; do not guess it. |

Empty fields stay empty. Do not guess a definition, spelling or date.

## HIT and BUILD

- **HIT**: the term was found attested in a named source. A HIT row must have a non-empty `quote`, `source` and `locator`. If any of the three is missing, do not add the row.
- **BUILD**: the term was assembled and is not attested as a whole.

Never mix the two: a BUILD row is never presented as attested, and a HIT row is never assembled from parts.

## Verification

- `found_by` keeps the name of whoever first added the entry. Never overwrite it.
- When someone verifies an entry, they must open the cited source and compare the quote against it. Only then may they set `last_verified_by` (their name, for example Claude, Grok, ChatGPT or the user) and `last_verified_date` (`YYYY-MM-DD`).
- If the entry is wrong, the verifier corrects the row, updates `last_verified_by` and `last_verified_date`, and writes a short `change_note` saying what was fixed. The earlier version stays in the Git history.
- If the source cannot be opened, do not set `last_verified_by`. Leave the fields as they were.

## Rules for the data

- Copy quotes, spellings and dates exactly as the source gives them. Do not invent or "improve" them.

## Adding a row

1. Open `entries.csv` and add a line at the end, with fields in the order of the header row.
2. Give it the next unused `id`.
3. Set `status` to `HIT` or `BUILD`. For `HIT`, fill `quote`, `source` and `locator`.
4. Wrap any field containing a comma, a line break or a double quote in double quotes, and double any quote inside it (`"` becomes `""`).
5. Set `found_by` and `date_added`. Leave `last_verified_by`, `last_verified_date` and `change_note` empty until the entry has been verified (see Verification).
6. Reload `index.html` and confirm the new card appears.

## Wōdlund register

`entries.csv` is the evidence layer: attested quotes with sources. `register.csv` is a second, separate layer: the Wōdlund register, which records the author's own diction choices. The author makes every decision recorded in it. **Nothing is added to the register without the author's decision.** The committed file starts as a header row only.

### Columns

| Column | Meaning |
|---|---|
| `reg_id` | Unique number for the row. |
| `concept` | The job or idea (for example "think about something"). Several rows can share a concept, one row per option the author uses. |
| `option` | The actual word, phrase or construction. |
| `type` | `word`, `phrase` or `construction`. |
| `entry_id` | The `id` of the matching row in `entries.csv`. Blank if no evidence row exists yet. |
| `tier` | One value, or blank. Blank means undecided. |
| `status` | Blank by default. Set only by the author. |
| `chapter` | Chapter reference where it is used, if known. |
| `decided_by` | Who recorded the author's decision. |
| `decided_date` | When it was recorded, `YYYY-MM-DD`. |
| `notes` | Free text. |
| `date_added` | Date the row was added, `YYYY-MM-DD`. |

### Tier rule

- A row holds exactly one tier, and the page filters by one tier at a time.
- Tier is decided only by the author. No assistant proposes, hints at, infers or changes a tier. A tier value entered without the author's instruction is an error to be reversed.
- The page builds its tier filter from the tier values that actually appear in `register.csv`, plus "All tiers" and "Undecided (blank)".

### Adding a row

1. Only add a row when the author has decided it. Do not invent or seed terms.
2. Open `register.csv` and add a line at the end, fields in the order of the header row, with the next unused `reg_id`.
3. Fill `concept`, `option` and `type`. Fill `tier`, `status`, `decided_by` and `decided_date` only from the author's stated decision, otherwise leave them empty.
4. Quote any field that contains a comma, quote or line break, and double any quote inside it.
5. Save as UTF-8 and keep the macron on Ō exactly.

### How `entry_id` links to the evidence

If `entry_id` is set, the register view looks up that `id` in `entries.csv` and shows the quote, source and locator under the option. If the id is not found, it shows "Evidence row not found". If `entry_id` is blank, it shows "No evidence row yet".

## Checking changes (for anyone adding or reviewing rows)

Run `git fetch origin` and then `python3 check.py` before pushing, and again when reviewing someone else's change. It needs only Python 3. A run only counts if the comparison with `origin/main` was made, which it shows as `compared with origin/main` NOTE lines.

```
python3 check.py --allow-file entries.csv --allow-file index.html --allow-remove entries.csv:3
```

- `--allow-file NAME` (repeatable): a file the task may change. The script lists every file that differs from the base, including staged, committed-on-branch and untracked files. Any changed file not named this way is an error. With no `--allow-file`, no changed file is allowed.
- `--allow-remove FILE:KEY` (repeatable): a row the task may delete, for example `entries.csv:3`. Any other removed row is an error; a removal named this way is only a note.
- `--base REF`: compare with REF instead of `origin/main`.
- `--no-base`: debugging only. It adds an error, because a run without the comparison is not a valid pre-merge run.

It reports errors (exit status 1, fix before pushing), warnings and notes. It checks:

- both files are valid UTF-8 CSV with exactly the expected header row, and every row has the right number of fields;
- `id` and `reg_id` values are present and unique;
- `status` is HIT or BUILD, and every HIT row has a quote, source and locator;
- `era`, dates and `type` are well-formed;
- verification: if `last_verified_by` is exactly `User`, `last_verified_date` may be blank or filled. If it is any other non-blank value, the date is required, and a blank date is an error that is also listed under a separate `MISSING DATES:` heading. A date with a blank `last_verified_by` is an error. A missing date must never be invented or filled in; stop and report the list;
- every non-blank `entry_id` in `register.csv` matches an `id` in `entries.csv`;
- the comparison with the base is required. If it cannot be done for any reason (no git, no `origin/main`, the file is missing there or unreadable), that is an error. It reports which rows were added, removed or changed. A row that exists in the base but not in the working file is an error unless named with `--allow-remove`. Changing `found_by` or `date_added` on an existing row is an error. Changes to an existing quote, source, locator, date, era, status, term, `source_url` or register value are warnings for a person to confirm;
- `source_url`: for HIT rows that are new compared with the base, or whose quote changed, and whose `found_by` is not exactly `User`, `source_url` is required and must start with `http://` or `https://`. Existing HIT rows with a blank `source_url` are listed in one note, not as errors. Rows whose `found_by` is `User` are never fetched;
- fetch-and-match: for the rows that need a `source_url`, if its host is on the `FETCHABLE_HOSTS` list at the top of `check.py` (currently `artflsrv04.uchicago.edu` and `bosworthtoller.com`), the script fetches the page (20-second timeout), strips tags, decodes entities, normalises to NFC and collapses whitespace, and requires the quote to appear in the page text. A quote containing `...` or `…` is split there and each piece must appear. A failed match is an error; a failed fetch (network, timeout, HTTP error) is an error saying the quote could not be checked. When the page is JSON, its text values are decoded before the quote is matched. The quote must appear in full in the page text, so a `source_url` should point to a page that shows the whole quote; a page that shows only a short window around the hit will fail a longer quote. A host not on the list gives a note, "not machine-checkable, needs a person". To add a site, add its hostname to `FETCHABLE_HOSTS`;
- which rows are marked verified and which register rows carry a tier, so a reviewer can confirm each one.

It cannot check that a quote matches a source it cannot fetch, or that a tier was the author's decision. A person or a second reviewer must check those. A passing run means the structure and rules it covers are fine, not that the content is correct.
