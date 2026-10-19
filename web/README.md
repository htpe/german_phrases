# German Phrases: browser app

The phone app from `mobile/` with a layout for desktop browsers too: the tabs are a left
sidebar at 900 px and wider, and at the bottom on narrow windows and phones. Same tabs
(Study, Browse, Auto play, Lists, Progress, Settings), same spaced repetition and the same
`progress.json` format as `trainer.py` (export/import in Settings).

## Online

<https://htpe.github.io/german_phrases/>, published by `.github/workflows/pages.yml`
on every push to `main` that changes `web/`. Open it on any device. To install it as an app:

- **Android**: Chrome → ⋮ → Add to Home screen → Install
- **macOS**: Safari → File → Add to Dock
- **iPhone/iPad**: Safari → Share → Add to Home Screen

After the first visit it works offline. A new version is picked up the next time the app is
opened while online. Progress stays on each device; move it with Settings → Export / Import.

## Run locally

ES modules and `fetch` don't work from `file://`, so serve the folder over http:

```bash
cd web
python -m http.server 8000
```

Then open <http://localhost:8000>. Progress is stored in the browser (localStorage, key
`german-phrases/progress`). Use Settings → Export / Import to move it to or from the PC trainer.

## Files

| File | |
|------|---|
| `app.js`, `logic.js` | copied from `mobile/` without changes |
| `phrases.json` | copied from `mobile/` (built by `python mobile/tools/build_data.py`) |
| `index.html` | `mobile/index.html` with hints for desktop browsers |
| `styles.css` | `mobile/styles.css` plus the desktop sidebar (`@media (min-width: 900px)`) |
| `sw.js`, `manifest.webmanifest`, `icons/` | offline support and install, own cache name `german-phrases-web` |

After changing the mobile app or the phrases, copy `app.js`, `logic.js` and `phrases.json`
from `mobile/` again.
