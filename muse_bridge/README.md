# Synova Muse 2 companion

The companion connects Muse 2 to the Synova iPhone app through a Mac on the same Wi-Fi. Recent EEG samples stream to the iPhone for display; full recordings stay on the Mac.

## First-time setup

1. Double-click `Setup Synova Muse.command`.
2. Turn on Muse 2, fit it, and close other apps connected to it.
3. Double-click `Check Muse Connection.command`. Allow Terminal Bluetooth access if macOS asks. The check reports real sample counts, rate, gaps, and per-channel amplitude/flatline flags; it saves a summary to `data/diagnostics/latest_headset_check.json`.
4. Once the connection check receives good signal, double-click `Practice Muse Session.command` for six REST and six imagined right-hand opening trials. The session remains available for inspection and is excluded from model fitting and evaluation.
5. For live display, double-click `Start Synova Muse.command` and keep the Terminal window open.
6. Copy the displayed Mac address and access key into Synova → Settings on the iPhone.

The access key is stored locally in `.access-key` with owner-only permissions and is reused so the iPhone can reconnect automatically.

## Record and evaluate research data

The display companion and recorder cannot use Muse 2 at the same time.

1. Stop **Start Synova Muse.command** with Control-C.
2. Double-click **Record Synova Training.command**. Use a pseudonymous participant code, not a real name. It now runs the project plan's two-class experiment: REST and imagined right-hand opening. Default: 30 trials/class in two balanced runs with a five-minute break. Mark accidental movements or missed cues after each run.
3. Double-click **Check Synova Data.command** after each session. It explicitly marks practice runs as excluded. Raw EEG, cue markers, trial decisions and session notes are saved in `data/open_rest/`, separate from legacy three-class files.
4. Aim for six sessions across at least seven calendar dates in New Jersey time, using consistent fit and task instructions. Full-study training enforces that minimum calendar span. The newest session is reserved for final testing; the next-newest is validation; earlier sessions train the model.
5. Double-click **Train Synova Model.command**. It fits a mu/beta spectral-power logistic baseline and reports validation results without reading the final session's trial file. It freezes partitions in `data/open_rest/P01_split.json` and saves a new checkpoint in `models/P01_open_rest.joblib` (substitute your code). It refuses to overwrite an existing checkpoint.
6. Once development is finished, **Review Synova Model.command** scores the reserved final session once. Do not adjust the model using those results. The result is saved beside that session as `final_evaluation.json`.

After fitting a model, **Monitor Synova Model.command** shows the probability of imagined opening from fresh two-second windows every 250 ms. Its four states are REST, OPEN_INTENT, UNCERTAIN and BAD_SIGNAL. Only signal with new samples that passes the basic amplitude, flatline and timestamp checks can produce a probability. A stream-read error also becomes BAD_SIGNAL. It logs exploratory candidate events after three confident predictions and a five-second cooldown in `data/monitor/`. It does not load, import, connect to or control the glove. A five-minute rest-only run can be selected in the launcher; its candidate count is not an actuator false-activation measurement. Do not use the reserved final-test session or its labels to adjust the threshold.

For an earlier three-session pilot, use `train_open_rest.py --participant P01 --pilot --output models/P01_open_rest.joblib`. A pilot freezes its own split and cannot silently become a full study on a later run; plan a separate dataset for the full experiment if you have inspected pilot results. The six-session schedule is still the project target; training requires six usable trials/class and validation/final evaluation require three/class as software minimums, not evidence of sufficient statistical power. The trainer reports balanced accuracy, the 50% majority baseline, a confusion matrix and REST false predictions. These are not actuator false activations per minute.

Muse 2 has fixed frontal/temporal channels, not the eight sensorimotor positions in the supplied NeuroGrip plan. This is a feasibility adaptation. See `../MUSE_PROJECT_STATUS.md` for differences and remaining milestones. No EEG classifier controls the glove.

The older `record.py`, `train.py`, `import_csv.py` and `evaluate_new.py` remain available for existing REST/OPEN/CLOSE work. They use a different dataset and must not be mixed with the new two-class study. The double-click launchers now use the two-class tools.

## Manual start

Developers can run:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python server.py --host 0.0.0.0 --access-key "a-private-key-at-least-16-characters"
```

Use only on a trusted private network. This is research software, not a medical device, and it does not include a trained movement classifier. To collect controlled trials and train the first offline baseline, see `HARDWARE_SETUP.md` in the project root. Stop this companion before running `record.py` because only one process can own Muse 2 at a time.
