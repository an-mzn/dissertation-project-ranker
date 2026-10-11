# Dissertation Project Ranker

**Short on time? Give this README to your AI assistant and ask it to guide you.** Copy this prompt, attaching the README and your project CSV (or giving a coding assistant access to this folder):

> Read this README and help me use Dissertation Project Ranker with my CSV. Check my operating system, Python setup, and CSV columns. Guide me through installation, configure the first notebook cell for my data, and show me how to rank projects and resume later. If you can edit files, make the configuration changes for me. Preserve my original CSV and saved progress; ask me only for information you cannot determine.

Compare two projects at a time to build a shortlist based on your preferences. Start with the fictional example, or use your own CSV.

## 1. Start the app

Download or clone this project. Install **Python 3.10+**, then open a terminal in the project folder.

**macOS / Linux:**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m jupyterlab
```

**Windows (PowerShell):**

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m jupyterlab
```

In JupyterLab, open **`Ranker.ipynb`** and select **Run → Run All Cells**. The last cell opens the ranking interface in your browser. If it does not open automatically, copy the printed local URL. Keep JupyterLab and the notebook kernel running while ranking. Use this locally on your computer; the browser interface is not a hosted multi-user service.

## Get a CSV from the university website

Already have a CSV? Skip to step 2. For the university page with clickable project rows:

1. Sign in and open the project list. Clear filters and show all rows if possible; the script only exports rows currently loaded on the page.
2. In Safari, enable **Safari → Settings → Advanced → Show features for web developers**, then open **Develop → Show JavaScript Console**. See [Apple’s developer-tools instructions](https://support.apple.com/en-ie/guide/safari/sfri20948/27.0/mac/27).
3. Open [the export script](scripts/export-university-projects.js), copy the **entire file**, paste it into the console, and press Enter once.
4. Leave the page open while it visits each project. Wait for **COMPLETE**, check the extracted count and any failures, and allow the `projects.csv` download. If rows are paginated, export each page separately and combine the CSVs with one header before ranking.
5. Move the download into `data/` and use these first-cell settings (keep the imports and save-path line):

```python
csv_location = Path("data/projects.csv")
has_header = True
delimiter = ","
columns = {"title": "title", "supervisor": "supervisor", "description": "description"}
```

The export keeps only title, supervisor, and full description; it omits student names, status, and other extra fields. It downloads locally and adds no generated metadata. It depends on the original university page layout; if no rows match or projects fail, ask your AI to adapt the script to the page before using an incomplete export.

## Optional: prepare with your AI

Want readable headings and metadata tailored to you? Use [these two copyable prompts](docs/prepare-with-ai.md): discuss your preferences, then ask your AI to produce `projects-prepared.csv` and matching notebook settings. Any AI assistant or existing conversation works. You choose which summaries, topics, tags, tools, difficulty, AI-assistance estimates, and draft ranks to add. Review the output; originals stay available on project cards. A new filename starts a separate session.

For a written preference draft, see the [fictional TXT example](examples/reference-rankings.txt) and its prompt in the guide. The app reads the resulting CSV, not the TXT.

## 2. Load your projects

Create a `data/` folder and put your CSV inside it. In the notebook's **first cell**, replace the example settings with your file path and exact column headers:

```python
csv_location = Path("data/my-projects.csv")
has_header = True
delimiter = ","
columns = {
    "title": "Project name",
    "supervisor": "Supervisor",
    "description": "Brief",
}
```

Leave the imports and `save_path = session_path(csv_location)` line in place. Run all cells again.

- **Required:** at least two projects, each with a title and a unique supervisor/title combination. Save the CSV as UTF-8.
- **No header row?** Set `has_header = False` and use zero-based positions, e.g. `columns = {"supervisor": 0, "title": 1, "description": 2}`.
- **Optional columns:** `supervisor`, `description`, `tags`, `summary`, `tools`, `difficulty`, `ai_assistance`, `readable_description`, `topics`, `draft_rank`. Map only columns that exist. Tags and topics use semicolons, e.g. `Web;Accessibility`; ratings are numbers from 1 to 10. Draft ranks are unique positive integers (1 = strongest preference). Blank metadata is hidden.

Any subjects, supervisors, and tags work. Projects start neutral by default. Optional `use_draft_prior = True` gently biases starting preferences using supplied draft ranks. Difficulty, AI-assistance ratings, topics, and tools do not affect scores.

## 3. Rank and return later

Choose **A** or **B** (click a card in the browser), or **Both** to endorse both. Use **Skip**, **Back** to undo, **Show top 20**, and **Stop / Resume** as needed. The app also pauses when its comparison budget is reached or its shortlist looks stable; you can resume for more comparisons.

Progress saves automatically beside your CSV as `<filename>.ranker-session.json`, with a `.bak` recovery copy. To return, reopen the same notebook with the same CSV and run all cells. Keep both save files. If you change or reorder projects, use a new CSV filename to start a separate session; an incompatible checkpoint will be rejected.

`data/`, `personal/`, and session files are Git-ignored. The optional `personal/` archive preserves the original author's setup; new users only need the root notebook. Review files before sharing them elsewhere.

## Troubleshooting

- **CSV error:** check the path, exact headers, delimiter, and column mappings in the first cell. Remove mappings for missing optional columns.
- **Cannot restore:** the CSV identities/order changed, or both session files are invalid. Keep the old files and use a new CSV filename for a fresh session.
- **Save failed:** keep the kernel open, fix write permissions or available disk space, then pause/resume to retry saving.
- **Browser disconnected:** rerun only the last notebook cell to open a new window. Start the notebook again if the kernel stopped.

## For contributors and coding assistants

Keep this README accurate whenever setup, CSV configuration, controls, or saving behavior changes. Run checks with `.venv/bin/python -m unittest discover -s tests` (Windows: `.venv\Scripts\python.exe -m unittest discover -s tests`).

Licensed under [MIT](LICENSE). Before publishing, run the tests, clear notebook outputs, and inspect `git status --short` for unexpected data files. Keep personal CSVs under `data/`; Git ignores do not protect files shared through ZIPs or other tools.
