#!/usr/bin/python3
# Copyright (c) 2019 Bart Massey
# [This program is licensed under the "MIT License"]
# Please see the file LICENSE in the source
# distribution of this software for license terms.

# Compressor / Equalizer for microphone input

import sys
import pyaudio as pa
import array
import queue
import numpy as np

# Sample rate.
rate = 48000

# Window size (latency) in samples.
window = 1024

# Queue for output windows.
outq = queue.SimpleQueue()

# Window of zeros for underruns.
zeros = array.array('h', [0] * window).tobytes()

def callback(in_data, frame_count, time_info, status):
    """Supply frames to PortAudio."""
    assert frame_count == window
    try:
        samples = outq.get(block=False)
    except queue.Empty:
        print("underrun", file=sys.stderr)
        samples = zeros

    # Return samples and continue signal.
    return (samples, pa.paContinue)

def process_window():
    frames = instream.read(window)
    unpacked = array.array('h', frames)
    samples = np.array(unpacked, dtype=np.dtype(np.float)) / 32768.0
    reframed = (samples * 32767.0).astype(np.dtype(np.int16))
    outq.put(bytes(reframed))

# Audio sample format (16-bit signed LE).
# pa_format = pa.get_format_from_width(2, unsigned=False)
pa_format = pa.paInt16

# Set up the audio streams.
pya = pa.PyAudio()
instream = pya.open(
    format=pa_format,
    channels=1,
    rate=48000,
    input=True,
    frames_per_buffer=window)

process_window()

outstream = pya.open(
    format=pa_format,
    channels=1,
    rate=48000,
    output=True,
    frames_per_buffer=window,
    stream_callback=callback)

while True:
    process_window()

# Done, clean up and exit.
outstream.stop_stream()
outstream.close()
instream.stop_stream()
instream.close()
