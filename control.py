#!/usr/bin/env python
"""
Uses the Google Speech API to parse voice commands. Can map arbitrary words or
sentences to specific shell commands.

Definitely not crossplatform code. Basically needs a GNU system with bash, ALSA
and PulseAudio tools, alsaaudio python module, and the sox binary.

Owain Jones [github.com/doomcat]

Inspired by:
http://jacerdass.wordpress.com/2013/07/16/hacking-google-voice-api-in-linux/
"""
# TODO: Hotword detection! Don't start listening for commands every time
#       there's a loud noise.
# TODO: Levenshtein distances!

from __future__ import print_function

import os
import json
import locale
import argparse
import subprocess
import http.client

# listen.py contains the function used to record your voice
import listen

# Defaults (given to argparse args)
LANGUAGE = locale.getlocale()[0].replace('_', '-')  # en-US, en-GB etc...
DURATION = 4  # Recording length in seconds.
RATE = 41000  # Sample rate of recording
DEF_CONFIG = '/etc/voice_control.json'  # Config file to be converted to dict
USR_CONFIG = '/home/owain/.listen.json'
CWD_CONFIG = 'config.json'
RECORD_PATH_RAW = '/tmp/google-voice-hack.raw'
RECORD_PATH = '/tmp/google-voice-hack.flac'
CONVERT_CMD = 'sox -q -t raw -e unsigned-integer -b8 -c1 -r{rate} -L '
CONVERT_CMD += '{in_path} -t flac -C0 {out_path} rate {rate} '
CONVERT_CMD += 'vad reverse vad reverse norm'
START_REC_CMD = 'paplay /usr/share/sounds/freedesktop/stereo/device-added.oga &'
END_REC_CMD = 'paplay /usr/share/sounds/freedesktop/stereo/device-removed.oga &'


def record(language=LANGUAGE, duration=DURATION, rate=RATE, path=RECORD_PATH,
           convert_cmd=CONVERT_CMD, raw_path=RECORD_PATH_RAW, verbose=False,
           last_sample=None):
    subprocess.call(START_REC_CMD, shell=True)
    listen.record_voice(raw_path, sample_rate=rate, verbose=verbose,
                        last_sample=last_sample)
    subprocess.call(convert_cmd.format(rate=rate, in_path=raw_path,
                                       out_path=path), shell=True)
    subprocess.call(END_REC_CMD, shell=True)
    headers = {"Content-type": "audio/x-flac; rate=" + str(rate)}
    connection = http.client.HTTPSConnection("www.google.com")
    audiofile = open(path, 'rb').read()
    connection.request("POST", "/speech-api/v1/recognize?xjerr=1" +
                               "&client=chromium&lang=" + language,
                       audiofile, headers)
    response = connection.getresponse()
    data = response.read()
    connection.close()
    subprocess.call(END_REC_CMD, shell=True)
    try:
        response_json = json.loads(str(data).strip()[2:-3])
        if verbose:
            print(response_json)
    except ValueError:
        return None
    return response_json


def respond(config, utterance, verbose=False):
    if 'commands' not in config:
        return
    utterance_orig = utterance.lower()
    utterance = set(utterance_orig.split(' '))
    for words, command in config['commands'].items():
        words_orig = words.lower()
        words = set(words_orig.split(' '))
        if words.issubset(utterance):
            hypothesis = utterance_orig.replace(words_orig, '', 1)
            cmd = command.format(string=hypothesis, pid=str(os.getpid()))
            if cmd.endswith('&') or cmd.endswith('exit') or cmd.endswith(';'):
                return cmd
            return cmd + ' &'


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    config = DEF_CONFIG
    if os.path.isfile(CWD_CONFIG):
        config = CWD_CONFIG
    elif os.path.isfile(os.path.expanduser(USR_CONFIG)):
        config = USR_CONFIG
    parser.add_argument('-c', '--config', default=config,
                        help='Configuration file')
    parser.add_argument('-d', '--duration', type=int, default=DURATION,
                        help='Length of recording')
    parser.add_argument('-r', '--rate', type=int, default=RATE,
                        help='Sample rate')
    parser.add_argument('-v', '--verbose', action='store_true', default=False)
    args = parser.parse_args()
    config = json.load(open(args.config, 'r'))
    while True:
        last_sample = listen.listen_for_voice()
        response = record(duration=args.duration, rate=args.rate,
                          verbose=args.verbose, last_sample=last_sample)
        if response is not None and 'hypotheses' in response:
            for hypothesis in response['hypotheses']:
                print("I heard:", hypothesis['utterance'])
                command = respond(config, hypothesis['utterance'],
                                  verbose=args.verbose)
                if command:
                    subprocess.call(command, shell=True)


if __name__ == '__main__':
    main()
    print()
