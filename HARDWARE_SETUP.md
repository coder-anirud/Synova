# Synova hardware setup

Synova is a research prototype, not a medical device. The iPhone app can show Muse 2 EEG and manually control a compatible ESP32-S3 glove. It does **not** turn thoughts into movement yet: no movement classifier has been trained or validated, and EEG never automatically sends a glove command.

## Muse 2 → Mac → iPhone

1. In Finder, open the `muse_bridge` folder and double-click **Setup Synova Muse.command**. This creates a private Python environment and installs BrainFlow. You only need to do this once.
2. Turn on Muse 2 and allow Bluetooth access to Terminal when macOS asks. Do not pair Muse in the normal Bluetooth settings first; let BrainFlow find it.
3. Double-click **Start Synova Muse.command**. Keep its Terminal window open. It shows the Mac address and a persistent access key for the iPhone app.
4. On the iPhone, open Synova → Settings → Muse 2 headset. Enter the displayed address and access key, then tap **Connect Muse**. Both devices must be on the same trusted Wi-Fi. Synova reconnects automatically on later launches.
5. The Signals page changes from a labeled simulated preview to live, auto-scaled EEG only after fresh Muse samples arrive. **Export latest samples** saves the recent display window on the iPhone.
6. Before collecting trials, stop the display companion and run **Check Muse Connection.command**. It reports whether actual samples arrived and checks all four channels. If macOS reports Bluetooth unavailable, check Bluetooth access for Terminal under System Settings → Privacy & Security → Bluetooth. A connected device in Settings does not establish that BrainFlow has received EEG.
7. Double-click **Practice Muse Session.command** for a short, separate first recording. **Check Synova Data.command** shows its usable trials but marks it as excluded from training. Then use **Record Synova Training.command** for full two-class sessions. **Train Synova Model.command** fits after six full sessions, reserving validation and final test sessions. These tools never send glove commands.

The bridge exposes EEG status and recording controls over plain HTTP on the local network, protected by its access key. Use a trusted private Wi-Fi network; do not port-forward it or use it for sensitive clinical data. If macOS Firewall asks, permit incoming connections for the bridge. Stop the bridge with Control-C. If the Mac changes Wi-Fi networks, update its address in Synova Settings.

Labeled recordings are inputs for future model development; they do not make Synova able to interpret thoughts. A usable classifier requires repeated sessions, participant-specific validation, an explicit false-activation target, and separate safety testing before it can ever issue a glove command.

## Current two-class study (from the supplied NeuroGrip plan)

The current launchers collect REST versus imagined right-hand opening, with 30 trials of each class, two runs, a five-minute break, two seconds of preparation, four seconds of task time, and randomized three-to-five-second recovery. Keep the same eyes-open fixation and remain still in both classes. The recorder checks signal quality before starting and logs rejected trials and participant-marked movement/missed cues.

Run `muse_bridge/.venv/bin/python muse_bridge/record_open_rest.py --participant P01` from the project root. For a shorter first run use `--practice`, which defaults to six trials/class and no scheduled break and is excluded from every model partition. Each session saves raw unfiltered EEG with BrainFlow cue markers (`raw.csv`), labeled epochs and quality decisions (`trials.jsonl`), and session metadata (`session.json`) under `muse_bridge/data/open_rest/`. Cue request timestamps and next-sample markers are software timing; physical display/audio latency is not measured. IMU capture is not implemented yet. Raw EEG includes preparation and recovery as well as task periods.

Aim for six complete sessions across at least seven calendar days. Inspect with `train_open_rest.py --participant P01 --inspect`. Train with `train_open_rest.py --participant P01 --output muse_bridge/models/P01_open_rest.joblib` (prefix the interpreter/script directory when running from the project root). Four earlier sessions train, the penultimate validates, and the newest remains unread for final testing. Partitions are frozen on the first successful fit. A three-session development pilot is available with `--pilot`; it is not the full study target. Existing checkpoints are never overwritten.

When development is complete, run **Review Synova Model.command** to score the reserved session once. This is an offline mu/beta spectral-power logistic baseline, not the full CSP/model-comparison pipeline in the plan. A promising score is not proof of motor-intention decoding: Muse 2's fixed frontal/temporal electrodes differ from the plan's eight motor-cortex electrodes. See `MUSE_PROJECT_STATUS.md` for the adaptation and remaining gates.

After fitting, **Monitor Synova Model.command** offers a display-only live prediction check. It samples the latest two seconds every 250 ms and uses the exact same spectral feature function as the offline model. It shows REST, OPEN_INTENT, UNCERTAIN or BAD_SIGNAL, with probabilities only for fresh usable EEG. Three consecutive confident predictions and a five-second cooldown produce a logged **candidate** event, never a motor command. Choose `rest` and 300 seconds to inspect exploratory rest candidates; label the condition truthfully. The default confidence of 0.75 has not been calibrated on real Muse data. Stop the bridge before running the monitor: only one process can own the headset. Keep the glove off and disconnected.

