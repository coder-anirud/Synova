"""Muse 2 acquisition and conservative signal checks shared by research tools."""

from contextlib import contextmanager
import time

import numpy as np

CHANNELS = ("TP9", "AF7", "AF8", "TP10")


@contextmanager
def connected_muse(name="", timeout=10):
    from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams

    params = BrainFlowInputParams()
    params.serial_number = name
    params.timeout = timeout
    board_id = BoardIds.MUSE_2_BOARD.value
    descriptor = BoardShim.get_board_descr(board_id)
    if descriptor["eeg_names"].split(",") != list(CHANNELS):
        raise ValueError("Unexpected Muse channel layout")
    board = BoardShim(board_id, params)
    prepared = streaming = False
    try:
        board.prepare_session()
        prepared = True
        board.start_stream()
        streaming = True
        yield board, descriptor
    finally:
        try:
            if streaming:
                board.stop_stream()
        finally:
            if prepared:
                board.release_session()


def collect_seconds(board, seconds, on_chunk=None):
    """Drain continuously, optionally persisting every unfiltered chunk."""
    chunks = []
    deadline = time.monotonic() + seconds
    while True:
        chunk = board.get_board_data()
        if chunk.shape[1]:
            chunks.append(chunk)
            if on_chunk:
                on_chunk(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(0.05, remaining))
    if not chunks:
        raise ValueError("No EEG samples received; check Bluetooth and headset power")
    return np.concatenate(chunks, axis=1)


def signal_quality(eeg, timestamps, sample_rate, minimum_seconds=2):
    """Heuristic only: neither electrode impedance nor proof of artifact-free EEG."""
    eeg = np.asarray(eeg, dtype=float)
    timestamps = np.asarray(timestamps, dtype=float)
    reasons = []
    result = {"usable": False, "reasons": reasons, "channels": [], "sample_count": int(timestamps.size)}
    if eeg.ndim != 2 or eeg.shape[0] != 4 or timestamps.ndim != 1 or eeg.shape[1] != timestamps.size:
        reasons.append("invalid_shape")
        return result
    if timestamps.size < round(minimum_seconds * sample_rate):
        reasons.append("too_few_samples")
    if timestamps.size < 2 or not np.isfinite(eeg).all() or not np.isfinite(timestamps).all():
        reasons.append("missing_or_nonfinite_signal")
        return result
    deltas = np.diff(timestamps)
    if (timestamps <= 0).any() or (deltas <= 0).any():
        reasons.append("invalid_or_nonmonotonic_timestamps")
    if (deltas > 3 / sample_rate).any():
        reasons.append("sample_gap")
    elapsed = timestamps[-1] - timestamps[0]
    measured = (timestamps.size - 1) / elapsed if elapsed > 0 else None
    result["observed_sample_rate"] = float(measured) if measured is not None else None
    result["max_gap_seconds"] = float(np.max(deltas))
    if measured is None or abs(measured / sample_rate - 1) > 0.1:
        reasons.append("unexpected_sample_rate")
    centered = eeg - np.median(eeg, axis=1, keepdims=True)
    for index, name in enumerate(CHANNELS):
        spread = float(np.std(centered[index]))
        peak = float(np.max(np.abs(centered[index])))
        flags = []
        if spread < 0.5:
            flags.append("flat_signal")
        if peak > 250:
            flags.append("large_amplitude")
        reasons.extend(name + ":" + flag for flag in flags)
        result["channels"].append({"name": name, "std_uv": spread, "peak_centered_uv": peak, "flags": flags})
    result["usable"] = not reasons
    return result


def check_chunk(raw, descriptor, minimum_seconds=2):
    return signal_quality(raw[descriptor["eeg_channels"]], raw[descriptor["timestamp_channel"]],
                          descriptor["sampling_rate"], minimum_seconds)
