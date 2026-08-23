package com.keerthi.ai.ui

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.keerthi.ai.data.KeerthiViewModel
import com.keerthi.ai.ui.theme.*

@Composable
fun SettingsScreen(vm: KeerthiViewModel) {
    val context = LocalContext.current
    val state by vm.state.collectAsState()
    var key by remember(state.apiKey) { mutableStateOf(state.apiKey) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Bg)
            .verticalScroll(rememberScrollState())
            .padding(20.dp)
    ) {
        Text("Settings", color = TextPrimary, fontSize = 20.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(18.dp))

        SettingsCard(title = "Gemini API key") {
            Text(
                "KEERTHI's chat brain calls the Gemini API directly from this device. Get a free key at aistudio.google.com/apikey and paste it below — it's stored only on this device.",
                color = TextSub, fontSize = 12.sp
            )
            Spacer(Modifier.height(10.dp))
            OutlinedTextField(
                value = key,
                onValueChange = { key = it },
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("AIza…", color = TextDim) },
                singleLine = true,
                shape = RoundedCornerShape(10.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = SignalDim, unfocusedBorderColor = LineColor,
                    focusedTextColor = TextPrimary, unfocusedTextColor = TextPrimary, cursorColor = Signal
                )
            )
            Spacer(Modifier.height(10.dp))
            Button(
                onClick = { vm.setApiKey(key.trim()) },
                colors = ButtonDefaults.buttonColors(containerColor = Signal, contentColor = androidx.compose.ui.graphics.Color(0xFF06130D))
            ) { Text("Save key", fontWeight = FontWeight.Bold) }
        }

        Spacer(Modifier.height(16.dp))

        SettingsCard(title = "Device permissions") {
            Text(
                "A few real actions need one-time permissions from Android itself:",
                color = TextSub, fontSize = 12.sp
            )
            Spacer(Modifier.height(10.dp))
            PermRow("Modify system settings", "needed for SET_BRIGHTNESS") {
                context.startActivity(Intent(Settings.ACTION_MANAGE_WRITE_SETTINGS, Uri.parse("package:" + context.packageName)))
            }
            PermRow("Device admin", "needed for LOCK_SCREEN / SLEEP") {
                val intent = Intent(android.app.admin.DevicePolicyManager.ACTION_ADD_DEVICE_ADMIN)
                intent.putExtra(
                    android.app.admin.DevicePolicyManager.EXTRA_DEVICE_ADMIN,
                    android.content.ComponentName(context, com.keerthi.ai.services.KeerthiDeviceAdminReceiver::class.java)
                )
                intent.putExtra(android.app.admin.DevicePolicyManager.EXTRA_ADD_EXPLANATION, "Lets KEERTHI lock or wake the screen on request.")
                context.startActivity(intent)
            }
            PermRow("Notifications", "needed for timer / reminder alerts") {
                val intent = Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                intent.putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName)
                context.startActivity(intent)
            }
            PermRow("Exact alarms", "needed for precise timers on Android 12+") {
                val intent = Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM)
                context.startActivity(intent)
            }
        }

        Spacer(Modifier.height(16.dp))

        SettingsCard(title = "What's real vs. simulated") {
            listOf(
                "Real" to "chat brain, timers, tasks, scheduled reminders, memory facts, macros, opening apps/URLs, volume, brightness, screen lock, weather, notifications, voice in/out",
                "Not possible on stock Android" to "killing other apps' processes, arbitrary shell commands, simulated key/mouse input, silent shutdown/restart/app install — the app is honest about these instead of faking them"
            ).forEach { (k, v) ->
                Text(k, color = Signal, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                Text(v, color = TextSub, fontSize = 12.sp, modifier = Modifier.padding(bottom = 10.dp, top = 2.dp))
            }
        }

        Spacer(Modifier.height(30.dp))
    }
}

@Composable
private fun SettingsCard(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(Panel)
            .border(1.dp, LineColor, RoundedCornerShape(14.dp))
            .padding(16.dp)
    ) {
        Text(title, color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 14.sp)
        Spacer(Modifier.height(10.dp))
        content()
    }
}

@Composable
private fun PermRow(title: String, sub: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(title, color = TextPrimary, fontSize = 13.sp)
            Text(sub, color = TextDim, fontSize = 11.sp)
        }
        OutlinedButton(onClick = onClick, contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)) {
            Text("Open", fontSize = 12.sp)
        }
    }
}
