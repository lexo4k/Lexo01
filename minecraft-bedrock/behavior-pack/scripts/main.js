import { world } from "@minecraft/server";

const EVENT_MARKER = "AURION_EVENT ";
const WORLD_ID = "aurion-bds-world";
const PLAYER_COOLDOWN_MS = 15000;
const lastInteractionByPlayer = new Map();
let eventSequence = 0;

function safeLabel(value, fallback, limit) {
    const text = typeof value === "string" ? value.trim() : "";
    if (!text) return fallback;
    return text.replace(/[\u0000-\u001f\u007f]/g, "").slice(0, limit) || fallback;
}

function makeEventId() {
    eventSequence += 1;
    return "aurion-" + Date.now().toString(36) + "-" +
        eventSequence.toString(36) + "-" +
        Math.random().toString(36).slice(2, 10);
}

world.afterEvents.playerInteractWithEntity.subscribe((event) => {
    try {
        const player = event.player;
        const target = event.target;
        if (!player || !target || target.typeId === "minecraft:player") return;

        const typeId = safeLabel(target.typeId, "entity", 80);
        const nameTag = safeLabel(target.nameTag, "", 80);
        const isNpc = typeId === "minecraft:npc" ||
            typeId.endsWith(":npc") || nameTag.length > 0;
        if (!isNpc) return;

        const now = Date.now();
        const playerKey = safeLabel(player.id, player.name, 80);
        const previous = lastInteractionByPlayer.get(playerKey) || 0;
        if (now - previous < PLAYER_COOLDOWN_MS) return;
        lastInteractionByPlayer.set(playerKey, now);

        const npcName = nameTag || typeId.replace(/^minecraft:/, "");
        const payload = {
            event_id: makeEventId(),
            event_type: "interaction",
            player: safeLabel(player.name, "Jogador", 48),
            npc: npcName,
            message: "",
            world_id: WORLD_ID
        };

        console.warn(EVENT_MARKER + JSON.stringify(payload));
        player.sendMessage("§7AURION registrou sua interação com §b" + npcName + "§7.");
    } catch (error) {
        console.error("[AURION] Falha ao registrar interação: " + String(error));
    }
});

console.warn("[AURION] Behavior pack ativo. Aguardando interação com NPC identificado.");
