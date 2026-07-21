# Local Gesture Browser Controller

Space 17 of Stackwalk: a local-only Python controller for a purpose-built browser workspace.

## Run

```sh
python3 app.py
```

Open <http://127.0.0.1:8765>. The fixture UI has keyboard and button parity. `←`/`→` navigate, `Enter` selects, and `Escape` pauses. The service binds only to loopback and issues a per-process bearer token to the local page. Requests with another origin or token are rejected.

## Verify

```sh
python3 -m unittest -v
```

The core recognizer accepts 21 normalized hand landmarks and recognizes `point` (select), open hand (next), fist (pause), thumb (previous), and thumb-plus-index (search). Observations remain in memory. The browser displays active state, local event log, FPS, latency, command count, and false-activation count.

Camera and offline voice are intentionally adapter boundaries rather than hidden permissions. A hardware adapter must request explicit consent, use a maintained local landmark model, and never persist frames or audio. This repository does not claim assistive-technology validation or arbitrary operating-system control.

## Evidence and limitations

The fixture path is reproducible without camera or microphone hardware. Accepted fixture, keyboard, button, and optional camera commands share one sequence-numbered channel that can change only the four pages in this local workspace; no arbitrary URL or operating-system action exists. Hardware evaluation should record environment, FPS, latency, and false activations across lighting/background conditions before publishing results. No performance or user outcome is claimed here.

With explicit camera consent, install the optional local adapters and run `python3 app.py --camera`:

```sh
python3 -m pip install opencv-python mediapipe
python3 app.py --camera
```

Press Escape in the camera window to stop capture. Offline voice is not included in the portable baseline; browser keyboard and buttons remain the supported parity path.

## Security and privacy

Assets are the local workspace and in-memory session state. The process accepts loopback traffic only, checks a per-run bearer token and browser origin, stores no media, and exposes no OS-control endpoint. Stop the process to revoke the token. A local process or browser extension with access to the page can still act as the user; that is a residual local-trust risk.

## License

MIT
