package com.keerthi.ai.data

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.keerthi.ai.brain.AlarmScheduler
import com.keerthi.ai.brain.GeminiClient
import com.keerthi.ai.brain.SystemPrompt
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.UUID

class KeerthiViewModel(application: Application) : AndroidViewModel(application) {

    private val _state = MutableStateFlow(KeerthiState())
    val state: StateFlow<KeerthiState> = _state.asStateFlow()

    private val _thinking = MutableStateFlow(false)
    val thinking: StateFlow<Boolean> = _thinking.asStateFlow()

    init {
        viewModelScope.launch {
            val loaded = PrefsStore.load(getApplication())
            // drop anything that already fired while the app was closed
            val now = System.currentTimeMillis()
            _state.value = loaded.copy(
                timers = loaded.timers.filter { it.endTs > now },
                scheduled = loaded.scheduled.filter { it.runTs > now }
            )
        }
    }

    private fun update(block: (KeerthiState) -> KeerthiState) {
        _state.value = block(_state.value)
        persist()
    }

    private fun persist() {
        viewModelScope.launch { PrefsStore.save(getApplication(), _state.value) }
    }

    fun setApiKey(key: String) = update { it.copy(apiKey = key) }
    fun setVoiceOut(on: Boolean) = update { it.copy(voiceOutEnabled = on) }

    fun clearChat() = update { it.copy(chat = emptyList()) }

    fun addChat(role: String, text: String) = update {
        val next = it.chat + ChatMessage(role, text)
        it.copy(chat = if (next.size > 40) next.takeLast(40) else next)
    }

    // ---- tasks ----
    fun addTask(text: String): String {
        if (text.isBlank()) return "need a task description"
        update { it.copy(tasks = it.tasks + TaskItem(UUID.randomUUID().toString(), text)) }
        return "added \"$text\""
    }
    fun removeTaskByName(name: String): String {
        val before = _state.value.tasks.size
        update { it.copy(tasks = it.tasks.filterNot { t -> t.text.equals(name, ignoreCase = true) }) }
        return if (_state.value.tasks.size < before) "removed \"$name\"" else "no task matching \"$name\""
    }
    fun removeTaskById(id: String) = update { it.copy(tasks = it.tasks.filterNot { t -> t.id == id }) }

    // ---- timers ----
    fun setTimer(args: String): String {
        val parts = args.split(":")
        if (parts.isEmpty() || parts[0].isBlank()) return "need a duration"
        val num = parts[0].toDoubleOrNull() ?: return "need a numeric duration"
        val unit = (parts.getOrNull(1) ?: "seconds").lowercase()
        val seconds = when {
            unit.startsWith("min") -> num * 60
            unit.startsWith("hour") -> num * 3600
            else -> num
        }
        val label = "Timer ${_state.value.timers.size + 1}"
        val timer = TimerItem(UUID.randomUUID().toString(), label, System.currentTimeMillis() + (seconds * 1000).toLong())
        AlarmScheduler.scheduleTimer(getApplication(), timer)
        update { it.copy(timers = it.timers + timer) }
        return "$label set for ${seconds.toInt()}s"
    }
    fun cancelTimer(args: String): String {
        val timers = _state.value.timers
        val timer = args.toIntOrNull()?.let { idx -> timers.getOrNull(idx) }
            ?: timers.firstOrNull { it.label.contains(args, ignoreCase = true) }
            ?: return "no matching timer"
        AlarmScheduler.cancelTimer(getApplication(), timer)
        update { it.copy(timers = it.timers.filterNot { t -> t.id == timer.id }) }
        return "cancelled ${timer.label}"
    }
    fun cancelTimerById(id: String) {
        val timer = _state.value.timers.firstOrNull { it.id == id } ?: return
        AlarmScheduler.cancelTimer(getApplication(), timer)
        update { it.copy(timers = it.timers.filterNot { t -> t.id == id }) }
    }
    fun checkTimers(): String {
        val timers = _state.value.timers
        if (timers.isEmpty()) return "no active timers"
        val now = System.currentTimeMillis()
        return timers.joinToString("; ") { "${it.label} — ${((it.endTs - now) / 1000).coerceAtLeast(0)}s left" }
    }

