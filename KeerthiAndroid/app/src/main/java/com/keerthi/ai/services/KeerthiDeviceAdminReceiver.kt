package com.keerthi.ai.services

import android.app.admin.DeviceAdminReceiver

/**
 * Registered as a Device Admin only so LOCK_SCREEN can call
 * DevicePolicyManager.lockNow() for a real, immediate screen lock.
 * The user must explicitly enable this under Settings > Security > Device admin apps.
 */
class KeerthiDeviceAdminReceiver : DeviceAdminReceiver()
