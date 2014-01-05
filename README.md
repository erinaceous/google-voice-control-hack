google-voice-control-hack
=========================

Inspired by:
http://jacerdass.wordpress.com/2013/07/16/hacking-google-voice-api-in-linux/

Use the Google Voice Recognition API to run arbitrary commands on your linux
machine. Written in python, currently aimed at Python 3.

Python Dependencies:
* alsaaudio module (http://pyalsaaudio.sourceforge.net/pyalsaaudio.html)

External Dependencies:
* sox (http://sox.sourceforge.net/)
* PulseAudio preferred but not needed; `paplay` used to give you audible
  feedback when recording is triggered or ends.
* bash (You are probably definitely going to have that ;))
* A correctly configured locale (If you have a British accent and your $LANG is
  set to `en_US`, then Google might have trouble with your accent ;))
* A microphone that doesn't have too much noise. Mine has developed a terrible
  hiss. I can't tell if it's my mic or my code that's making Google fail to
  recognize what I'm saying...

To use:
    python control.py -v

This uses Version 1 of Google's Voice Recognition API (which isn't public, just
reverse-engineered, and they don't seem to care about hackers using it to do
cool things). Version 2 exists and is better (allows streaming of audio to the
server and getting hypotheses back in realtime) but too much effort for moi :p

The script will start running and will be listening for loud noises. As soon as
it hears ANY loud noise through your default system mic, it triggers recording.
After soon as the recording gets quiet again, it stops recording, converts the
result to flac and POSTs it to the Google servers.

Should Google come back with what it recognized you saying in your recording,
the script will compare the words in Google's hypotheses with a list of keywords
in `config.json`. Should there be a good match, it'll run the command associated
with that keyword.

To configure it to do your own bidding, edit `config.json`.
By default, commands ran by this python script are forked asynchronously, so
it'll continue doing stuff whilst the commands are running. If you'd rather it
wait until the command is done (useful if the command makes noise), add a
semicolon `;` to the end of the command.

The values I've used in the scripts (especially in `listen.py`) are pretty
arbitrary. Also I suck at statsy mathsy stuff. So maybe how I'm figuring out
when to start/stop recording is dumb and you can and should improve it. Pull
requests definitely welcome :)
