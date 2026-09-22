package com.keerthi.ai.brain

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import com.keerthi.ai.data.ScheduledItem
import com.keerthi.ai.data.TimerItem
import com.keerthi.ai.services.ScheduledTaskReceiver
import com.keerthi.ai.services.TimerReceiver

object AlarmScheduler {

    private fun alarmManager(context: Context) =
        context.getSystemService(Context.ALARM_SERVICE) as AlarmManager

    fun scheduleTimer(context: Context, timer: TimerItem) {
        val intent = Intent(context, TimerReceiver::class.java).apply {
            putExtra("id", timer.id)
            putExtra("label", timer.label)
            putExtra("notifId", timer.id.hashCode())
        }
        val pi = PendingIntent.getBroadcast(
            context, timer.id.hashCode(), intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        setExact(context, timer.endTs, pi)
    }

    fun cancelTimer(context: Context, timer: TimerItem) {
        val intent = Intent(context, TimerReceiver::class.java)
        val pi = PendingIntent.getBroadcast(
            context, timer.id.hashCode(), intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        alarmManager(context).cancel(pi)
    }

    fun scheduleTask(context: Context, item: ScheduledItem) {
        val intent = Intent(context, ScheduledTaskReceiver::class.java).apply {
            putExtra("id", item.id)
            putExtra("cmd", item.cmd)
            putExtra("notifId", item.id.hashCode())
        }
        val pi = PendingIntent.getBroadcast(
            context, item.id.hashCode(), intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        setExact(context, item.runTs, pi)
    }

    fun cancelTask(context: Context, item: ScheduledItem) {
        val intent = Intent(context, ScheduledTaskReceiver::class.java)
        val pi = PendingIntent.getBroadcast(
            context, item.id.hashCode(), intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        alarmManager(context).cancel(pi)
    }

    private fun setExact(context: Context, atMillis: Long, pi: PendingIntent) {
        val am = alarmManager(context)
        try {
            am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, atMillis, pi)
        } catch (e: SecurityException) {
            // SCHEDULE_EXACT_ALARM not granted on this OS version — fall back to inexact
            am.set(AlarmManager.RTC_WAKEUP, atMillis, pi)
        }
    }
}
