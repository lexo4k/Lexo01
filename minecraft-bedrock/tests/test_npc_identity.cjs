const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const scriptPath = path.join(__dirname, "..", "behavior-pack", "scripts", "main.js");
const source = fs.readFileSync(scriptPath, "utf8");
const start = source.indexOf("function safeLabel(value");
const end = source.indexOf("function makeEventId()", start);
assert.ok(start >= 0 && end > start, "NPC identity helper must remain in the behavior pack entry script");

const context = {
    Date,
    Math,
    NPC_ID_PROPERTY: "aurion:npc_identity",
    console: { warn() {} },
};
vm.runInNewContext(
    source.slice(start, end) + "\nglobalThis.stableNpcIdentity = stableNpcIdentity;",
    context,
);

const properties = new Map();
const entity = {
    id: "runtime-entity-1",
    getDynamicProperty(name) {
        return properties.get(name);
    },
    setDynamicProperty(name, value) {
        properties.set(name, value);
    },
};

const firstIdentity = context.stableNpcIdentity(entity);
const secondIdentity = context.stableNpcIdentity(entity);
assert.equal(firstIdentity, secondIdentity, "the same entity must retain its persisted identity");
assert.match(firstIdentity, /^aurion-npc-[a-z0-9-]+$/);
assert.equal(properties.get("aurion:npc_identity"), firstIdentity);

const unsupportedEntity = {
    id: "legacy-entity",
    getDynamicProperty() {
        throw new Error("dynamic properties unavailable");
    },
    setDynamicProperty() {
        throw new Error("dynamic properties unavailable");
    },
};
assert.equal(
    context.stableNpcIdentity(unsupportedEntity),
    "runtime-legacy-entity",
    "unsupported persistence must be clearly marked as a runtime-only fallback",
);

console.log("Bedrock NPC identity persistence tests passed.");
