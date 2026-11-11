# AURION + Minecraft Bedrock Android

## Status

Planning and compatibility investigation only. This directory is not yet a working integration or an installable add-on.

## User requirement

Keep the official Minecraft Bedrock Android app installed on the phone. AURION supplies the language model and speech; Minecraft remains the game client. Do not replace Minecraft with a clone or a separate game.

## Verified platform constraint

The official Minecraft Script API module `@minecraft/server-net` can make HTTP requests, but Microsoft documents it as available only on Bedrock Dedicated Server. It does not run in the Minecraft game client or Realms. Therefore a normal behavior pack installed into a local Android world cannot directly make HTTP calls to the AURION Android app.

Reference: https://learn.microsoft.com/minecraft/creator/scriptapi/mojang-net/mojang-net

## Viable integration route to validate

Use the official Minecraft Bedrock Android app as a client connected to a Bedrock Dedicated Server (BDS) world. A server-side behavior pack can observe supported player/entity interactions and exchange events with a relay service. The AURION Android app can poll that relay, run the prompt through its local GGUF runtime, and return the NPC response. The server pack then displays the response in the game.

This keeps the original Minecraft Android app, but it means the AI-enabled world is hosted on a compatible BDS server rather than an ordinary single-player local world. Do not describe it as a direct local-world integration.

## Implementation gates

1. Confirm the exact Minecraft Bedrock client version and the BDS version/API modules that can be paired with it.
2. Implement a minimal BDS behavior pack that detects one explicit interaction and emits a structured event.
3. Implement an authenticated relay with expiring pairing codes, per-session isolation, rate limits, and no public unauthenticated endpoints.
4. Add an opt-in AURION bridge screen and background-safe polling while AURION is foregrounded. Route prompts through the existing local inference method; return generated text only after successful inference.
5. Add server-side response delivery and test a full round trip with a real Android Bedrock client.
6. Add NPC identity and conversation memory only after the round trip is reliable.
7. Add voice playback on the Android device after text dialogue works. Do not claim NPC voice inside Minecraft until the audio path is demonstrated.

## Acceptance criteria

- The official Minecraft Bedrock Android client joins the test world.
- An actual in-game interaction creates a server event with a unique correlation ID.
- The event reaches the paired AURION app.
- AURION's local model generates a non-template response.
- The response returns to the same game session and is visible in-game.
- A second interaction proves conversation context is preserved.
- The Android voice path is demonstrated separately and its limitations are stated.
- CI builds the Android app and validates the add-on/relay contracts.
- No milestone is marked complete based on documentation, mock responses, or an APK build alone.

## Important boundary

If the requirement is that the existing single-player local world on Android must work without joining a BDS server, this route does not meet it. That capability needs a separately verified client-side bridge; do not ship a fake or unsupported workaround.
