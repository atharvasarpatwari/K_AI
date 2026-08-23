package com.keerthi.ai.services

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class TimerReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val label = intent.getStringExtra("label") ?: "Timer"
        val id = intent.getIntExtra("notifId", 1)
        NotificationHelper.notify(context, id, "⏰ $label", "Your timer is done.")
    }
}
