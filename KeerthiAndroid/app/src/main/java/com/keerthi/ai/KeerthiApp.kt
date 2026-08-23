package com.keerthi.ai

import android.app.Application
import com.keerthi.ai.services.NotificationHelper

class KeerthiApp : Application() {
    override fun onCreate() {
        super.onCreate()
        NotificationHelper.ensureChannel(this)
    }
}
