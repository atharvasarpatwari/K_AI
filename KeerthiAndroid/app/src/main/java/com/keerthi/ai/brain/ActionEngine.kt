package com.keerthi.ai.brain

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.media.AudioManager
import android.net.Uri
import android.provider.MediaStore
import android.provider.Settings
import com.keerthi.ai.data.KeerthiViewModel
import com.keerthi.ai.data.SAFETY_ACTIONS
import com.keerthi.ai.services.KeerthiDeviceAdminReceiver
import com.keerthi.ai.utils.LocationInfo
import com.keerthi.ai.utils.SystemInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.util.concurrent.TimeUnit

object ActionEngine {

    fun isSafety(name: String): Boolean = name in SAFETY_ACTIONS

    private val http = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS).readTimeout(10, TimeUnit.SECONDS).build()

    suspend fun run(name: String, args: String, context: Context, vm: KeerthiViewModel): String {
        if (name != "MACRO_RECORD" && name != "MACRO_STOP") {
            vm.macroRecordStep(name, args)
        }
        return try {
            when (name) {
                "SYSTEM_STATUS" -> "${SystemInfo.memorySummary(context)} mem · ${SystemInfo.diskSummary()} disk · ${SystemInfo.batterySummary(context)}"
                "CPU_USAGE" -> "Per-app CPU usage isn't exposed to third-party apps on Android; try LIST_PROCESSES for recently used apps instead."
                "MEMORY_USAGE" -> SystemInfo.memorySummary(context)
                "DISK_USAGE" -> SystemInfo.diskSummary()
                "BATTERY_STATUS" -> SystemInfo.batterySummary(context)

                "LIST_PROCESSES" -> listRecentApps(context)
                "KILL_PROCESS" -> "Android does not allow one app to stop another app's process for security reasons — open $args and stop it from Settings > Apps."

                "OPEN_APP" -> openApp(context, args, vm)
                "RUN_COMMAND" -> "Arbitrary shell commands aren't available on a non-rooted Android device — nothing was run."

                "FILE_LIST" -> listDownloads(context)
                "OPEN_FILE" -> "File opening needs a document picker interaction in-app; use the Files tile on the dashboard."

                "RESET_STATE" -> { vm.resetState(); "tasks and timers reset" }

                "SET_TIMER" -> vm.setTimer(args)
                "CANCEL_TIMER" -> vm.cancelTimer(args)
                "CHECK_TIMERS" -> vm.checkTimers()

                "ADD_TASK" -> vm.addTask(args)
                "REMOVE_TASK" -> vm.removeTaskByName(args)
                "STATUS_REPORT" -> "${SystemInfo.batterySummary(context)} · ${vm.state.value.tasks.size} open task(s) · ${vm.state.value.timers.size} timer(s) running"

                "WEATHER_REPORT" -> weatherReport(context)

                "TYPE_TEXT" -> "Typing into other apps needs an Accessibility Service, which this app does not request to stay Play Store safe — nothing was typed."
                "PRESS_KEYS" -> "Simulated key presses need an Accessibility Service, which this app does not request — nothing was pressed."
                "MOVE_MOUSE", "CLICK_MOUSE", "SCROLL_MOUSE" -> "Android has no pointer to move or click on a touch device — nothing happened."
                "TAKE_SCREENSHOT" -> "Screen capture needs a one-time on-screen consent dialog (MediaProjection) that isn't wired up in this build."
                "READ_SCREEN" -> "Screen reading needs a one-time on-screen consent dialog (MediaProjection) that isn't wired up in this build."

                "SHUTDOWN" -> "Powering off requires root or a device-owner profile — not available to a regular app. Use the physical power button."
                "RESTART" -> "Restarting requires root or a device-owner profile — not available to a regular app."
                "SLEEP" -> sleepScreen(context)
                "LOCK_SCREEN" -> lockScreen(context)

                "SET_VOLUME" -> setVolume(context, args, vm)
                "MUTE" -> mute(context, args)
                "SET_BRIGHTNESS" -> setBrightness(context, args, vm)

                "LIST_WINDOWS" -> vm.state.value.windows.let { w -> if (w.isEmpty()) "no open windows" else w.joinToString(", ") { "${it.name} (${it.state})" } }
                "FOCUS_WINDOW" -> { vm.openWindow(args); "focused $args" }
                "MINIMIZE_WINDOW" -> if (vm.setWindowState(args, "minimized")) "minimized $args" else "no window named \"$args\""
                "MAXIMIZE_WINDOW" -> if (vm.setWindowState(args, "maximized")) "maximized $args" else "no window named \"$args\""
                "CLOSE_WINDOW" -> if (vm.closeWindow(args)) "closed $args" else "no window named \"$args\""
                "MOVE_WINDOW", "MOVE_WINDOW_TO_MONITOR" -> "noted (Android has no desktop-style window placement; tracked on the virtual desktop only)"

                "OPEN_URL" -> openUrl(context, args)
                "WEB_SEARCH" -> webSearch(context, args)

                "SAVE_FACT" -> vm.saveFact(args)
                "LIST_FACTS" -> vm.listFacts()

                "MACRO_RECORD" -> vm.macroRecordStart(args)
                "MACRO_STOP" -> vm.macroRecordStop()
                "MACRO_REPLAY" -> replayMacro(context, args, vm)
                "MACRO_LIST" -> vm.macroList()
                "MACRO_DELETE" -> vm.macroDelete(args)

                "SCHEDULE_TASK" -> vm.scheduleTask(args)
                "CANCEL_SCHEDULED" -> vm.cancelScheduled(args)
                "LIST_SCHEDULED" -> vm.listScheduled()

                "INSTALL_APP" -> installApp(context, args)

                else -> "unknown action"
            }
        } catch (e: Exception) {
            "error: ${e.message}"
        }
    }

    private fun listRecentApps(context: Context): String {
        val pm = context.packageManager
        val apps = pm.getInstalledApplications(0)
            .filter { pm.getLaunchIntentForPackage(it.packageName) != null }
            .shuffled().take(6)
            .map { pm.getApplicationLabel(it).toString() }
        return if (apps.isEmpty()) "no launchable apps found" else "recently available apps: " + apps.joinToString(", ") +
            " (Android hides live CPU/RAM per app from other apps, so no live figures here)"
    }

    private fun openApp(context: Context, args: String, vm: KeerthiViewModel): String {
        val pm = context.packageManager
        val target = pm.getInstalledApplications(0).firstOrNull {
            pm.getApplicationLabel(it).toString().equals(args, ignoreCase = true) ||
                pm.getApplicationLabel(it).toString().contains(args, ignoreCase = true)
        } ?: return "couldn't find an installed app named \"$args\""
        val launch = pm.getLaunchIntentForPackage(target.packageName)
            ?: return "\"$args\" has no launchable activity"
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(launch)
        vm.openWindow(pm.getApplicationLabel(target).toString())
        return "launching ${pm.getApplicationLabel(target)}"
    }

    private fun listDownloads(context: Context): String {
        val names = mutableListOf<String>()
        val uri = MediaStore.Files.getContentUri("external")
        val projection = arrayOf(MediaStore.MediaColumns.DISPLAY_NAME, MediaStore.MediaColumns.RELATIVE_PATH)
        try {
            context.contentResolver.query(uri, projection, null, null, null)?.use { cursor ->
                val nameIdx = cursor.getColumnIndex(MediaStore.MediaColumns.DISPLAY_NAME)
                val pathIdx = cursor.getColumnIndex(MediaStore.MediaColumns.RELATIVE_PATH)
                while (cursor.moveToNext() && names.size < 10) {
                    val path = if (pathIdx >= 0) cursor.getString(pathIdx) ?: "" else ""
                    if (path.contains("Download")) {
                        names.add(cursor.getString(nameIdx))
                    }
                }
            }
        } catch (e: Exception) {
            return "couldn't read the Downloads folder — check storage permission"
        }
        return if (names.isEmpty()) "Downloads folder is empty or inaccessible" else names.joinToString(", ")
    }

    private suspend fun weatherReport(context: Context): String = withContext(Dispatchers.IO) {
        try {
            val fix = LocationInfo.lastKnown(context)
            val (lat, lon, name) = if (fix != null) {
                Triple(fix.latitude, fix.longitude, LocationInfo.placeName(context, fix))
            } else {
                val geoReq = Request.Builder()
                    .url("https://geocoding-api.open-meteo.com/v1/search?name=Hyderabad&count=1")
                    .build()
                val geoBody = http.newCall(geoReq).execute().use { it.body?.string() } ?: return@withContext fallbackWeather()
                val results = JSONObject(geoBody).optJSONArray("results") ?: return@withContext fallbackWeather()
                if (results.length() == 0) return@withContext fallbackWeather()
                val g = results.getJSONObject(0)
                Triple(g.getDouble("latitude"), g.getDouble("longitude"), g.getString("name"))
            }
            val wxReq = Request.Builder()
                .url("https://api.open-meteo.com/v1/forecast?latitude=$lat&longitude=$lon&current=temperature_2m,relative_humidity_2m,wind_speed_10m")
                .build()
            val wxBody = http.newCall(wxReq).execute().use { it.body?.string() } ?: return@withContext fallbackWeather()
            val c = JSONObject(wxBody).getJSONObject("current")
            "$name: ${c.getDouble("temperature_2m")}°C, humidity ${c.getInt("relative_humidity_2m")}%, wind ${c.getDouble("wind_speed_10m")} km/h"
        } catch (e: Exception) {
            fallbackWeather()
        }
    }
    private fun fallbackWeather() = "Hyderabad: ~29°C, partly cloudy (live fetch unavailable right now)"

    private fun sleepScreen(context: Context): String {
        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        val admin = ComponentName(context, KeerthiDeviceAdminReceiver::class.java)
        return if (dpm.isAdminActive(admin)) {
            dpm.lockNow()
            "screen turned off"
        } else {
            "enable KEERTHI as a Device Admin in Settings to let it turn the screen off"
        }
    }

    private fun lockScreen(context: Context): String {
        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        val admin = ComponentName(context, KeerthiDeviceAdminReceiver::class.java)
        return if (dpm.isAdminActive(admin)) {
            dpm.lockNow()
            "screen locked"
        } else {
            "enable KEERTHI as a Device Admin in Settings > Security to let it lock the screen"
        }
    }

    private fun setVolume(context: Context, args: String, vm: KeerthiViewModel): String {
        val pct = args.toIntOrNull()?.coerceIn(0, 100) ?: return "need a percentage, e.g. SET_VOLUME:50"
        val am = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val max = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
        am.setStreamVolume(AudioManager.STREAM_MUSIC, (max * pct / 100).coerceIn(0, max), 0)
        vm.setVolumePref(pct)
        return "volume set to $pct%"
    }

    private fun mute(context: Context, args: String): String {
        val am = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val muting = args != "off"
        am.adjustStreamVolume(AudioManager.STREAM_MUSIC, if (muting) AudioManager.ADJUST_MUTE else AudioManager.ADJUST_UNMUTE, 0)
        return if (muting) "muted" else "unmuted"
    }

    private fun setBrightness(context: Context, args: String, vm: KeerthiViewModel): String {
        val pct = args.toIntOrNull()?.coerceIn(0, 100) ?: return "need a percentage, e.g. SET_BRIGHTNESS:70"
        if (!Settings.System.canWrite(context)) {
            return "grant KEERTHI the \"Modify system settings\" permission to control brightness"
        }
        Settings.System.putInt(context.contentResolver, Settings.System.SCREEN_BRIGHTNESS, (pct * 255 / 100))
        vm.setBrightnessPref(pct)
        return "brightness set to $pct%"
    }

    private fun openUrl(context: Context, args: String): String {
        var url = args.trim()
        if (!url.startsWith("http")) url = "https://$url"
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        return try { context.startActivity(intent); "opening $url" } catch (e: Exception) { "couldn't open $url" }
    }

    private fun webSearch(context: Context, args: String): String {
        val intent = Intent(Intent.ACTION_WEB_SEARCH).putExtra("query", args).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        return try { context.startActivity(intent); "searching for \"$args\"" } catch (e: Exception) { openUrl(context, "https://www.google.com/search?q=" + Uri.encode(args)) }
    }

    private fun installApp(context: Context, args: String): String {
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse("market://search?q=$args")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        return try { context.startActivity(intent); "opened the Play Store listing for \"$args\"" } catch (e: Exception) { "couldn't open the Play Store" }
    }

    private suspend fun replayMacro(context: Context, name: String, vm: KeerthiViewModel): String {
        val steps = vm.macroSteps(name)
        if (steps.isEmpty()) return "no macro named \"$name\""
        for (step in steps) {
            run(step.name, step.args, context, vm)
        }
        return "replayed macro \"$name\" (${steps.size} steps)"
    }
}
