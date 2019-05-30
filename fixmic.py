#!/usr/bin/python3
# Copyright (c) 2019 Bart Massey
# [This program is licensed under the "MIT License"]
# Please see the file LICENSE in the source
# distribution of this software for license terms.

# Compressor / Equalizer for microphone input

import math
import sys
import pyaudio as pa
import array
import queue
import numpy as np

# Sample rate.
rate = 48000

# Window size (latency) in samples.
window = 1024


class Compressor(object):
    """Sample compressor."""
    def __init__(self,
                 threshold=-15,
                 ratio=8.0,
                 postgain=-9.0,
                 smooth=0.5,
                 limit=-30):
        """
        threshold is input level (dB) at which break occurs.
        ratio is compression ratio at break level.
        postgain is gain after compression (dB).
        smooth is a smoothing constant between
          0.0 (use only current power measurement)
          1.0 (never change the power measurement)
        limit is power (dB) below which is silence
        """
        self.threshold = threshold
        self.ratio = ratio
        self.smooth = smooth
        self.power = 0
        cgain = self.cf(0)
        self.postgain = postgain - cgain
        self.limit = limit

    def cf(self, db_in):
        """Compression function."""
        if db_in < self.threshold:
            return db_in
        else:
            # https://www.audio-issues.com/music-mixing/
            # what-does-the-ratio-on-your-compressor-really-do/
            return (db_in - self.threshold) / self.ratio + self.threshold

    def compress(self, samples):
        """Compress samples according to compression function."""
        rms = np.sqrt(np.dot(samples, samples) / window)
        power = self.power * (1.0 - self.smooth) + rms * self.smooth
        self.power = power
        if power <= 1e-40:
            samples *= 0
            return
        db_in = 10.0 * math.log10(power)
        if db_in <= self.limit:
            samples *= 0
            return
        db_out = self.cf(db_in)
        db_gain = db_out - db_in + self.postgain
        gain = 10**(0.1 * db_gain)
        samples *= gain

compressor = Compressor()

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
    samples = instream.read(window)
    samples = array.array('h', samples)
    samples = np.array(samples, dtype=np.dtype(np.float)) / 32768.0
    compressor.compress(samples)
    samples = (samples * 32767.0).astype(np.dtype(np.int16))
    outq.put(bytes(samples))

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
