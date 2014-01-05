#!/usr/bin/env python
# vim: set tabstop=4 shiftwidth=4 textwidth=79 cc=80:
"""
    listen: Use alsaaudio lib to check current volume of mic / record audio
            files and stop recording when volume drops under threshold.
    Original Author: Owain Jones [github.com/doomcat] [contact@odj.me]
"""

from __future__ import print_function
import alsaaudio as audio
import math


def amp2DB(amp):
    """Convert pulse-core amplitude to decibels (I think?)"""
    return (20.0 * math.log10(amp))


def get_volume(values):
    """Get arbitrary measure of volume for this sample.
       Currently this calculates the distance between max PCM value and min
       PCM value, which works well enough for the purposes of triggering
       the starting/stopping of recording based on volume levels."""
    raw = values
    if raw[0] == 0:
        return 0
    sample = [int(x) for x in raw[1]]
    average = max(sample) - min(sample)
    return average


def get_input(pcm=None, sample_rate=8000, sample_length=0.1):
    """Get ALSA PCM input stream, configure for our purposes
       (One channel, unsigned 8-bit int format)
    """
    if pcm is None:
        pcm = audio.PCM(type=audio.PCM_CAPTURE, mode=audio.PCM_NORMAL)
    pcm.setrate(sample_rate)
    pcm.setformat(audio.PCM_FORMAT_U8)
    pcm.setchannels(1)
    pcm.setperiodsize(int(sample_rate * sample_length))
    return pcm


def record_voice(voice_file, sample_rate=8000, verbose=False,
                 window_size=5, sample_length=0.1, sustain=0.75,
                 threshold=1.5, pcm=None, last_sample=None):
    """Records audio to voice_file until the volume goes under threshold for a
       period of time (determined by sample_length). A few samples at the
       beginning are ignored by the thresholding, so the recording will be at
       minimum `window_size * sample_length` long.
    """
    if type(voice_file) == str:
        vfile = open(voice_file, 'wb+')
    else:
        vfile = voice_file

    pcm = get_input(pcm, sample_rate=sample_rate, sample_length=sample_length)

    if last_sample is None:
        values = pcm.read()
    else:
        values = last_sample
    vfile.write(values[1])
    rolling_average = get_volume(values)

    last_rolling_average = rolling_average
    floating_gradient = 0
    i = 0

    while True:
        values = pcm.read()
        volume = get_volume(values)
        rolling_average = (((rolling_average * sustain) + volume)
                           / float(window_size))
        gradient = (rolling_average - last_rolling_average) / 1.0
        floating_gradient += abs(gradient)
        floating_gradient *= sustain
        last_rolling_average = rolling_average
        i += 1
        if verbose:
            print(i, gradient, floating_gradient, rolling_average, volume,
                  sep='\t')
        if floating_gradient < threshold:
            if i < window_size:
                threshold = floating_gradient
            else:
                break
        vfile.write(values[1])

    if type(voice_file) == str:
        vfile.flush()
        vfile.close()


def listen_for_voice(sample_rate=8000, verbose=False, window_size=5,
                     sample_length=0.1, sustain=0.75, threshold=1.5, pcm=None):
    """Waits (in a while loop) until the volume goes over threshold. Returns
       the last sample."""
    
    pcm = get_input(pcm, sample_rate=sample_rate, sample_length=sample_length)
    rolling_average = 0
    last_rolling_average = 0
    floating_gradient = 0
    i = 0
    while True:
        values = pcm.read()
        volume = get_volume(values)
        rolling_average = (((rolling_average * sustain) + volume)
                           / float(window_size))
        gradient = (rolling_average - last_rolling_average) / 1.0
        floating_gradient = (floating_gradient + abs(gradient)) * sustain
        last_rolling_average = rolling_average
        i += 1
        if verbose:
            print(i, gradient, floating_gradient, rolling_average, volume,
                  sep='\t')
        if floating_gradient > threshold:
            if i < window_size:
                threshold = floating_gradient
            else:
                return values


if __name__ == '__main__':
    record_voice('/tmp/test.raw', verbose=True,
                 last_sample=listen_for_voice(verbose=True))
