# Asterisk Call-Leg Transcription

Reliable per-leg transcription for Asterisk and FreePBX using MixMonitor,
ARI Snoop, and External Media—without AI diarization guesses.

This project treats speaker attribution as a media-routing problem.  Preserve
each call leg as its own audio track, then transcribe each track independently.
The resulting transcript is attributed by the PBX topology, not inferred by a
model from a mixed recording.

## What is included today

* A standard-library Python utility that packages Asterisk `MixMonitor`
  `r()`/`t()` mono tracks into one labelled stereo WAV.
* A provider-neutral transcript merger that keeps the physical-track labels.
* A FreePBX-safe custom-context example for recording outbound calls without
  editing generated dialplan files.
* A documented real-time topology for `Snoop` + `externalMedia`. The live ARI
  reference implementation is the next milestone.

## Two paths, one attribution model

| Need | Asterisk topology | Result |
| --- | --- | --- |
| Post-call transcription | `MixMonitor(...,r(rx.wav)t(tx.wav))` | Two physical files packaged as a labelled stereo WAV |
| Real-time transcription | One `Snoop` per target call leg, each bridged to its own `externalMedia` channel | One RTP stream and transcription session per speaker |

These approaches are complementary. `MixMonitor` is the simpler path for
post-call processing; ARI is for live captions, agent assist, or live handoff.

## Quick start: package MixMonitor tracks

The `r()` and `t()` options write receive and transmit tracks separately. Once
Asterisk has finished writing both files:

```bash
python -m asterisk_call_leg_transcription pack \
  --left /var/spool/asterisk/recording-in.wav \
  --right /var/spool/asterisk/recording-out.wav \
  --output call.wav \
  --left-label caller \
  --right-label agent
```

This produces `call.wav` and `call.wav.labels.json`. The WAV is 16-bit stereo:
left = caller, right = agent. Shorter audio is silence-padded so timestamps
remain aligned.

Use a post-call worker only after both MixMonitor files are complete and no
longer changing. Do not read files while a call is active.

## FreePBX installation

Copy the additive example in
[`examples/freepbx/extensions_custom.conf`](examples/freepbx/extensions_custom.conf)
into FreePBX's `/etc/asterisk/extensions_custom.conf`, adapt the recording path
and call scope, then run `fwconsole reload`. It uses FreePBX pre-dial hooks and
ends every hook with `Return()`.

Before enabling call recording or transcription, obtain the consent and give
the disclosures required in the jurisdictions and call paths you operate.

## Real-time ARI design

See [`docs/realtime-ari.md`](docs/realtime-ari.md). The important rule is one
Snoop/External-Media pipeline **per leg**. A mixed bridge stream can be useful
for an AI voice application, but it is not a reliable speaker-attribution
source after a human joins or takes over.

## Development

No runtime dependencies are required for the initial post-call tooling.

```bash
python -m unittest discover -s tests -v
```

## Compatibility and support

The dialplan sample is intended for current Asterisk/FreePBX systems using
`MixMonitor` and FreePBX custom dialplan hooks. Test it in a non-production
environment first: hook names and call direction may vary by installed FreePBX
modules and version.

This is a reference implementation, not legal advice or a complete recording
compliance solution.

## License

Apache-2.0. See [LICENSE](LICENSE).
