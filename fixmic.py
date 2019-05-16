#!/usr/bin/python3
# Copyright (c) 2019 Bart Massey
# [This program is licensed under the "MIT License"]
# Please see the file LICENSE in the source
# distribution of this software for license terms.

# Compressor / Equalizer for microphone input

import sys
import numpy as np
import math
import pyaudio
import array
import queue

# Sample rate.
rate = 48000

# Window size (latency) in samples.
window = 1024

# Queue for output windows.
outq = queue.SimpleQueue()

# Window of zeros for underruns.
zeros = bytes(array.array('h', [0] * window))

def callback(in_data, frame_count, time_info, status):
    """Supply frames to PortAudio."""
    assert frame_count == window
    try:
        samples = outq.get(block=False)
    except queue.Empty:
        print("underrun", file=sys.stderr)
        samples = zeros

    # Return samples and continue signal.
    return (samples, pyaudio.paContinue)

# Set up the audio streams.
pa = pyaudio.PyAudio()
instream = pa.open(
    format=pa.get_format_from_width(2),
    channels=1,
    rate=48000,
    input=True,
    frames_per_buffer=window)

samples = instream.read(window)
outq.put(samples)

outstream = pa.open(
    format=pa.get_format_from_width(2),
    channels=1,
    rate=48000,
    output=True,
    frames_per_buffer=window,
    stream_callback=callback)

while True:
    samples = instream.read(window)
    outq.put(samples)

# Done, clean up and exit.
outstream.stop_stream()
outstream.close()
instream.stop_stream()
instream.close()
