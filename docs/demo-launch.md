# Demo launch kit

The strongest story in this project is not "AI transcribes a call." It is:

> The PBX already knows who owns each media leg. Use that fact instead of
> making a model guess who spoke.

The demo is intentionally short, visual, and falsifiable. It runs the local
FreePBX/Asterisk lab, sends real caller audio through ARI Snoop and External
Media, and shows OpenAI Realtime STT events labelled by the PBX-controlled
caller leg.

## Capture the proof clip

Use the same populated environment file used by the E2E test. Never show its
contents or enter its API key into a recording.

```powershell
.\docker\e2e\recording-run.ps1 -EnvFile C:\path\to\.env.e2e
```

The script gives OBS a short lead-in, then runs `demo.ps1`. It is a real test,
not a replay. A successful run ends with two green `PASS` statements.

In OBS, create a dedicated scene with these settings:

| Setting | Value |
| --- | --- |
| Source | Window Capture of the dedicated PowerShell window |
| Capture method | `Windows 10 (1903 and up)` |
| Canvas/output | 1920 x 1080, 30 fps |
| Transform | `Fit to Screen` (`Ctrl+F`) |
| Cursor | Off |
| Audio | Off unless narration has been recorded separately |
| Recording | MKV while recording; remux the selected cut to MP4 afterward |

The Windows 10 capture method is particularly useful when standard display
capture has no available monitor (for example, in a remote or virtual display
session). Record only a clean run: the demo must end in `PASS`, otherwise
discard the take and investigate the failure.

## Edit plan: one asset, two placements

Make a 35–50 second master in 16:9. It works as a GitHub README/release asset
and as a LinkedIn native video. Keep the terminal text readable; do not add
background music.

| Time | On-screen moment | Purpose |
| --- | --- | --- |
| 0–3 s | Title: `CALL TRANSCRIPTION WITHOUT DIARIZATION GUESSES` | The hook makes the technical claim before viewers scroll. |
| 3–11 s | The `PJSIP -> ARI Snoop -> External Media -> OpenAI` diagram | Explain the mechanism in one glance. |
| 11–27 s | `RUNNING ... E2E CALL` and the three `[OK]` checks | Establish that this is a running PBX path, not an architecture slide. |
| 27–38 s | The caller-labelled transcript event | Show the attribution result. |
| 38–46 s | Both green `PASS` lines | End on proof, not a logo. |

For LinkedIn, add captions or a terse top-line overlay because many viewers
start muted: `The PBX labels the speaker. The model only transcribes.` For
GitHub, use the same MP4 in the README or a release, together with the exact
command that recreates it.

## GitHub release copy

**Title:** `v0.1.0 — real-time, PBX-attributed call-leg transcription`

**Body:**

This reference implementation shows a different starting point for call
transcription: speaker attribution should come from PBX media topology, not
from diarization after the audio has already been mixed.

The demo runs an isolated FreePBX/Asterisk E2E call and proves this path:

`PJSIP caller -> ARI Snoop -> External Media RTP -> OpenAI Realtime STT -> caller-labelled transcript`

No core Asterisk patches. No public PBX, SIP, or RTP ports. The repo includes
the lab runbook, the E2E harness, and a capture-ready terminal demo.

**Question for the release discussion:** Where do diarization mistakes hurt
you most: QA scoring, compliance, agent assist, or analytics?

## LinkedIn post copy

Most call-transcription demos begin after the call has been mixed.

That is exactly where speaker attribution becomes a guess.

I built an Asterisk/FreePBX reference implementation that starts one layer
lower: with the PBX media topology. Each call leg gets its own ARI Snoop +
External Media RTP path, and the transcription event is labelled by the PBX
that owns the leg.

The clip is a real local E2E run: SIP call accepted, caller-leg media routed,
OpenAI Realtime STT emits the caller-labelled transcript.

No core patches. No diarization required for caller/agent identity.

I am especially interested in feedback from people operating FreePBX or
Asterisk in production: would you rather trust diarization, or preserve
identity at the PBX media layer? What failure mode matters most in your
environment?

Repo: https://github.com/Operlane-Systems/asterisk-call-leg-transcription

#Asterisk #FreePBX #VoIP #OpenSource #SpeechToText

## Comment prompts and replies

Ask one real technical question, then stay present in the thread. These are
good prompts because they invite counterexamples rather than empty praise:

* "Where does diarization break down first in your call flow?"
* "Would per-leg attribution change how you score QA or satisfy compliance?"
* "If you run Asterisk 20–22, what edge case should this lab prove next?"

Useful concise replies:

* **"Why not just diarize?"** — Diarization can still add value to a mixed
  recording; it is not the source of caller/agent identity in this design.
* **"Does it need an Asterisk patch?"** — No. It uses ARI Snoop and External
  Media plus additive FreePBX custom configuration.
* **"Can I reproduce it?"** — Yes. The local WSL lab runbook and E2E command
  are in the repository; use a non-production PBX and your own test account.

## Publishing order

1. Upload the final MP4 to the GitHub release and link it from the README.
2. Publish the LinkedIn post natively with the same master, using the question
   above as the closing line.
3. Reply to early technical comments with exact implementation details and a
   link to the reproducible test—not a sales pitch.
4. After the GitHub discussion has a few concrete questions, adapt the same
   post for the FreePBX and Asterisk communities with their compatibility
   question front and center.
