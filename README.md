# Synova

Synova is a research prototype for exploring Muse 2 EEG recordings and an assistive robotic-hand interface. The iOS and macOS apps show headset signals and offer manual glove controls. The EEG classifier is experimental and **does not control the glove**.

## Get started with the headset

1. On a Mac, open `muse_bridge/Setup Synova Muse.command` to install the Python requirements.
2. Fit and turn on Muse 2, close other apps using it, then open `muse_bridge/Check Muse Connection.command`. Allow Bluetooth access for Terminal if prompted.
3. After the connection check receives usable EEG, open `muse_bridge/Practice Muse Session.command` for a short rest-versus-imagined-opening session. Practice sessions remain available for inspection but are excluded from training.
4. Read [HARDWARE_SETUP.md](HARDWARE_SETUP.md) for the full recording protocol and the iOS/glove setup.

The offline baseline trains only from real, labeled sessions. Full-study training requires six complete sessions across at least seven New Jersey calendar dates; the latest session is reserved for final testing. After a model exists, the display-only live monitor can show probabilities and signal-quality decisions. Its candidate events never send motor commands.

The project plan originally called for eight configurable electrodes near motor cortex. Muse 2 has four fixed frontal/temporal EEG channels, so this is a feasibility adaptation, not a replacement for that hardware. Current work and limitations are documented in [MUSE_PROJECT_STATUS.md](MUSE_PROJECT_STATUS.md).

## Development

The web interface uses React, TypeScript and Vite:

```sh
npm ci
npm run build
```

The Python research tools live in `muse_bridge/`:

```sh
cd muse_bridge
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s . -p 'test_*.py'
```

The local environment, raw EEG, access key and model checkpoints are excluded from Git. This is a research prototype, not a medical device or evidence of rehabilitation benefit.
