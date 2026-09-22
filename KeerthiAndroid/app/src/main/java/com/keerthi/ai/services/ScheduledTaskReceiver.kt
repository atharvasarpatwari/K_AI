package com.keerthi.ai.services

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.keerthi.ai.data.PrefsStore

class ScheduledTaskReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val cmd = intent.getStringExtra("cmd") ?: "scheduled task"
        val notifId = intent.getIntExtra("notifId", 2)
        val itemId = intent.getStringExtra("id")
        NotificationHelper.notify(context, notifId, "📅 KEERTHI reminder", cmd)

        val appContext = context.applicationContext
        goAsyncIO {
            // ponytail: same foreground-race ceiling as TimerReceiver — see its comment.
            if (itemId != null) {
                val state = PrefsStore.load(appContext)
                PrefsStore.save(appContext, state.copy(scheduled = state.scheduled.filterNot { it.id == itemId }))
            }
        }
    }
}
