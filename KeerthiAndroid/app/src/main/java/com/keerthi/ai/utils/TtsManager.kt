package com.keerthi.ai.utils

import android.content.Context
import android.speech.tts.TextToSpeech
import java.util.Locale

object TtsManager {
    private var tts: TextToSpeech? = null
    private var ready = false

    fun init(context: Context) {
        if (tts != null) return
        tts = TextToSpeech(context.applicationContext) { status ->
            ready = status == TextToSpeech.SUCCESS
            if (ready) tts?.language = Locale.US
        }
    }

    fun speak(text: String) {
        if (!ready) return
        val clean = text.replace(Regex("\\[ACTION:[^\\]]+\\]"), "").trim()
        if (clean.isBlank()) return
        tts?.speak(clean, TextToSpeech.QUEUE_FLUSH, null, "keerthi_utterance")
    }

    fun shutdown() {
        tts?.stop()
        tts?.shutdown()
        tts = null
        ready = false
    }
}
