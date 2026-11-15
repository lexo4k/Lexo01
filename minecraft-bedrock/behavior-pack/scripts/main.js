import { world, system } from "@minecraft/server";
import { ModalFormData } from "@minecraft/server-ui";

const EVENT_MARKER = "AURION_EVENT ";
const WORLD_ID = "aurion-bds-world";
const PLAYER_COOLDOWN_MS = 15000;
const lastInteractionByPlayer = new Map();
const openFormsByPlayer = new Set();
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

function emitChatEvent(playerName, playerKey, npcName, npcId, npcType, message) {
    const now = Date.now();
    const previous = lastInteractionByPlayer.get(playerKey) || 0;
    if (now - previous < PLAYER_COOLDOWN_MS) return false;
    lastInteractionByPlayer.set(playerKey, now);

    const payload = {
        event_id: makeEventId(),
        event_type: "chat",
        player: playerName,
        npc: npcName,
        npc_id: npcId,
        npc_type: npcType,
        message: message,
        world_id: WORLD_ID
    };
    console.warn(EVENT_MARKER + JSON.stringify(payload));
    return true;
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

        const playerKey = safeLabel(player.id, player.name, 80);
        if (openFormsByPlayer.has(playerKey)) return;

        const npcName = nameTag || typeId.replace(/^minecraft:/, "");
        const playerName = safeLabel(player.name, "Jogador", 48);
        const npcId = safeLabel(target.id, "", 128);
        openFormsByPlayer.add(playerKey);

        // Defer the form until the interaction callback has returned to the game loop.
        system.run(() => {
            new ModalFormData()
                .title("Conversar com " + npcName)
                .textField("Sua mensagem", "Digite o que deseja dizer ao NPC")
                .show(player)
                .then((response) => {
                    openFormsByPlayer.delete(playerKey);
                    if (response.canceled) return;
                    const rawMessage = response.formValues && response.formValues[0];
                    const message = safeLabel(rawMessage, "", 500);
                    if (!message) {
                        player.sendMessage("§7Digite uma mensagem para conversar com §b" + npcName + "§7.");
                        return;
                    }
                    if (emitChatEvent(playerName, playerKey, npcName, npcId, typeId, message)) {
                        player.sendMessage("§7Mensagem enviada ao §b" + npcName + "§7. AURION está preparando a resposta.");
                    } else {
                        player.sendMessage("§7Aguarde um instante antes de falar novamente com um NPC.");
                    }
                })
                .catch((error) => {
                    openFormsByPlayer.delete(playerKey);
                    console.error("[AURION] Não foi possível abrir o formulário de conversa: " + String(error));
                    try {
                        player.sendMessage("§cNão consegui abrir a conversa com AURION. Tente interagir novamente.");
                    } catch (_) {}
                });
        });
    } catch (error) {
        console.error("[AURION] Falha ao iniciar conversa com NPC: " + String(error));
    }
});

console.warn("[AURION] Behavior pack ativo. Aguardando conversa com NPC identificado.");
