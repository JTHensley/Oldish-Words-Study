# Instructions for assistants working in this repository

This repository holds two data layers: `entries.csv` (evidence) and `register.csv` (the Wōdlund register, the author's own choices). Read `README.md` for the columns and rules.

## Do only what is asked
- Make only the changes the user has specified. Do not add, invent, "improve" or re-spell any quote, spelling, date or term.
- Never enter a tier, or change one, unless the user gave it. Never overwrite `found_by`.
- Do not change repository settings or GitHub Pages.

## Check your work before every push
Do this every time, and do not push until every item passes. ONE retry is allowed, and only to fix your own typing or formatting mistake (for example a malformed CSV line). Never change a quote, date, id, spelling or any supplied content to make a check pass. For any other failure, or any changed file outside the task, STOP and report the script's output exactly as printed. Do not merge.

0. **Run the script.** Run `git fetch origin`, then `python3 check.py` with one `--allow-file` for each file the task says you may change, and one `--allow-remove` for each deletion the task names. If the task does not say which files may change, stop and ask. Merge only if the output is `OK` and includes the `compared with origin/main` NOTE lines; a run without those lines does not count. Read every warning and note it prints, and deal with each one. The script covers the mechanical parts of items 3, 4 and 6 below, but it does not replace items 1, 2 and 5.
1. **Diff review.** Run `git diff` and read all of it. Confirm that only the intended files and rows changed, and that nothing else moved.
2. **Copy check.** Compare every quote, source, locator, date and spelling you entered against the text the user gave, character by character, including accents and macrons. Report any difference.
3. **CSV validity.** Parse each changed CSV with a CSV parser. Confirm that the header row is exactly as the README defines it, that every row has the same number of fields as the header, that the file is UTF-8, and that `id` / `reg_id` values are unique.
4. **Rule checks.**
   - Every HIT row has a non-empty `quote`, `source` and `locator`.
   - `status` is `HIT` or `BUILD` only.
   - `era` is one of the values in the README.
   - No row is marked verified unless a source was opened and compared. The verification fields (`last_verified_by`, `last_verified_date`, `change_note`) are written exactly as supplied. Whoever is named in them did the checking. Never enter your own name there.
   - If the script prints `MISSING DATES`, stop and report that list. Do not fill the dates in.
   - If the script cannot fetch a source address, report that and do not work around it.
   - In `register.csv`, any `tier` or `status` value comes from the author's stated decision, and every non-blank `entry_id` matches an `id` in `entries.csv`.
5. **Page check.** If `index.html` or a CSV changed, load the page in a headless browser at 375px width. Confirm that it loads, the cards or register options appear, search works, and there is no horizontal scroll.
6. **Untouched files.** Confirm that files you were not asked to change have no diff.

## Report
After pushing, tell the user which files and which rows changed, which checks you ran and their results, and anything you could not check. Do not say a check passed if you did not run it.
