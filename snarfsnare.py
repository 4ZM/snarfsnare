#!/usr/bin/env python

"""
Copyright (C) 2011 Anders Sundman <anders@4zm.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import time
import signal
import sys
from pythonwifi.iwlibs import Wireless
from optparse import OptionParser
import pynotify

# Ctrl-C exit gracefully
def sig_int_exit(signal, frame):
    exit(0);
signal.signal(signal.SIGINT, sig_int_exit)

# Command line option processing
use = "Usage: %prog [--verbose|-v] interface"
parser = OptionParser(usage = use)

parser.add_option("-v", "--verbose", 
  dest="verbose", action="store_true", default=False, help="Verbose output.")

options, args = parser.parse_args()

if len(args) != 1:
   parser.print_usage()
   exit(1)

interface = args[0]


# Get a handle to the card
wifi = Wireless(interface)

current_essid = None
current_ap_addr = None
SAMPLE_WINDOW_SIZE = 10
SIGMA_MUL = 5
SIGMA_MIN = 2
SAMPLE_FREQ_HZ = 2

if options.verbose:
    print("Scanning for rouge AP's. Ctrl-C to exit.")

# Start processing. Ctrl-C to exit
while True: 
    
    time.sleep(1 / SAMPLE_FREQ_HZ)

    # Sample the network
    stat = wifi.getStatistics()[1]
    sig_level = stat.getSignallevel()
    ap_addr = wifi.getAPaddr()
    essid = wifi.getEssid()

    # First time sample on essid
    if not essid == current_essid:
        if options.verbose:
            print("Current essid: '%s' (%s)" % (essid, ap_addr))

        current_essid = essid
        current_ap_addr = ap_addr
        sig_sample = [sig_level]
        sig_avg = None
        sig_std = None
        continue

    # Check that AP addr hasn't changed
    if not current_ap_addr == ap_addr:
        pynotify.Notification ("Snarf Snare - Warning!", 
          " AP address changed.\nOld: %s\nNew: %s" % 
          (current_ap_addr, ap_addr)).show()
        if options.verbose:
            print("WARNING! AP address changed. Old: %s New: %s" % 
              (current_ap_addr, ap_addr))
        current_essid = None
        continue

    # Add measurement
    sig_sample.append(sig_level)

    # Still to short to do any statistics
    if len(sig_sample) < SAMPLE_WINDOW_SIZE: 
        continue
      
    # To long, pop oldest 
    if len(sig_sample) > SAMPLE_WINDOW_SIZE:
        sig_sample = sig_sample[1:]

    # Compute stats
    sig_avg = sum(sig_sample) / len(sig_sample)
    sig_std = (sum([(x-sig_avg)**2 for x in sig_sample]) / len(sig_sample))**0.5 
    sig_std = SIGMA_MIN if sig_std < SIGMA_MIN else sig_std

    # Warn if current sig level is outside SIGMA_MUL sig of the average
    if abs(sig_level - sig_avg) > SIGMA_MUL * sig_std:
        pynotify.Notification ("Snarf Snare - Warning!",
          "Significant change in signal strength detected.").show()
        if options.verbose:
            print("WARNING! Significant change in signal strength detected.")
        current_essid = None
        continue

    current_sig_level = sig_avg

