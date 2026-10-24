# NeuroGrip / Synova: Muse 2 implementation status

Updated October 24, 2026. Based on the supplied “NeuroGrip Eight-Week Project Plan.” Its July–September dates are historical; progress below is by milestone, not a claim those weeks were completed.

## Hardware adaptation

The plan calls for eight configurable electrodes around sensorimotor cortex. The available Muse 2 supplies four fixed channels, TP9, AF7, AF8 and TP10, at 256 Hz through the installed BrainFlow descriptor. They do not reproduce FC3/C3/CP3/Cz/FC4/C4/CP4/Pz. Imagined right-hand opening versus rest is therefore an exploratory feasibility experiment on this hardware. No software change can supply the missing electrode positions. Do not reposition the headset to imitate the cap layout or assume the plan's occipital SSVEP fallback works with these fixed sensors.

Manufacturer channel specification: https://choosemuse.my.site.com/s/article/Comparing-Muse-Headbands

BrainFlow Muse support and Bluetooth requirements: https://brainflow.readthedocs.io/en/stable/SupportedBoards.html#muse-2

## Implemented in this milestone

- A bounded real-headset diagnostic, launched with `muse_bridge/Check Muse Connection.command`. It checks sample arrival, observed rate, timestamp gaps, flat channels and large amplitudes. Output is a diagnostic summary, not raw EEG or electrode impedance.
- A separate two-class dataset and recorder matching the plan's REST/OPEN_INTENT scope. It records two randomized balanced runs, default 30 trials/class, 2-second preparation, 4-second tasks, 3–5-second recovery and a 5-minute break.
- Unfiltered EEG, BrainFlow software markers, cue request times, per-trial quality decisions and session metadata. Completed work survives interruption. Run-end annotations exclude known movement or missed-cue trials.
- A small mu/beta log-power logistic-regression baseline. Scaling is fitted only on training windows. Complete trials and sessions stay in one partition. Duplicate EEG trials are rejected across development partitions and against the final test.
- Frozen training/validation/final-test partitions. Training does not read final-test trial bytes. Six sessions over at least seven calendar dates are required by default, with an explicit three-session pilot option that cannot silently become the full study. Final results are stored once; the software refuses checkpoint overwrites and repeated final scoring.
- Updated double-click launchers. Legacy REST/OPEN/CLOSE tools and data remain separate.
- A separate display-only live monitor that reuses training's two-second features, checks freshness and quality before probabilities, and logs 250 ms predictions and candidate events after the plan's preliminary threshold/persistence/cooldown. It does not contain an actuator interface; those candidate counts are not physical activation measurements.
- A short six-trial-per-class practice launcher. It preserves the initial real EEG for inspection while marking that session so training, validation and final testing exclude it.

## Actual hardware result so far

Three connection attempts from the assistant's execution process reported Bluetooth unavailable and received no EEG, including two after the user reported connecting the headset. This does not establish that the headset is disconnected at the OS level; Bluetooth permission or execution restrictions can also prevent access. The last attempt was October 24, 2026 at 5:00 p.m. Eastern. The diagnostic must run successfully from the user's Terminal before claiming live hardware validation. No real participant model has been trained.

## Next run

1. Close Muse/Mind Monitor and any other connection to the headset. Fit it and sit still.
2. Double-click `Check Muse Connection.command`, allow Terminal Bluetooth access, and inspect its result. If connection succeeds but quality fails, correct contact and rerun.
3. Stop the diagnostic before starting the recorder. Use a consistent pseudonym, such as P01.
4. Run `Practice Muse Session.command`, then `Check Synova Data.command`. This run is excluded from model fitting. For the full study use `Record Synova Training.command` (30 trials/class/session).
5. Collect the planned six sessions across at least seven calendar days. The seven-day span and target class counts are research-protocol requirements; the software's lower usable-trial minimums are only execution checks.
6. Train and inspect validation results. Freeze the approach before running the final review. Preserve the split file and final evaluation; new experiments need a separately planned dataset, not deletion of safeguards to reuse a test set.

## Work still required

- Public motor-imagery dataset baseline and the plan's CSP/LDA and CSP/logistic comparisons.
- Successful real Muse acquisition, artifact reference recordings/plots, IMU recording and cue-latency measurement. Current amplitude/flatline/gap checks cannot reliably reject every blink, jaw movement, or muscle artifact.
- Repeated-session evidence for any separation of imagery and rest. High accuracy alone cannot establish that features are neural motor intention rather than artifacts or cue responses.
- Separate model-hand construction and 100-cycle keyboard reliability test. Existing five-servo glove firmware is a different mechanical design from the plan's single-servo model hand.
- Real-headset validation of the display-only monitor's signal quality, latency, and REST/OPEN_INTENT/UNCERTAIN/BAD_SIGNAL states; then measurement and tuning of confidence/persistence/cooldown using development sessions only. The current thresholds are exploratory, unvalidated defaults.
- Physical emergency-stop and connection-loss bench tests before any EEG-to-actuator integration. No model currently sends actuator commands.
- The plan's formal five-minute rest, artifact challenge, cued-activation, cross-day and final comparison experiments. Offline REST errors are not a substitute for measured false activations/minute or response time.

This milestone prepares acquisition and offline evaluation. It does not complete the plan's research or hardware safety gates.

## Software verification

All 20 unit/integration tests passed on October 24, 2026. They cover HTTP authorization/recording, signal rejection, marker-aligned epoch extraction, session partitioning, practice exclusion, final-test isolation, one-time final evaluation, exact live/training feature parity, live quality gates, and persistence/cooldown behavior. The BrainFlow synthetic board also retained cue markers and produced the expected four-second epoch. These fixtures validate software behavior, not real Muse performance or classification accuracy. Python syntax and launcher shell syntax checks passed. Real-headset validation remains blocked as described above.
