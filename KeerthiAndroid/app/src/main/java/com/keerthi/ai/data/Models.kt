package com.keerthi.ai.data

import kotlinx.serialization.Serializable

@Serializable
data class ChatMessage(
    val role: String,      // "user" | "assistant" | "system"
    val text: String,
    val ts: Long = System.currentTimeMillis()
)

@Serializable
data class TaskItem(
    val id: String,
    val text: String
)

@Serializable
data class TimerItem(
    val id: String,
    val label: String,
    val endTs: Long
)

@Serializable
data class ScheduledItem(
    val id: String,
    val cmd: String,
    val runTs: Long
)

@Serializable
data class FactItem(
    val id: String,
    val text: String
)

@Serializable
data class MacroStep(
    val name: String,
    val args: String
)

@Serializable
data class VirtualWindow(
    val name: String,
    val state: String = "open" // open | minimized | maximized
)

@Serializable
data class KeerthiState(
    val apiKey: String = "",
    val chat: List<ChatMessage> = emptyList(),
    val tasks: List<TaskItem> = emptyList(),
    val timers: List<TimerItem> = emptyList(),
    val scheduled: List<ScheduledItem> = emptyList(),
    val facts: List<FactItem> = emptyList(),
    val macros: Map<String, List<MacroStep>> = emptyMap(),
    val windows: List<VirtualWindow> = emptyList(),
    val macroRecording: String? = null,
    val volume: Int = 60,
    val brightness: Int = 70,
    val voiceOutEnabled: Boolean = true
)

data class ActionSpec(
    val name: String,
    val description: String,
    val safety: Boolean = false
)

val ACTION_LIBRARY: List<ActionSpec> = listOf(
    ActionSpec("SYSTEM_STATUS", "Report memory, disk and battery usage at a glance."),
    ActionSpec("CPU_USAGE", "Report the current CPU usage percentage."),
    ActionSpec("MEMORY_USAGE", "Report memory usage (used / total)."),
    ActionSpec("DISK_USAGE", "Report disk usage (used / total)."),
    ActionSpec("BATTERY_STATUS", "Report battery level and whether it is charging."),
    ActionSpec("LIST_PROCESSES", "List recently used apps."),
    ActionSpec("KILL_PROCESS", "Force-stop a background app by name.", safety = true),
    ActionSpec("OPEN_APP", "Launch an installed app by name (e.g. OPEN_APP:Camera)."),
    ActionSpec("RUN_COMMAND", "Run a shell command.", safety = true),
    ActionSpec("FILE_LIST", "List files in the Downloads folder."),
    ActionSpec("OPEN_FILE", "Open a file with its default app."),
    ActionSpec("RESET_STATE", "Clear saved tasks and timers back to defaults."),
    ActionSpec("SET_TIMER", "Set a timer (e.g. SET_TIMER:90 or SET_TIMER:3:minutes)."),
    ActionSpec("CANCEL_TIMER", "Cancel a timer by label or index."),
    ActionSpec("CHECK_TIMERS", "Report all pending timers."),
    ActionSpec("ADD_TASK", "Add a task to the list."),
    ActionSpec("REMOVE_TASK", "Remove a task by name.", safety = true),
    ActionSpec("STATUS_REPORT", "Report the current status and task list."),
    ActionSpec("WEATHER_REPORT", "Report the current weather for the user's location."),
    ActionSpec("TYPE_TEXT", "Type text into the focused field.", safety = true),
    ActionSpec("PRESS_KEYS", "Press a key combination.", safety = true),
    ActionSpec("MOVE_MOUSE", "Move the pointer to coordinates.", safety = true),
    ActionSpec("CLICK_MOUSE", "Click at the pointer position.", safety = true),
    ActionSpec("SCROLL_MOUSE", "Scroll the screen.", safety = true),
    ActionSpec("TAKE_SCREENSHOT", "Capture the screen."),
    ActionSpec("READ_SCREEN", "Describe what is on screen."),
    ActionSpec("SHUTDOWN", "Power off the device.", safety = true),
    ActionSpec("RESTART", "Restart the device.", safety = true),
    ActionSpec("SLEEP", "Turn the screen off.", safety = true),
    ActionSpec("LOCK_SCREEN", "Lock the device screen.", safety = true),
    ActionSpec("SET_VOLUME", "Set the media volume to a percentage."),
    ActionSpec("MUTE", "Mute or unmute the volume."),
    ActionSpec("SET_BRIGHTNESS", "Set the screen brightness to a percentage."),
    ActionSpec("LIST_WINDOWS", "List open app windows on the virtual desktop."),
    ActionSpec("FOCUS_WINDOW", "Bring a window to the front."),
    ActionSpec("MINIMIZE_WINDOW", "Minimize a window."),
    ActionSpec("MAXIMIZE_WINDOW", "Maximize a window."),
    ActionSpec("CLOSE_WINDOW", "Close a window.", safety = true),
    ActionSpec("OPEN_URL", "Open a URL in the default browser."),
    ActionSpec("WEB_SEARCH", "Search the web."),
    ActionSpec("SAVE_FACT", "Save a user fact to long-term memory."),
    ActionSpec("LIST_FACTS", "List facts saved about the user."),
    ActionSpec("MACRO_RECORD", "Start recording a macro of subsequent actions."),
    ActionSpec("MACRO_STOP", "Stop the active macro recording and save it."),
    ActionSpec("MACRO_REPLAY", "Replay a recorded macro.", safety = true),
    ActionSpec("MACRO_LIST", "List recorded macros."),
    ActionSpec("MACRO_DELETE", "Delete a recorded macro."),
    ActionSpec("SCHEDULE_TASK", "Schedule a command to run later.", safety = true),
    ActionSpec("CANCEL_SCHEDULED", "Cancel a scheduled task by index."),
    ActionSpec("LIST_SCHEDULED", "Report all scheduled tasks."),
    ActionSpec("INSTALL_APP", "Open the Play Store listing for an app.", safety = true),
    ActionSpec("MOVE_WINDOW", "Move a window on the virtual desktop."),
    ActionSpec("MOVE_WINDOW_TO_MONITOR", "Move a window to another monitor.")
)

val SAFETY_ACTIONS: Set<String> = ACTION_LIBRARY.filter { it.safety }.map { it.name }.toSet()
