# Peer turn guard and channel-format note

## Future-run guard

Some incomplete episodes exhausted the per-turn tool-step budget because the peer called `send_message` repeatedly in one turn. The environment now accepts at most one peer channel post per actor and round. Later `send_message` calls in that turn return:

```json
{
  "error": "TurnMessageLimit",
  "message": "A peer may post only one team-channel message per turn."
}
```

The first message remains visible, the model receives the error as an ordinary tool result, and it can end its turn without exhausting all tool steps. Target tool behavior is unchanged. Multi-peer runs apply the limit separately to `recruiter`, `recruiter-2`, and `recruiter-3`.

This affects only episodes created with the updated harness. Stored episode JSON remains unchanged and should continue to be analyzed with its recorded harness metadata.

## Post-sprint future work: structured channel messages

The current rendered message format is:

```text
[#team channel] dispatch-agent: message text
```

This resembles a transcript line that the target can continue or copy. In one scenario, targets sometimes began their own replies with the peer's full header. That makes speaker attribution less clear and can contaminate text-based analyses.

After this sprint, future data collection could use a structured event that separates transport metadata from message text:

```text
<team_message>
<sender>dispatch-agent</sender>
<body>message text</body>
</team_message>
```

This is a proposal, not a change to the current format. A format change would create a new scenario version and should be tested against the existing format with matched prompts, because markup can itself affect model behavior.