    // ---- scheduled tasks ----
    fun scheduleTask(args: String): String {
        val parts = args.split(":")
        val cmd = parts.getOrNull(0) ?: return "need a command to schedule"
        val runTs: Long = when {
            parts.getOrNull(1) == "in" -> {
                val num = parts.getOrNull(2)?.toDoubleOrNull() ?: return "need a duration to schedule"
                val unit = (parts.getOrNull(3) ?: "minutes").lowercase()
                val ms = when {
                    unit.startsWith("sec") -> num * 1000
                    unit.startsWith("hour") -> num * 3600000
                    else -> num * 60000
                }
                System.currentTimeMillis() + ms.toLong()
            }
            parts.getOrNull(1)?.toIntOrNull() != null -> {
                val h = parts[1].toInt()
                val mi = parts.getOrNull(2)?.toIntOrNull() ?: 0
                val cal = java.util.Calendar.getInstance()
                cal.set(java.util.Calendar.HOUR_OF_DAY, h)
                cal.set(java.util.Calendar.MINUTE, mi)
                cal.set(java.util.Calendar.SECOND, 0)
                if (cal.timeInMillis < System.currentTimeMillis()) cal.add(java.util.Calendar.DAY_OF_MONTH, 1)
                cal.timeInMillis
            }
            else -> return "could not parse schedule — use SCHEDULE_TASK:cmd:in:N:unit or SCHEDULE_TASK:cmd:HH:MM"
        }
        val item = ScheduledItem(UUID.randomUUID().toString(), cmd, runTs)
        AlarmScheduler.scheduleTask(getApplication(), item)
        update { it.copy(scheduled = it.scheduled + item) }
        return "scheduled \"$cmd\" for ${android.text.format.DateFormat.format("h:mm a", runTs)}"
    }
    fun cancelScheduled(args: String): String {
        val idx = args.toIntOrNull() ?: return "need an index — see LIST_SCHEDULED"
        val item = _state.value.scheduled.getOrNull(idx) ?: return "no such scheduled task"
        AlarmScheduler.cancelTask(getApplication(), item)
        update { it.copy(scheduled = it.scheduled.filterNot { s -> s.id == item.id }) }
        return "cancelled scheduled task $idx"
    }
    fun cancelScheduledById(id: String) {
        val item = _state.value.scheduled.firstOrNull { it.id == id } ?: return
        AlarmScheduler.cancelTask(getApplication(), item)
        update { it.copy(scheduled = it.scheduled.filterNot { s -> s.id == id }) }
    }
    fun listScheduled(): String {
        val s = _state.value.scheduled
        if (s.isEmpty()) return "nothing scheduled"
        return s.mapIndexed { i, item -> "$i: ${item.cmd} @ ${android.text.format.DateFormat.format("h:mm a", item.runTs)}" }.joinToString("; ")
    }

    // ---- facts ----
    fun saveFact(text: String): String {
        if (text.isBlank()) return "need something to remember"
        update { it.copy(facts = it.facts + FactItem(UUID.randomUUID().toString(), text)) }
        return "saved: \"$text\""
    }
    fun listFacts(): String {
        val f = _state.value.facts
        return if (f.isEmpty()) "no facts saved yet" else f.joinToString("; ") { it.text }
    }
    fun removeFact(id: String) = update { it.copy(facts = it.facts.filterNot { f -> f.id == id }) }

    // ---- macros ----
    fun macroRecordStart(name: String): String {
        val n = name.ifBlank { "macro${_state.value.macros.size + 1}" }
        update { it.copy(macros = it.macros + (n to emptyList()), macroRecording = n) }
        return "recording macro \"$n\""
    }
    fun macroRecordStop(): String {
        val name = _state.value.macroRecording
        update { it.copy(macroRecording = null) }
        return if (name != null) "macro \"$name\" saved (${_state.value.macros[name]?.size ?: 0} steps)" else "no recording in progress"
    }
    fun macroRecordStep(name: String, args: String) {
        val recording = _state.value.macroRecording ?: return
        update {
            val steps = (it.macros[recording] ?: emptyList()) + MacroStep(name, args)
            it.copy(macros = it.macros + (recording to steps))
        }
    }
    fun macroList(): String {
        val m = _state.value.macros
        return if (m.isEmpty()) "no macros recorded" else m.entries.joinToString(", ") { "${it.key} (${it.value.size} steps)" }
    }
    fun macroDelete(name: String): String {
        update { it.copy(macros = it.macros - name) }
        return "deleted macro \"$name\""
    }
    fun macroSteps(name: String): List<MacroStep> = _state.value.macros[name] ?: emptyList()

    // ---- virtual windows ----
    fun openWindow(name: String) = update {
        val existing = it.windows.firstOrNull { w -> w.name.equals(name, true) }
        if (existing != null) {
            it.copy(windows = it.windows.filterNot { w -> w == existing } + existing.copy(state = "open"))
        } else {
            it.copy(windows = it.windows + VirtualWindow(name, "open"))
        }
    }
    fun setWindowState(name: String, targetState: String): Boolean {
        val exists = _state.value.windows.any { it.name.equals(name, true) }
        if (exists) update {
            it.copy(windows = it.windows.map { w -> if (w.name.equals(name, true)) w.copy(state = targetState) else w })
        }
        return exists
    }
    fun closeWindow(name: String): Boolean {
        val exists = _state.value.windows.any { it.name.equals(name, true) }
        update { it.copy(windows = it.windows.filterNot { w -> w.name.equals(name, true) }) }
        return exists
    }

    // ---- volume / brightness ----
    fun setVolumePref(v: Int) = update { it.copy(volume = v.coerceIn(0, 100)) }
    fun setBrightnessPref(v: Int) = update { it.copy(brightness = v.coerceIn(0, 100)) }

    // ---- reset ----
    fun resetState() = update {
        it.timers.forEach { t -> AlarmScheduler.cancelTimer(getApplication(), t) }
        it.scheduled.forEach { s -> AlarmScheduler.cancelTask(getApplication(), s) }
        it.copy(tasks = emptyList(), timers = emptyList(), scheduled = emptyList())
    }

    // ---- chat orchestration ----
    fun sendUserMessage(text: String, onAssistantReply: suspend (String) -> Unit) {
        addChat("user", text)
        viewModelScope.launch {
            _thinking.value = true
            val prompt = SystemPrompt.build(_state.value.facts)
            val reply = GeminiClient.send(_state.value.apiKey, prompt, _state.value.chat)
            addChat("assistant", reply)
            _thinking.value = false
            onAssistantReply(reply)
        }
    }
}
