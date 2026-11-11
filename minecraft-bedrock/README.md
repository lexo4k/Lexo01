# AURION + Minecraft Bedrock Android

## Status

The relay prototype and automated contract tests are now present. The Android-to-relay bridge, Bedrock behavior pack, hosted relay deployment, and real game round-trip are **not yet implemented or validated**. This directory is not yet an installable Minecraft add-on or a completed integration.

## User requirement

Keep the official Minecraft Bedrock Android app installed on the phone. AURION supplies the language model and speech; Minecraft remains the game client. Do not replace Minecraft with a clone or a separate game.

## Verified platform constraint

Microsoft documents `@minecraft/server-net` as available only on Bedrock Dedicated Server. It does not run in the Minecraft game client or Realms. This means a normal behavior pack installed into a local Android world cannot directly make HTTP calls to AURION.

Reference: [Microsoft server-net module](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server-net/minecraft-server-net?view=minecraft-bedrock-experimental).

The currently documented module is still pre-release and lists a preview-specific version. Microsoft also states that regular Bedrock clients must use a regular compatible server, while Preview clients use Preview servers. The exact client/BDS/API version combination must therefore be confirmed before selecting a pack manifest dependency. Do not assume a preview API pack will work with the user's ordinary Play Store client.

References:
- [Microsoft server-net module and version notes](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server-net/minecraft-server-net?view=minecraft-bedrock-experimental)
- [Microsoft Bedrock Dedicated Server setup and client compatibility](https://help.minecraft.net/hc/en-us/articles/49914677714957)

## Candidate integration route

The candidate architecture keeps the official Android Bedrock app as the game client, connected to a compatible Bedrock Dedicated Server world. A server-side behavior pack can observe supported player/entity interactions and exchange events with a relay service. AURION polls the relay while foregrounded, invokes its existing local GGUF inference method, and sends the generated response back. The server pack then displays the response in the same game session.

This keeps the original Minecraft app, but the AI-enabled world would be hosted on a compatible BDS server rather than an ordinary local single-player world. Compatibility with the user's exact Play Store game version is still an open gate.

## Relay prototype

`relay/` contains a small FastAPI relay service and contract tests.

- Pairing codes are eight digits and expire after five minutes.
- Claiming a code is one-time and creates separate high-entropy app and server bearer tokens.
- App and server tokens are side-scoped and stored as SHA-256 digests in relay memory.
- Events and replies are isolated by paired session.
- Duplicate event IDs are rejected, event queues are bounded, and session/IP request rates are limited.
- The relay transports messages only. It does not generate NPC dialogue or call a hosted AI model.
- State is in-memory and will be lost on restart. This is a prototype, not a production persistence guarantee.
- The service has not been deployed. The Render blueprint is supplied as a deployment starting point only.

The server token must remain in BDS server-side secret configuration, never in a downloadable behavior pack. The app token must be stored in Android private secure storage once the Android bridge is implemented.

## Implementation gates

1. Confirm the exact Minecraft Bedrock Android client version and a compatible BDS/API version, including whether the required server-net module is available to that release.
2. Implement a minimal BDS behavior pack that detects one explicit interaction and emits a structured event.
3. Deploy and harden the relay, including persistent storage or an explicit session-recovery policy.
4. Add an opt-in AURION bridge screen and foreground polling. Route prompts through the existing local inference method; only return generated text after successful inference.
5. Add server-side response delivery and test a full round trip with a real Android Bedrock client.
6. Add NPC identity and conversation memory only after the round trip is reliable.
7. Demonstrate Android voice playback for returned NPC dialogue. Do not claim that speech is audible inside Minecraft until that separate audio path is demonstrated.

## Acceptance criteria

- The official Minecraft Bedrock Android client joins the compatible test world.
- An actual in-game interaction creates a server event with a unique correlation ID.
- The event reaches the paired AURION app.
- AURION's local model generates a non-template response.
- The response returns to the same game session and is visible in-game.
- A second interaction proves conversation context is preserved.
- The Android voice path is demonstrated separately and its limitations are stated.
- CI builds the Android app and validates the add-on/relay contracts.
- No milestone is marked complete based on documentation, mock responses, or an APK build alone.

## Important boundary

If the requirement is that the existing single-player local world on Android must work without joining a BDS server, the current candidate route does not meet it. That capability needs a separately verified client-side bridge; do not ship a fake or unsupported workaround.
