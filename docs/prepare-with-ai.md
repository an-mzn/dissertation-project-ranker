# Prepare your projects with any AI assistant

This step is optional: the ranker accepts the original CSV immediately. To get readable cards and personalized guidance, attach your CSV and this guide to your AI assistant. You can use a new conversation or continue one that already knows you, including a ChatGPT project.

## 1. Discuss what matters to you

Copy this prompt:

> Help me prepare my dissertation project list for Dissertation Project Ranker. First discuss my interests, experience, preferred kinds of work, time and resource constraints, and anything else I consider important. Use what you already know about me, but confirm assumptions. Ask which optional information I want: readable descriptions, summaries, topics, tags, difficulty, AI assistance, tools/stack, and draft ranks. Suggest useful choices without assuming I want them all. Agree what each estimate means and confirm a short preference profile before preparing any data. Draft rankings should reflect my priorities, not your generic idea of the best project.

## Optional: keep a written preference draft

[This fictional TXT example](../examples/reference-rankings.txt) follows the original personalization document's structure: rating scales, preference assumptions, revisions, ranked topics, qualifications, a review appendix, distributions, and confidence notes. It uses the fictional CSV, not the author's personal data.

> Using our confirmed preferences and my project CSV, create `reference-rankings.txt` following the attached fictional example's structure. Use my own topics and preferences, distinguish facts from estimates, preserve all projects, and leave unsupported ratings blank. Repeat a project across topics only when useful, using identical ratings each time and counting it once in distributions. Keep uncertain or lower-interest projects in a review appendix without excluding them. Finish with uncertainties and a proposed unique global draft rank for each project I want ranked.

The root notebook reads CSVs, not this TXT. After reviewing the draft, use it with the next prompt to populate approved CSV metadata. Topic-local numbering must become unique global `draft_rank` values; combine repeated topics with semicolons rather than duplicating CSV rows.

## 2. Prepare a new CSV

Once the preference profile is agreed, copy this prompt:

> Use my attached CSV and our agreed preferences to create a downloadable UTF-8 `projects-prepared.csv` for Dissertation Project Ranker. Preserve every original column and value, especially title, supervisor, and the full original description. Preserve all rows and their order. Add only the optional columns we agreed on, using the formats below. Do not overwrite an existing column with different content: ask me how to resolve a conflicting column name.
>
> For `readable_description`, use Markdown headings, paragraphs, and flat bullet or numbered lists. Organize supported information under Overview, What you'll do, Deliverables, and Requirements; omit headings not supported by the source. Preserve all variants, constraints, qualifications, and links. Use plain text URLs, without HTML, images, or inline Markdown formatting. Do not invent requirements or omit important details. Keep source facts distinct from personal estimates and suggestions in other metadata columns.
>
> Base summaries, topics, and tags on the source. Label tools not required by the brief as “Suggested: …”. Estimate difficulty and AI assistance only when there is enough evidence and explain that they are subjective in your accompanying notes. Draft ranks should follow our confirmed preferences; never remove or exclude a project because it ranks low. Leave unsupported metadata blank.
>
> Use a CSV writer so commas, quotes, and multiline cells are correctly escaped. Before returning the file, verify the row count, row order, project identities, and all original cell values are unchanged. Report the verification result, flag uncertainties, and return notebook first-cell settings using the exact output headers. Map only columns that exist. Keep the imports and `save_path = session_path(csv_location)` line. Set `use_draft_prior = False` unless I explicitly choose to enable it. Do not change my original CSV or saved progress files.

## Supported columns

Original title, supervisor, and description columns may have any names: configure their mappings in the notebook. Optional added columns use these names:

| Column | Format and meaning |
| --- | --- |
| `readable_description` | Markdown headings (`## Overview`), paragraphs, `-` bullets, or `1.` numbered lists. Original description remains accessible underneath. |
| `summary` | Short plain-text overview based on the source. |
| `topics` | Semicolon-separated section/topic labels, e.g. `Accessibility;Mobile development`. Display only. |
| `tags` | Semicolon-separated consistent labels. Shared tags let the model learn across projects from your choices. |
| `tools` | Plain-text tools/stack; distinguish explicit requirements from “Suggested” starting points. Display only. |
| `difficulty` | Number from 1 to 10: estimated challenge relative to your experience (1 low, 10 very high). Display only. |
| `ai_assistance` | Number from 1 to 10: estimated scope for useful AI assistance (1 little, 10 substantial). Display only; this is not permission to use AI in assessed work. |
| `draft_rank` | Unique positive integer: 1 is your strongest preference. Gaps are allowed; unknown ranks may be blank. |

The renderer supports the block formats above, not arbitrary Markdown. HTML and inline links/images appear as literal text, without executing or loading them.

## 3. Review and rank

Check several prepared descriptions against their originals, particularly requirements and project variants, and review personalized estimates. Put the file in `data/`, apply the AI's notebook settings, and run all cells. Keep the original CSV.

By default, draft ranks are guidance displayed on cards. Set `use_draft_prior = True` if you want a modest starting preference: supplied ranks are ordered and spread from 65/100 to 35/100. Unranked projects, or a lone ranked project, start at 50/100. Your comparison choices then update these scores. No low-ranked projects are excluded or delayed.

A new CSV filename starts a separate saved session. To retain existing progress while adding metadata, keep the same CSV path, project identities, order, and original descriptions; back up the CSV and session files before replacing the input. Rerun the notebook to recompute scores with the new metadata. Never copy a session onto a changed or reordered project list.
