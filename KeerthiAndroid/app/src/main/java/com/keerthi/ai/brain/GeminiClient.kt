package com.keerthi.ai.brain

import com.keerthi.ai.data.ChatMessage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Talks to the Gemini REST API directly (same brand/model family as the original
 * KeerthiAI desktop app). Requires the user to supply their own API key in Settings —
 * a standalone Android app has no built-in key injection the way an Anthropic
 * artifact does.
 */
object GeminiClient {

    private const val MODEL = "gemini-2.0-flash"
    private const val BASE = "https://generativelanguage.googleapis.com/v1beta/models/$MODEL"
    private const val ENDPOINT = "$BASE:generateContent"
    private const val STREAM_ENDPOINT = "$BASE:streamGenerateContent"

    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private fun buildRequestBody(systemPrompt: String, history: List<ChatMessage>): JSONObject {
        val contents = JSONArray()
        history.forEach { msg ->
            if (msg.role == "user" || msg.role == "assistant") {
                val role = if (msg.role == "assistant") "model" else "user"
                val part = JSONObject().put("text", msg.text)
                val entry = JSONObject()
                    .put("role", role)
                    .put("parts", JSONArray().put(part))
                contents.put(entry)
            }
        }
        return JSONObject()
            .put("contents", contents)
            .put(
                "systemInstruction",
                JSONObject().put(
                    "parts",
                    JSONArray().put(JSONObject().put("text", systemPrompt))
                )
            )
            .put(
                "generationConfig",
                JSONObject().put("maxOutputTokens", 1000)
            )
    }

    private fun textOf(candidate: JSONObject): String {
        val parts = candidate.getJSONObject("content").getJSONArray("parts")
        val text = StringBuilder()
        for (i in 0 until parts.length()) text.append(parts.getJSONObject(i).optString("text"))
        return text.toString()
    }

    /** Extracts the text delta from one raw SSE line, or null if the line carries none
     *  (a non-`data:` line, a heartbeat, or a chunk with no candidates). Pure/testable —
     *  see [GeminiClientTest]. */
    internal fun chunkTextFrom(sseLine: String): String? {
        if (!sseLine.startsWith("data:")) return null
        val payload = sseLine.removePrefix("data:").trim()
        if (payload.isEmpty()) return null
        val candidates = JSONObject(payload).optJSONArray("candidates") ?: return null
        if (candidates.length() == 0) return null
        return textOf(candidates.getJSONObject(0)).ifEmpty { null }
    }

    suspend fun send(apiKey: String, systemPrompt: String, history: List<ChatMessage>): String =
        withContext(Dispatchers.IO) {
            if (apiKey.isBlank()) {
                return@withContext "I don't have a Gemini API key yet — add one in Settings to let me think."
            }
            try {
                val request = Request.Builder()
                    .url("$ENDPOINT?key=$apiKey")
                    .post(buildRequestBody(systemPrompt, history).toString().toRequestBody("application/json".toMediaType()))
                    .build()

                client.newCall(request).execute().use { resp ->
                    val raw = resp.body?.string().orEmpty()
                    if (!resp.isSuccessful) {
                        return@withContext "Gemini request failed (${resp.code}). Check your API key in Settings."
                    }
                    val json = JSONObject(raw)
                    val candidates = json.optJSONArray("candidates") ?: return@withContext "I hit a technical snag. Please try that again."
                    if (candidates.length() == 0) return@withContext "I hit a technical snag. Please try that again."
                    textOf(candidates.getJSONObject(0)).trim().ifBlank { "I hit a technical snag. Please try that again." }
                }
            } catch (e: Exception) {
                "I hit a technical snag reaching Gemini: ${e.message}"
            }
        }

    /**
     * Same request as [send], but reads the response as an SSE stream and invokes [onChunk] for
     * each incremental piece of text as it arrives, so the UI can render tokens as they land
     * instead of waiting for the full reply. Returns the full concatenated reply at the end, or
     * an error string via a single [onChunk] call — same fallback messages as [send].
     */
    suspend fun stream(
        apiKey: String,
        systemPrompt: String,
        history: List<ChatMessage>,
        onChunk: (String) -> Unit
    ): String = withContext(Dispatchers.IO) {
        if (apiKey.isBlank()) {
            val msg = "I don't have a Gemini API key yet — add one in Settings to let me think."
            onChunk(msg)
            return@withContext msg
        }
        try {
            val request = Request.Builder()
                .url("$STREAM_ENDPOINT?alt=sse&key=$apiKey")
                .post(buildRequestBody(systemPrompt, history).toString().toRequestBody("application/json".toMediaType()))
                .build()

            client.newCall(request).execute().use { resp ->
                if (!resp.isSuccessful) {
                    val msg = "Gemini request failed (${resp.code}). Check your API key in Settings."
                    onChunk(msg)
                    return@withContext msg
                }
                val source = resp.body?.source() ?: run {
                    val msg = "I hit a technical snag. Please try that again."
                    onChunk(msg)
                    return@withContext msg
                }
                val full = StringBuilder()
                while (!source.exhausted()) {
                    val line = source.readUtf8Line() ?: break
                    val piece = chunkTextFrom(line) ?: continue
                    full.append(piece)
                    onChunk(piece)
                }
                full.toString().trim().ifBlank { "I hit a technical snag. Please try that again." }
            }
        } catch (e: Exception) {
            val msg = "I hit a technical snag reaching Gemini: ${e.message}"
            onChunk(msg)
            msg
        }
    }
}
