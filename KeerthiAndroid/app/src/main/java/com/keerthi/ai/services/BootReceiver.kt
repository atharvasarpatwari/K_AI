package com.keerthi.ai.services

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.keerthi.ai.brain.AlarmScheduler
import com.keerthi.ai.data.PrefsStore

/**
 * Re-arms any still-pending timers and scheduled tasks after a device reboot,
 * since AlarmManager alarms do not survive a restart on their own.
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        val appContext = context.applicationContext
        goAsyncIO {
            val state = PrefsStore.load(appContext)
            val now = System.currentTimeMillis()
            state.timers.filter { it.endTs > now }.forEach {
                AlarmScheduler.scheduleTimer(appContext, it)
            }
            state.scheduled.filter { it.runTs > now }.forEach {
                AlarmScheduler.scheduleTask(appContext, it)
            }
        }
    }
}