## Legacy three-class experiment (manual CLI only)

The initial task is personal REST vs imagined OPEN vs imagined CLOSE. Muse 2 has four frontal and temporal electrodes, so we must measure whether these particular patterns are distinguishable for the wearer. Keep your hand, eyes, jaw, and head still during each cue. Do not wear or connect the powered glove while collecting these trials.

Use **one** of these collection methods for each sitting:

- Preferred controlled recorder: stop the Mac companion first, then run `muse_bridge/.venv/bin/python muse_bridge/record.py --participant P01 --blocks 6` from the project root. Each block shuffles the three cues; each trial saves four seconds of EEG after discarding the first half-second. This writes trial JSONL to `muse_bridge/data/`.
- Quick recordings from the iPhone **Signals** page can also be imported for exploratory work: collect separate REST, imagined OPEN, and imagined CLOSE CSVs of at least six seconds each while sitting still. Run `muse_bridge/.venv/bin/python muse_bridge/import_csv.py --participant P01 --session-id 20261022-evening PATH_TO_REST.csv PATH_TO_OPEN.csv PATH_TO_CLOSE.csv` with all labeled CSVs from one sitting. Repeat for another sitting with a new session ID. The importer discards the first second after each start. These manually timed recordings are less controlled than the randomized Mac recorder; a result from them could reflect cue or timing differences.

Collect at least **two separate sessions**, with at least six usable trials of each class in the older session(s) and three of each class in the newest one. Then run `muse_bridge/.venv/bin/python muse_bridge/train.py --participant P01`. The newest whole session is held out. The report shows balanced accuracy, per-class recall, a confusion matrix, and REST trials mistakenly classified as movement. A saved research checkpoint is optional: add `--output muse_bridge/models/P01.joblib`. No model is loaded by the iPhone app or allowed to drive the glove. Accuracy from this small experiment is not a clinical or safety result.

For legacy checkpoints only, record a **new third session** and run `muse_bridge/.venv/bin/python muse_bridge/evaluate_new.py --participant P01`. It refuses to reuse sessions that trained or evaluated the checkpoint and prints predictions for each usable new trial. The double-click launchers now use the two-class study above. This remains offline research; it does not send commands to the glove.

These scripts require BrainFlow, NumPy, SciPy, scikit-learn, and joblib from `muse_bridge/requirements.txt`. Raw EEG and model files under `muse_bridge/data/` and `muse_bridge/models/` are ignored by git. Keep recordings private. The app's demo charts and demo trial counts are not measurements of classifier performance.

## ESP32-S3 glove → iPhone

1. The sketch is at `firmware/SynovaGlove/SynovaGlove.ino`. Install the Espressif Arduino-ESP32 **3.x** board package and select the actual ESP32-S3 board.
2. Provide the exact GPIO assignments for five servos, a normally-closed physical emergency-stop switch, and an independently wired active-high motor-power gate. Do **not** power motors from an iPhone or the ESP32's logic supply.
3. With the glove **off a person**, measure each finger's safe `OPEN_US`, `CLOSE_US`, and `REST_US` pulse widths. Fill in the sketch's pins and pulse widths. Set `CALIBRATION_REVIEWED = true` only after reviewing every value and confirming the stop switch removes motor power independently of firmware.
4. Upload the sketch. On a physical iPhone, open Synova → Glove → **Real glove** → **Find glove** → **Connect**. Check the area before **Reset emergency stop**, then **Arm controls**. Test **Rest**, **Open hand**, **Close hand**, and **Emergency stop** on the bench.
5. Test the physical stop, loss of Bluetooth, app backgrounding, and a stalled connection with the glove still off a person. On reconnection the controller starts stopped. A Bluetooth acknowledgment means only that a command was received; the app has no finger-position or force feedback.

The shipped firmware deliberately has no pin assignments or calibrated pulse widths, so it cannot arm or drive motors as delivered. A real glove also needs mechanical travel limits, force limits, wiring inspection, power isolation, and supervised validation before anyone wears it. The Bluetooth prototype has no authenticated pairing; keep it powered off outside a controlled test and do not rely on it for clinical use.

## Build the iPhone app

Open `SynovaIOS/Synova.xcodeproj` in Xcode, select the **Synova** scheme, and run on an iPhone. After changing web UI files, run `npm run ios:assets` before rebuilding. The Simulator can test the interface and Mac bridge, but cannot validate the glove's Bluetooth hardware or physical behavior.
