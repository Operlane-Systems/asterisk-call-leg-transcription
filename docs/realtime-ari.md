# Real-time ARI transcription topology

## Goal

Produce a live transcript that remains attributable when a bridge contains more
than one person. Do not ask a model to infer who spoke in a mixed audio stream
when Asterisk already knows each channel.

```text
caller channel  -> Snoop(spy=in) -> dedicated bridge -> externalMedia -> RTP gateway A -> transcription A
agent channel   -> Snoop(spy=in) -> dedicated bridge -> externalMedia -> RTP gateway B -> transcription B
```

Each pipeline owns its Snoop channel, bridge, external-media channel, RTP port,
and transcription session. The application assigns labels from the call model
(`caller`, `agent`, `supervisor`) before delivering audio to a transcription
provider.

## Lifecycle requirements

1. Create a Snoop channel for exactly one target call leg.
2. Wait for the Snoop channel to enter the ARI application.
3. Create an `externalMedia` channel pointing to that leg's dedicated RTP
   gateway port and add both helper channels to a dedicated mixing bridge.
4. On hangup or takeover, stop the transcription session and remove/hang up
   helper channels before destroying the bridge.
5. Treat partial setup failure as a cleanup path, not an invitation to fall
   back silently to unlabelled mixed audio.

## Why `spy=in`

The appropriate Snoop direction depends on the channel and bridge topology.
This reference uses a per-target leg and `spy=in` so the pipeline receives the
audio entering that channel. Validate audio direction with a real test call
before assigning speaker labels; channel perspective varies with where the
channel was created.

## Boundaries

The reference implementation is in `src/asterisk_call_leg_transcription/`:

* `ari.py` owns only the ARI resources the pipeline creates.
* `rtp.py` validates RTP headers and uses bounded queues so a slow transcription
  provider never blocks receipt from Asterisk.
* `live.py` owns the ordered setup, Snoop-ready retry, and symmetrical cleanup.
* `openai_realtime.py` is an optional adapter, not a requirement of the ARI
  pipeline.

It does not ship an AI voice agent, a PBX management console, SIP trunk
credentials, or recording-compliance policy. Those remain application concerns.
