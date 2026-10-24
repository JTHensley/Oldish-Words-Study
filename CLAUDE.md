# Instructions for assistants working in this repository

This repository holds two data layers: `entries.csv` (evidence) and `register.csv` (the Wōdlund register, the author's own choices). Read `README.md` for the columns and rules.

## Do only what is asked
- Make only the changes the user has specified. Do not add, invent, "improve" or re-spell any quote, spelling, date or term.
- Never enter a tier, or change one, unless the user gave it. Never overwrite `found_by`.
- Do not change repository settings or GitHub Pages.

## Check your work before every push
Do this every time, and do not push until every item passes. If a check fails, fix it and run all the checks again.

1. **Diff review.** Run `git diff` and read all of it. Confirm that only the intended files and rows changed, and that nothing else moved.
2. **Copy check.** Compare every quote, source, locator, date and spelling you entered against the text the user gave, character by character, including accents and macrons. Report any difference.
3. **CSV validity.** Parse each changed CSV with a CSV parser. Confirm that the header row is exactly as the README defines it, that every row has the same number of fields as the header, that the file is UTF-8, and that `id` / `reg_id` values are unique.
4. **Rule checks.**
   - Every HIT row has a non-empty `quote`, `source` and `locator`.
   - `status` is `HIT` or `BUILD` only.
   - `era` is one of the values in the README.
   - No row is marked verified unless a source was opened and compared.
   - In `register.csv`, any `tier` or `status` value comes from the author's stated decision, and every non-blank `entry_id` matches an `id` in `entries.csv`.
5. **Page check.** If `index.html` or a CSV changed, load the page in a headless browser at 375px width. Confirm that it loads, the cards or register options appear, search works, and there is no horizontal scroll.
6. **Untouched files.** Confirm that files you were not asked to change have no diff.

## Report
After pushing, tell the user which files and which rows changed, which checks you ran and their results, and anything you could not check. Do not say a check passed if you did not run it.
