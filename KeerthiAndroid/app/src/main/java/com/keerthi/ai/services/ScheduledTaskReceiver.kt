package com.keerthi.ai.services

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class ScheduledTaskReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val cmd = intent.getStringExtra("cmd") ?: "scheduled task"
        val id = intent.getIntExtra("notifId", 2)
        NotificationHelper.notify(context, id, "📅 KEERTHI reminder", cmd)
    }
}
