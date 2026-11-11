package com.lexo.lumen

import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit

/**
 * HTTPS client for the AURION <-> Bedrock relay.
 *
 * This class deliberately does not run inference. The Android activity must
 * pass received game events to the existing local GGUF engine and submit only
 * its generated answer through submitReply().
 */
internal class MinecraftRelayClient(baseUrl: String) {
    private val root: String

    init {
        val normalized = baseUrl.trim().trimEnd('/')
        require(normalized.startsWith("https://")) {
            "O relay Minecraft precisa usar HTTPS."
        }
        require(normalized.length <= 512) { "Endereço do relay inválido." }
        root = normalized
    }

    data class PairingStart(
        val pairingCode: String,
        val appToken: String,
        val expiresInSeconds: Int
    )

    data class PairingClaim(
        val sessionId: String,
        val serverToken: String
    )

    data class GameEvent(
        val eventId: String,
        val eventType: String,
        val player: String,
        val npc: String,
        val message: String,
        val worldId: String
    )

    data class NpcReply(
        val eventId: String,
        val npc: String,
        val message: String
    )

    fun startPairing(): PairingStart {
        val json = request("POST", "/v1/pair/start")
        return PairingStart(
            pairingCode = json.getString("pairing_code"),
            appToken = json.getString("app_token"),
            expiresInSeconds = json.getInt("expires_in")
        )
    }

    fun claimPairing(code: String): PairingClaim {
        require(code.matches(Regex("[0-9]{8}"))) { "O código precisa ter oito dígitos." }
        val json = request(
            "POST",
            "/v1/pair/claim",
            body = JSONObject().put("pairing_code", code)
        )
        return PairingClaim(
            sessionId = json.getString("session_id"),
            serverToken = json.getString("server_token")
        )
    }

    fun fetchEvents(appToken: String): List<GameEvent> {
        val rows = request("GET", "/v1/app/events", bearer = appToken).optJSONArray("events")
            ?: JSONArray()
        return buildList {
            for (index in 0 until rows.length()) {
                val item = rows.optJSONObject(index) ?: continue
                add(
                    GameEvent(
                        eventId = item.getString("event_id"),
                        eventType = item.getString("event_type"),
                        player = item.getString("player"),
                        npc = item.getString("npc"),
                        message = item.optString("message"),
                        worldId = item.optString("world_id", "default")
                    )
                )
            }
        }
    }

    fun submitReply(appToken: String, reply: NpcReply) {
        request(
            "POST",
            "/v1/app/replies",
            bearer = appToken,
            body = JSONObject()
                .put("event_id", reply.eventId)
                .put("npc", reply.npc)
                .put("message", reply.message)
        )
    }

    fun fetchServerReplies(serverToken: String): List<NpcReply> {
        val rows = request("GET", "/v1/server/replies", bearer = serverToken)
            .optJSONArray("replies") ?: JSONArray()
        return buildList {
            for (index in 0 until rows.length()) {
                val item = rows.optJSONObject(index) ?: continue
                add(
                    NpcReply(
                        eventId = item.getString("event_id"),
                        npc = item.getString("npc"),
                        message = item.getString("message")
                    )
                )
            }
        }
    }

    fun acknowledgeDeliveredReply(serverToken: String, eventId: String) {
        request(
            "POST",
            "/v1/server/ack",
            bearer = serverToken,
            body = JSONObject().put("event_id", eventId)
        )
    }

    private fun request(
        method: String,
        path: String,
        bearer: String? = null,
        body: JSONObject? = null
    ): JSONObject {
        val connection = (URL(root + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = TimeUnit.SECONDS.toMillis(8).toInt()
            readTimeout = TimeUnit.SECONDS.toMillis(12).toInt()
            useCaches = false
            setRequestProperty("Accept", "application/json")
            if (bearer != null) setRequestProperty("Authorization", "Bearer $bearer")
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
            }
        }
        try {
            if (body != null) {
                connection.outputStream.use { output ->
                    output.write(body.toString().toByteArray(Charsets.UTF_8))
                }
            }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val response = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (status !in 200..299) {
                val detail = try { JSONObject(response).optString("detail") } catch (_: Exception) { "" }
                throw IllegalStateException(
                    if (detail.isNotBlank()) detail else "Relay respondeu HTTP $status."
                )
            }
            return if (response.isBlank()) JSONObject() else JSONObject(response)
        } finally {
            connection.disconnect()
        }
    }
}
