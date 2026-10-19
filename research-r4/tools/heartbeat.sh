#!/bin/bash
# Box-freeze detector: one timestamp every 10 s; a gap > 60 s between lines = VM suspension.
while true; do date +%s >> /workspace/r4/lab/heartbeat.log; sleep 10; done
