# Lettuce Lattice UI

Static app-shell frontend for the local Lettuce runtime.

Start the standalone Python runtime from the repo root:

```bash
python3 -m lettuce.runtime --host 127.0.0.1 --port 8787
```

Then open `http://127.0.0.1:8787/`.

The UI reads from `/api/state` and other JSON endpoints, and sends writes to the runtime with the preview token header when you save a token in Settings. Local runtime state lives in `.lettuce/runtime/state.json`.

You can still open `index.html` directly or serve this folder statically. In that mode the app uses embedded fallback data so the shell remains explorable, but write actions will not persist.
