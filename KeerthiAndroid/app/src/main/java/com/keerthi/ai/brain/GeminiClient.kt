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
    private const val ENDPOINT =
        "https://generativelanguage.googleapis.com/v1beta/models/$MODEL:generateContent"

    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    suspend fun send(apiKey: String, systemPrompt: String, history: List<ChatMessage>): String =
        withContext(Dispatchers.IO) {
            if (apiKey.isBlank()) {
                return@withContext "I don't have a Gemini API key yet — add one in Settings to let me think."
            }
            try {
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

                val body = JSONObject()
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

                val request = Request.Builder()
                    .url("$ENDPOINT?key=$apiKey")
                    .post(body.toString().toRequestBody("application/json".toMediaType()))
                    .build()

                client.newCall(request).execute().use { resp ->
                    val raw = resp.body?.string().orEmpty()
                    if (!resp.isSuccessful) {
                        return@withContext "Gemini request failed (${resp.code}). Check your API key in Settings."
                    }
                    val json = JSONObject(raw)
                    val candidates = json.optJSONArray("candidates") ?: return@withContext "I hit a technical snag. Please try that again."
                    if (candidates.length() == 0) return@withContext "I hit a technical snag. Please try that again."
                    val parts = candidates.getJSONObject(0)
                        .getJSONObject("content")
                        .getJSONArray("parts")
                    val text = StringBuilder()
                    for (i in 0 until parts.length()) {
                        text.append(parts.getJSONObject(i).optString("text"))
                    }
                    text.toString().trim().ifBlank { "I hit a technical snag. Please try that again." }
                }
            } catch (e: Exception) {
                "I hit a technical snag reaching Gemini: ${e.message}"
            }
        }
}
