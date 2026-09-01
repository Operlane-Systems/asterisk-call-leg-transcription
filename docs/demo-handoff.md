# Demo completion handoff

## Objective

Create one polished, technically honest demonstration for both the GitHub
repository and LinkedIn. It must establish professional credibility for
Operlane Systems and Daniel Haines by showing that real-time, per-leg call
transcription works end to end with Asterisk/FreePBX.

The demo must make the following point clear within the first few seconds:

> Speaker identity comes from PBX media topology; the model transcribes the
> labelled leg instead of guessing speakers from mixed audio.

## Non-negotiable proof requirements

The final clip must be a successful real E2E run, not a mocked terminal,
pre-rendered output, or architecture-only presentation.

It must visibly show:

1. The topology: `PJSIP caller -> ARI Snoop -> External Media RTP -> OpenAI
   Realtime STT`.
2. The isolated FreePBX/Asterisk E2E call running.
3. Successful service/path checks.
4. A transcript event explicitly labelled `caller`.
5. The final green `PASS` statements.

It must also make the generated caller speech **audible**. The audio and the
visible caller-labelled transcript should overlap long enough for viewers to
connect cause and effect. Do not show or record real customer audio, API keys,
or PBX management credentials.

## Target formats

Make a 35–50 second 16:9 master at 1920 x 1080 and 30 fps.

Use it in two places:

* **GitHub:** attach the MP4 to the initial release and link it near the demo
  command in the README.
* **LinkedIn:** upload the same master as a native video. Add captions or a
  concise text overlay because many viewers start muted.

There is no authorization to publish the GitHub release or LinkedIn post in
this handoff. Prepare the assets and copy; ask before uploading or posting.

## Recording storyboard

| Time | Moment | Viewer takeaway |
| --- | --- | --- |
| 0–3 s | Overlay/title: `CALL TRANSCRIPTION WITHOUT DIARIZATION GUESSES` | Establish the differentiating claim immediately. |
| 3–10 s | Terminal topology diagram | Show why attribution is deterministic. |
| 10–25 s | E2E call begins and the caller test phrase becomes audible | This is an actual PBX media path. |
| 20–32 s | Audible speech overlaps the live caller-labelled transcript event | The PBX label, not model inference, assigns speaker identity. |
| 32–42 s | The three `[OK]` lines and final `PASS` lines | End on reproducible proof. |
| 42–46 s | Small closing overlay: `Open source reference implementation` | Direct viewers to the repository without a sales pitch. |

Suggested on-screen sentence for the overlap moment:

> `The PBX labels the speaker. The model only transcribes.`

## Audio specification

The current caller harness synthesizes the known test phrase and sends it over
the isolated SIP call. The transcript uses OpenAI Realtime STT from the
caller-leg RTP path.

The existing E2E terminal demo proves the transcription path, but terminal
recording alone does not make the generated caller audio audible. For the
finished video, capture or add the **same synthetic test phrase** as program
audio in sync with the live E2E run. Prefer a direct recording of the test
audio output; if that is not practical, a synchronized playback of that exact
synthetic phrase is acceptable only when the terminal run itself remains real
and the edit does not imply a different audio source.

Avoid background music. Voice/phrase clarity is more important than energy.
Keep audio at a comfortable, consistent level and make no real calls.

## Working project state

Repository:

`C:\Users\Dan\Desktop\Projects\asterisk-call-leg-transcription`

Public remote:

`https://github.com/Operlane-Systems/asterisk-call-leg-transcription`

Current branch:

`master`

Important commits:

* `387fd73` — presentation-ready terminal demo
* `645832f` — recording-ready demo launch kit
* `fa54e63` — Windows PowerShell-safe Docker Compose handling

Core commands:

```powershell
# Full real E2E / curated terminal demo
.\docker\e2e\demo.ps1 -EnvFile C:\path\to\.env

# Same demo with a short lead-in for a recording
.\docker\e2e\recording-run.ps1 -EnvFile C:\path\to\.env

# Tests
python -m unittest discover -s tests -v
```

Do not print or commit the `.env` file. It contains the OpenAI key used for
the real STT E2E test.

## Known environment details

* Docker Desktop is using its local Linux engine. The active local lab services
  are `db`, `pbx`, and `transcriber` under the Compose project
  `asterisk-call-leg-e2e`.
* The PBX UI is local-only at `127.0.0.1:8080`.
* The E2E path has passed previously with real OpenAI STT and caller-labelled
  output.
* `docker compose` writes normal progress to stderr. The scripts in `fa54e63`
  now tolerate this correctly in Windows PowerShell 5.1 and still fail on a
  non-zero Docker exit code.
* Use ASCII in terminal-facing demo output. The em dash rendered as mojibake in
  one Windows PowerShell capture.

## OBS control and capture

OBS version observed earlier: 32.2.2.

The supplied WebSocket endpoint is:

* IP: `192.168.0.227`
* Port: `4455`

An earlier connectivity check failed both against this address and localhost;
the user has since stated that OBS is up. Re-test before use. If the endpoint
requires authentication, obtain the generated obs-websocket password from the
user; never write it into source control or display it in a recording.

Use obs-websocket for deterministic control where possible:

* create/select a dedicated demo scene;
* add the intended terminal/window capture and program-audio source;
* start/stop recording;
* verify the active scene, source state, recording state, and output path.

Recommended capture settings:

| Setting | Value |
| --- | --- |
| Canvas/output | 1920 x 1080 |
| Frame rate | 30 fps |
| Terminal capture | Window Capture |
| Window method | `Windows 10 (1903 and up)` |
| Transform | Fit to Screen |
| Cursor | Hidden |
| Recording container | MKV while recording, then remux selected take to MP4 |

The normal OBS Display Capture source had no available monitor in this remote
session. Window Capture with `Windows 10 (1903 and up)` did render terminal
and Chromium windows.

Create a **new** Window Capture source after the dedicated terminal is visible.
Do not reuse a source bound to a previous Windows Terminal tab: OBS can retain
the old tab's pixels even when the title is identical. Several diagnostic MKV
takes may exist in `C:\Users\Dan\Videos`; they are not approved publishing
assets and should not be used.

## Engagement direction

The desired tone is credible, technical, and invitational—not promotional.
The clip should provoke useful implementation comments from Asterisk/FreePBX
operators, consultants, MSPs, and voice/AI developers.

Best closing question for LinkedIn:

> If you operate Asterisk or FreePBX in production, would you rather trust
> diarization or preserve identity at the PBX media layer? Which failure mode
> matters most in your environment?

Ready-to-edit GitHub release copy, LinkedIn post copy, comment prompts, and
the publishing order are in [`demo-launch.md`](demo-launch.md).

## Guardrails

* Do not claim that diarization is useless; it can still be useful for mixed
  recordings. The claim is that it should not be the source of caller/agent
  identity when PBX media topology can provide that identity.
* Do not say that no code is required. The accurate claim is: no **core
  Asterisk patches** are required.
* Do not expose the OpenAI API key, credentials, real call recordings, public
  SIP/RTP ports, or PBX management interfaces.
* Do not mention the specific SIP caller test library in public-facing docs or
  posts. Keep the demo and runbook SIP-phone agnostic.
* Do not publish to GitHub, LinkedIn, forums, or Reddit without explicit user
  confirmation.
