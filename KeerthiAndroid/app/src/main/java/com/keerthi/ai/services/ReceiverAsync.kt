package com.keerthi.ai.services

import android.content.BroadcastReceiver
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * Runs [block] on a background dispatcher while holding this receiver's `goAsync()`
 * result, so Android doesn't tear down the process before the work finishes —
 * `onReceive()` returning is otherwise a signal that the receiver is done.
 */
fun BroadcastReceiver.goAsyncIO(block: suspend () -> Unit) {
    val pending = goAsync()
    CoroutineScope(Dispatchers.IO).launch {
        try {
            block()
        } finally {
            pending.finish()
        }
    }
}
