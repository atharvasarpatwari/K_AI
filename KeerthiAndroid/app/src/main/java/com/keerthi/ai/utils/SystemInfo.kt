package com.keerthi.ai.utils

import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.StatFs
import android.os.Environment

object SystemInfo {

    fun memoryPercent(context: Context): Int {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val info = ActivityManager.MemoryInfo()
        am.getMemoryInfo(info)
        if (info.totalMem == 0L) return 0
        val usedRatio = 1.0 - (info.availMem.toDouble() / info.totalMem.toDouble())
        return (usedRatio * 100).toInt().coerceIn(0, 100)
    }

    fun memorySummary(context: Context): String {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val info = ActivityManager.MemoryInfo()
        am.getMemoryInfo(info)
        val usedGb = (info.totalMem - info.availMem) / 1e9
        val totalGb = info.totalMem / 1e9
        return String.format("%.1f GB / %.1f GB (%d%%)", usedGb, totalGb, memoryPercent(context))
    }

    fun diskPercent(): Int {
        val stat = StatFs(Environment.getDataDirectory().path)
        val total = stat.blockCountLong * stat.blockSizeLong
        val free = stat.availableBlocksLong * stat.blockSizeLong
        if (total == 0L) return 0
        return (((total - free).toDouble() / total.toDouble()) * 100).toInt().coerceIn(0, 100)
    }

    fun diskSummary(): String {
        val stat = StatFs(Environment.getDataDirectory().path)
        val total = stat.blockCountLong * stat.blockSizeLong
        val free = stat.availableBlocksLong * stat.blockSizeLong
        val usedGb = (total - free) / 1e9
        val totalGb = total / 1e9
        return String.format("%.1f GB / %.1f GB (%d%%)", usedGb, totalGb, diskPercent())
    }

    fun batteryPercentAndCharging(context: Context): Pair<Int, Boolean> {
        val filter = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
        val batteryStatus = context.registerReceiver(null, filter)
        val level = batteryStatus?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
        val scale = batteryStatus?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
        val pct = if (level >= 0 && scale > 0) (level * 100 / scale) else 0
        val status = batteryStatus?.getIntExtra(BatteryManager.EXTRA_STATUS, -1) ?: -1
        val charging = status == BatteryManager.BATTERY_STATUS_CHARGING ||
                status == BatteryManager.BATTERY_STATUS_FULL
        return Pair(pct, charging)
    }

    fun batterySummary(context: Context): String {
        val (pct, charging) = batteryPercentAndCharging(context)
        return "$pct%" + if (charging) " (charging)" else " (on battery)"
    }
}
