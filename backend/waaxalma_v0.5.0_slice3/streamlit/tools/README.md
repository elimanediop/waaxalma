# External Tools

This directory documents third-party tools used by some Waaxalma local
development and conferencing scenarios.

Third-party installers, ZIP archives, binaries, and drivers are not committed
to this repository. Download them from the vendor's official distribution
channel and follow the applicable license terms.

## Virtual audio paths

Outbound conferencing needs one independent virtual audio path.

Full-duplex conferencing in v0.4.4 needs two independent paths:

```text
Path A — outbound
Waaxalma
    -> virtual cable A
    -> conferencing microphone

Path B — inbound
conferencing speaker
    -> virtual cable B
    -> Waaxalma Conference Input
```

Do not use the same virtual path for both directions. Doing so can reintroduce
Waaxalma's translated output into Conference Input and create an audio loop.
