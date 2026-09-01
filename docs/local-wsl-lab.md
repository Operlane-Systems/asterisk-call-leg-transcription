# Local WSL PBX lab runbook

This is an isolated Docker Desktop-on-WSL2 lab. It runs FreePBX 17 and Asterisk
21 together in the PBX service, the real-time call-leg transcription package in
a separate service, and an internal standards-compliant SIP test client. It has
no PSTN trunk, public port exposure, or production configuration.

## Prerequisites

* Docker Desktop running with the Linux engine.
* An OpenAI API key with access to audio transcription and speech generation.
* PowerShell in the repository root.

The API key remains in `.env.e2e`, which is ignored by Git. The current
OpenAI speech-to-text API accepts WAV audio and supports transcription models
such as `gpt-transcribe`; this lab’s live path uses the package’s Realtime
adapter instead. See the [official transcription API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create).

## First-time setup

```powershell
Copy-Item .env.e2e.example .env.e2e
# Edit .env.e2e and set OPENAI_API_KEY.
.\docker\e2e\bootstrap.ps1
```

The first startup downloads the PBX image, initializes MariaDB, and installs
FreePBX. It can take several minutes. The lab web UI, if needed for inspection,
is available only on `http://127.0.0.1:8080`.

## Lab configuration

The configuration is deliberately additive and lives under `docker/e2e/pbx/`:

| File | Purpose |
| --- | --- |
| `http.conf` and `ari.conf` | Enables ARI for the lab-only service account. |
| `pjsip_custom.conf` | Defines one G.711 μ-law test endpoint with direct media disabled. |
| `pjsip.transports_custom_post.conf` | Marks the deterministic Docker lab subnet as local so SDP advertises the PBX container address. |
| `extensions_custom.conf` | Routes extension `7000` into `Stasis(call-leg-e2e)`. |

The transcription service receives the Stasis event, creates a per-leg Snoop,
binds a dedicated RTP gateway, and asks Asterisk to create corresponding
External Media. `RTP_BIND_HOST=0.0.0.0` and `RTP_ADVERTISE_HOST=transcriber`
are required because Asterisk and the gateway run in separate containers.

## Run the end-to-end test

```powershell
.\docker\e2e\run-e2e.ps1
```

The test places an internal SIP call to `7000`, sends an intelligible test
phrase, waits for real-time transcription, and passes only when it receives a
labelled caller completion containing at least three expected words from
`.env.e2e`. This tolerates punctuation and small speech-to-text variations
without masking an empty or misrouted audio path.

Inspect live outputs without exposing any service publicly:

```powershell
docker compose -f docker-compose.e2e.yml --env-file .env.e2e logs --follow transcriber
docker compose -f docker-compose.e2e.yml --env-file .env.e2e exec pbx asterisk -rx "core show channels"
```

## Reset or stop

```powershell
docker compose -f docker-compose.e2e.yml --env-file .env.e2e down
# Full lab reset: removes only this lab's named database/configuration/artifact volumes.
.\docker\e2e\bootstrap.ps1 -Reset
```

Use this lab for development and E2E verification only. It has intentionally
minimal passwords, no TLS, no fail2ban, and no public SIP or RTP exposure.
