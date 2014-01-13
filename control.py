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
import time
import locale
import difflib
import argparse
import readline
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


def fuzzysubset(parent, child, word_threshold=0.5):
    """Using levenshtein distances, check whether a child set (a set of
       strings) is contained within a parent set.
       Similarity ratios are calculated per word. If all of the words
       in the child set have ratios over word_threshold to some words
       in the parent set, this returns a dict containing the
       child_word -> parent_word mapping.
       If all the words in child are under word_threshold,
       this returns None, implying that child is not a subset of parent.
    """
    result = dict()
    for word_1 in child:
        for word_2 in parent:
            ratio = difflib.SequenceMatcher(None, word_1, word_2).ratio()
            if ratio >= word_threshold:
                if word_2 not in result or result[word_2][0] < ratio:
                    result[word_2] = (ratio, word_1)
    if len(result) == 0:
        return None
    return result


def respond(config, utterance, verbose=False):
    if 'commands' not in config:
        return
    utterance_orig = utterance.lower()
    utterance = set(utterance_orig.split(' '))
    cmd_scores = dict()
    for words, command in config['commands'].items():
        words_orig = words.lower()
        words = set(words_orig.split(' '))
        #if words.issubset(utterance):
        fuzzy = fuzzysubset(utterance, words)
        if fuzzy is not None:
            score = sum([fuzzy[x][0] for x in fuzzy])
            cmd_scores[score] = (command, fuzzy)
            #cmd_scores[command] = (sum([fuzzy[x][0] for x in fuzzy]), fuzzy)
        else:
            cmd_scores[0] = (command, None)
        #if fuzzy is not None:
        #    hypothesis = utterance_orig.replace(words_orig, '', 1)
        #    cmd = command.format(string=hypothesis, pid=str(os.getpid()))
        #    if cmd.endswith('&') or cmd.endswith('exit') or cmd.endswith(';'):
        #        return cmd
        #    return cmd + ' &'
    best = max(cmd_scores)
    command = cmd_scores[best][0]
    if best < 1.0:
        return
    words = [key for key, value in config['commands'].items()
             if value == cmd_scores[best][0]][0]
    words_orig = words.lower()
    hypothesis = utterance_orig.replace(words_orig, '', 1)
    cmd = command.format(string=hypothesis, pid=str(os.getpid()))
    return cmd


def help(config):
    print('Available commands:')
    for command in config['commands'].keys():
        if '{string}' in config['commands'][command]:
            print(' ', command, '[...]')
        else:
            print(' ', command)


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
    parser.add_argument('-t', '--text-mode', action='store_true',
                        default=False)
    args = parser.parse_args()
    config = json.load(open(args.config, 'r'))
    while True:
        if args.text_mode:
            response = {'hypotheses': [{'utterance': input('> ')}]}
        else:
            last_sample = listen.listen_for_voice()
            response = record(duration=args.duration, rate=args.rate,
                              verbose=args.verbose, last_sample=last_sample)
        if response is not None and 'hypotheses' in response:
            for hypothesis in response['hypotheses']:
                if not args.text_mode:
                    print("I heard:", hypothesis['utterance'])
                command = respond(config, hypothesis['utterance'],
                                  verbose=args.verbose)
                if command:
                    if command.startswith('!'):
                        subprocess.call(command[1:], shell=True)
                    else:
                        eval(command)
                    time.sleep(0.2)
                    print()


if __name__ == '__main__':
    main()
    print()
