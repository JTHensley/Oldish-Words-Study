# Oldish-Words-Study
Historical English Research Database

A small research database of historically attested English words and phrases (Old, Middle, Early Modern and Modern English), kept for a novelist's constructed register.

- `entries.csv` holds the data, one row per entry.
- `index.html` is a single self-contained page that loads `entries.csv` from the same folder and lets you search and filter it. It makes no other network calls. Browsers block `fetch` on `file://` pages, so view it through a web server (for example `python3 -m http.server`) rather than by double-clicking.

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
| `found_by` | Who located the entry. |
| `checked_by` | Who verified it against the source. Empty until someone has. |
| `date_added` | Date the row was added, `YYYY-MM-DD`. |

Empty fields stay empty. Do not guess a definition, spelling or date.

## HIT and BUILD

- **HIT**: the term was found attested in a named source. A HIT row must have a non-empty `quote`, `source` and `locator`. If any of the three is missing, do not add the row.
- **BUILD**: the term was assembled and is not attested as a whole.

Never mix the two: a BUILD row is never presented as attested, and a HIT row is never assembled from parts.

## Rules for the data

- Copy quotes, spellings and dates exactly as the source gives them. Do not invent or "improve" them.
- Outside a quotation, keep archaic second-person pronouns and archaic verb endings out of every term and note. Write notes in plain modern English.

## Adding a row

1. Open `entries.csv` and add a line at the end, with fields in the order of the header row.
2. Give it the next unused `id`.
3. Set `status` to `HIT` or `BUILD`. For `HIT`, fill `quote`, `source` and `locator`.
4. Wrap any field containing a comma, a line break or a double quote in double quotes, and double any quote inside it (`"` becomes `""`).
5. Set `found_by` and `date_added`. Leave `checked_by` empty until the entry has been verified.
6. Reload `index.html` and confirm the new card appears.
