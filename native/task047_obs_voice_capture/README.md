# BAI Voice Capture OBS Plugin

`bai-voice-capture` is a selected-source OBS audio filter. It leaves the OBS
audio path unchanged and copies bounded float-planar PCM frames into a fixed
single-producer/single-consumer queue. A worker may forward those frames to a
pre-existing local named pipe after a same-user Controller handshake supplies a
one-session 256-bit key in memory.

Safety defaults:

- disabled until the filter is explicitly enabled and a same-user Controller session is connected;
- no network API and no filesystem audio writer;
- no allocation, blocking wait, IPC, AI, logging, or normalization in the audio callback;
- fixed maximum of 8 planes, 8192 frames per callback, and 64 queued frames;
- queue overflow, oversize, invalid input, and unauthorized input are counted and dropped;
- IPC is worker-only; the Plugin verifies the named-pipe server Windows user,
  the Controller verifies the connecting process is the selected `obs64.exe`,
  and audio is authenticated with HMAC-SHA-256 plus a random session nonce and
  monotonic sequence;
- audio copying is connection-gated: closing the authenticated receiver returns the callback to the unauthorized fast path, bounding resource use while OBS remains open;
- the receiver/controller owns the always-visible recording indicator, save destination, duration and disk-floor controls; the filter never writes audio to disk;
- OBS receives its original `obs_audio_data` unchanged.

The build scripts never install or launch OBS. `package.ps1` refuses to create
a runtime ZIP unless the real `bai-voice-capture.dll` exists. A source ZIP and
offline test receipt can still be generated when the OBS dependency build is
unavailable.

`scripts/build-controller.ps1` builds and self-tests the local Windows recording
controller without CMake. The controller is packaged outside the OBS deployment
tree; it provides the visible recording state, destination picker, real-time
Peak/RMS/clip meter, elapsed time, disk floor, maximum duration, Pause/Resume
and Stop controls. An already-running exact OBS process is reused instead of
requiring a restart. Pause disconnects
the authenticated receiver so the plugin returns to its unauthorized callback
fast path; Resume opens a new receiver without persisting paused audio. A five
second pre-recording gain check computes peak, RMS and clipping facts without
persisting audio or changing any device setting; policy admission remains
explicitly unknown until an approved Quality Policy is bound.
