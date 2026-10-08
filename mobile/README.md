# German Phrases for Android (web app)

The Phrase Trainer (`trainer.py`) for phones: the same five tabs (Study, Browse, Auto play,
Lists, Progress), the same spaced-repetition schedule and the same `progress.json` format.
It is an installable web app (PWA). After the first visit it works offline, has its own icon on
the home screen and opens full screen like any other app.

## Put it on your phone

The app is a folder of static files. Android only installs web apps served over **HTTPS**, so
host the `mobile` folder once on any static host. Two free options:

- **Netlify Drop**: open <https://app.netlify.com/drop> and drag the `mobile` folder onto the page.
- **GitHub Pages**: push the `mobile` folder to a repository and enable Pages for it.

Then, on the phone, open the address in **Chrome** and choose **⋮ → Add to Home screen → Install**.
The host is needed only to install and update the app. Your progress stays on the phone.

To try it on the PC first: `python -m http.server 8000 --directory mobile`, then open
<http://localhost:8000>.

## Differences from the PC trainer

- **Tap the card** to show the answer, and **swipe** left/right in Browse. On a PC browser the
  keyboard shortcuts of `trainer.py` work too (Space, 1-4, ←/→, S, E, D/F/G, M, Ctrl+Z).
- **Speech** uses the phone's text-to-speech voice. Under ⚙ Settings, pick the German voice (if
  several are installed), set the speed and press *Test voice*. For more natural female and male
  voices, go to Android Settings → Text-to-speech → Google → Install voice data → German.
- **Auto play** keeps the screen on while playing. Android may pause it when the screen is
  locked or you switch apps.
- **Progress chart**: tap a bar to select that day and see its numbers.
- **Settings** (level, topic, direction, answer mode, new phrases per day, daily goal) are under ⚙.

## Moving progress between the PC and the phone

⚙ Settings → **Export** saves `progress.json` to the phone's Downloads. **Share…** sends it to
Drive, e-mail and so on. Copy it to `data/progress.json` on the PC (close the PC app first).
To go the other way, choose **Import…** on the phone and pick the PC's `data/progress.json`.

Importing **replaces** the phone's progress. The two copies are not merged, so study on one device
at a time and move the file when you switch.

## Updates

- After changing `data/phrases_*.csv`, rebuild the phone's data with `python mobile/tools/build_data.py`.
- After uploading a new version, the phone picks it up on the next start after it has been online.

## Files

| File | Purpose |
|------|---------|
| `index.html`, `styles.css` | the screens |
| `app.js` | the five tabs, settings, speech, import/export (mirrors `trainer.py`) |
| `logic.js` | scheduling, study queue, lists, calendar, answer checking (port of the Python modules) |
| `phrases.json` | all 3,000 phrases, built from `data/phrases_*.csv` |
| `sw.js`, `manifest.webmanifest`, `icons/` | offline cache, install info, app icon |
| `tools/build_data.py` | rebuilds `phrases.json` |
| `tools/make_fixtures.py` | records the Python app's results for the parity test |
| `tests/parity.test.js` | checks `logic.js` against the Python app: `node --test tests/parity.test.js` |

If you change the Python learning logic, port the change to `logic.js`, run
`python mobile/tools/make_fixtures.py`, then run the test.
