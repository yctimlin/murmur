#!/usr/bin/env python3
"""Clock probe: every 5 s log realtime, monotonic, monotonic_raw, boottime and /proc/stat steal (all CPUs).
Used to find out which clock (if any) excludes the host-side VM freezes on this box."""
import time, sys
out = sys.argv[1]
while True:
    steal = open("/proc/stat").readline().split()[8]
    line = "%.3f %.3f %.3f %.3f %s\n" % (time.time(), time.clock_gettime(time.CLOCK_MONOTONIC),
        time.clock_gettime(time.CLOCK_MONOTONIC_RAW), time.clock_gettime(time.CLOCK_BOOTTIME), steal)
    with open(out, "a") as f: f.write(line)
    time.sleep(5)
