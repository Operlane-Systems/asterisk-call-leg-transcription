# Asterisk Call-Leg Transcription

Real-time, reliable per-leg transcription for Asterisk and FreePBX using ARI
Snoop and External Media—without AI diarization guesses.

This project treats speaker attribution as a media-routing problem.  Preserve
each call leg as its own audio track, then transcribe each track independently.
The resulting transcript is attributed by the PBX topology, not inferred by a
model from a mixed recording.

## What is included today

* A production-shaped real-time ARI pipeline: one `Snoop` + `externalMedia` +
  RTP gateway + transcription session for every labelled call leg.
* An OpenAI Realtime adapter that accepts Asterisk μ-law RTP, transcodes it to
  the documented 24 kHz PCM input, and emits labelled transcript deltas and
  completions.
* A provider contract so the Asterisk/RTP lifecycle is independent of the
  transcription service.
* A standard-library post-call utility that packages Asterisk `MixMonitor`
  `r()`/`t()` mono tracks into one labelled stereo WAV.
* A FreePBX-safe custom-context example for recording outbound calls without
  editing generated dialplan files.

## Two paths, one attribution model

| Need | Asterisk topology | Result |
| --- | --- | --- |
| Post-call transcription | `MixMonitor(...,r(rx.wav)t(tx.wav))` | Two physical files packaged as a labelled stereo WAV |
| Real-time transcription | One `Snoop` per target call leg, each bridged to its own `externalMedia` channel | One RTP stream and transcription session per speaker |

These approaches are complementary. `MixMonitor` is a post-call fallback or
archive path. ARI is the primary path for live captions, agent assist, and
human handoff.

## Quick start: real-time labelled transcription

The reference pipeline starts after your application has placed the target call
legs in Stasis and knows their channel IDs. It creates independent helper
resources for each leg and prints final OpenAI transcript events by label:

```bash
python examples/start_live_transcription.py \
  --caller-channel PJSIP/caller-00000001 \
  --agent-channel PJSIP/agent-00000002
```

Set `ARI_URL`, `ARI_USER`, `ARI_PASS`, `ARI_APP`, and `OPENAI_API_KEY` in the
environment first. The sample is intentionally an explicit attachment tool,
not a dialplan router: your Stasis event handler remains responsible for
identifying which two (or more) channels belong to one conversation.

The default OpenAI adapter uses `gpt-live-transcribe`, which is designed for
low-latency transcript deltas from live audio. See OpenAI's [Realtime
transcription guide](https://developers.openai.com/api/docs/guides/realtime-transcription)
for its current session and latency options.

When the RTP gateway runs in a different container or host namespace than
Asterisk, bind it to a reachable interface and give Asterisk a reachable
`external_media_host`; the default loopback values are only for same-host
deployments. See the [local WSL lab runbook](docs/local-wsl-lab.md) for a
tested container topology.

## Terminal demo

With a populated `.env.e2e`, run the curated live demo from PowerShell:

```powershell
.\docker\e2e\demo.ps1
```

It renders the caller-leg topology, runs the isolated FreePBX/Asterisk E2E
call, and replays the caller-labelled transcript events. See the [local WSL
lab runbook](docs/local-wsl-lab.md) for setup.

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

## Real-time ARI implementation

See [`docs/realtime-ari.md`](docs/realtime-ari.md). The implementation lives
in `ari.py`, `rtp.py`, `live.py`, and `openai_realtime.py`. The important rule
is one Snoop/External-Media pipeline **per leg**. A mixed bridge stream can be
useful for an AI voice application, but it is not a reliable speaker-attribution
source after a human joins or takes over.

## Development

Install the package and its ARI/WebSocket dependencies:

```bash
python -m pip install --editable .
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
