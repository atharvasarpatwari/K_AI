package com.keerthi.ai.services

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.keerthi.ai.data.PrefsStore

class TimerReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val label = intent.getStringExtra("label") ?: "Timer"
        val notifId = intent.getIntExtra("notifId", 1)
        val timerId = intent.getStringExtra("id")
        NotificationHelper.notify(context, notifId, "⏰ $label", "Your timer is done.")

        val appContext = context.applicationContext
        goAsyncIO {
            // ponytail: if the app is foregrounded at this exact instant, the ViewModel's
            // in-memory state won't see this removal until it reloads — fix is observing
            // DataStore as a Flow instead of KeerthiViewModel's one-shot load().
            if (timerId != null) {
                val state = PrefsStore.load(appContext)
                PrefsStore.save(appContext, state.copy(timers = state.timers.filterNot { it.id == timerId }))
            }
        }
    }
}
