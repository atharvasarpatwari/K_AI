package com.keerthi.ai

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Chat
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.keerthi.ai.data.KeerthiViewModel
import com.keerthi.ai.ui.ChatScreen
import com.keerthi.ai.ui.DashboardScreen
import com.keerthi.ai.ui.SettingsScreen
import com.keerthi.ai.ui.theme.*
import com.keerthi.ai.utils.TtsManager

class MainActivity : ComponentActivity() {

    private val permissionLauncher = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        TtsManager.init(this)
        requestRuntimePermissions()

        setContent {
            KeerthiTheme {
                val vm: KeerthiViewModel = viewModel()
                KeerthiApp(vm)
            }
        }
    }

    private fun requestRuntimePermissions() {
        val needed = mutableListOf<String>()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.RECORD_AUDIO)
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.ACCESS_COARSE_LOCATION)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            needed.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        if (needed.isNotEmpty()) permissionLauncher.launch(needed.toTypedArray())
    }

    override fun onDestroy() {
        super.onDestroy()
        TtsManager.shutdown()
    }
}

private enum class Tab(val label: String) { CHAT("Chat"), DASH("Dashboard"), SETTINGS("Settings") }

@Composable
private fun KeerthiApp(vm: KeerthiViewModel) {
    var tab by remember { mutableStateOf(Tab.CHAT) }

    Scaffold(
        containerColor = Bg,
        bottomBar = {
            NavigationBar(containerColor = Panel, contentColor = TextPrimary) {
                NavigationBarItem(
                    selected = tab == Tab.CHAT,
                    onClick = { tab = Tab.CHAT },
                    icon = { Icon(Icons.AutoMirrored.Filled.Chat, contentDescription = null) },
                    label = { Text("Chat", fontSize = 11.sp) },
                    colors = navColors()
                )
                NavigationBarItem(
                    selected = tab == Tab.DASH,
                    onClick = { tab = Tab.DASH },
                    icon = { Icon(Icons.Default.Dashboard, contentDescription = null) },
                    label = { Text("Dashboard", fontSize = 11.sp) },
                    colors = navColors()
                )
                NavigationBarItem(
                    selected = tab == Tab.SETTINGS,
                    onClick = { tab = Tab.SETTINGS },
                    icon = { Icon(Icons.Default.Settings, contentDescription = null) },
                    label = { Text("Settings", fontSize = 11.sp) },
                    colors = navColors()
                )
            }
        }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding).background(Bg)) {
            AnimatedContent(
                targetState = tab,
                transitionSpec = { fadeIn(tween(180)) togetherWith fadeOut(tween(180)) },
                label = "tab"
            ) { current ->
                when (current) {
                    Tab.CHAT -> ChatScreen(vm)
                    Tab.DASH -> DashboardScreen(vm)
                    Tab.SETTINGS -> SettingsScreen(vm)
                }
            }
        }
    }
}

@Composable
private fun navColors() = NavigationBarItemDefaults.colors(
    selectedIconColor = Signal,
    selectedTextColor = Signal,
    unselectedIconColor = TextDim,
    unselectedTextColor = TextDim,
    indicatorColor = Panel2
)
