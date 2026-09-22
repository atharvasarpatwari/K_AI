package com.keerthi.ai.ui

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.keerthi.ai.brain.ActionEngine
import com.keerthi.ai.data.KeerthiViewModel
import com.keerthi.ai.ui.theme.*
import com.keerthi.ai.utils.SystemInfo
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.text.DateFormat
import java.util.Date

@Composable
fun DashboardScreen(vm: KeerthiViewModel) {
    val context = LocalContext.current
    val state by vm.state.collectAsState()
    val scope = rememberCoroutineScope()
    var tick by remember { mutableStateOf(0L) }

    LaunchedEffect(Unit) {
        while (true) { delay(1000); tick = System.currentTimeMillis() }
    }

    val memPct = remember(tick) { SystemInfo.memoryPercent(context) }
    val diskPct = remember { SystemInfo.diskPercent() }
    val battery = remember(tick / 15000) { SystemInfo.batterySummary(context) }

    LazyColumn(
        modifier = Modifier.fillMaxSize().background(Bg),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            DashCard(title = "Telemetry", tag = "live") {
                StatRow("Memory", "$memPct%")
                ProgressBar(memPct, Signal)
                Spacer(Modifier.height(10.dp))
                StatRow("Disk", "$diskPct%")
                ProgressBar(diskPct, Amber)
                Spacer(Modifier.height(10.dp))
                StatRow("Battery", battery)
                Text(
                    "Memory, disk and battery are real device readings. Android does not expose live per-app CPU usage to third-party apps.",
                    color = TextDim, fontSize = 11.sp, modifier = Modifier.padding(top = 6.dp)
                )
            }
        }

        item {
            DashCard(title = "Virtual Desktop", tag = "windows") {
                if (state.windows.isEmpty()) {
                    EmptyHint("Ask KEERTHI to open an app to see it here")
                } else {
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        state.windows.forEach { w ->
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(w.name, color = TextPrimary, fontSize = 13.sp)
                                Text(w.state, color = TextDim, fontFamily = FontFamily.Monospace, fontSize = 11.sp)
                            }
                        }
                    }
                }
            }
        }

        item {
            DashCard(title = "Tasks", tag = "${state.tasks.size}") {
                if (state.tasks.isEmpty()) EmptyHint("no tasks")
                else Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    state.tasks.forEach { t ->
                        RowItem(t.text, null) { vm.removeTaskById(t.id) }
                    }
                }
                AddRow(hint = "Add a task…") { text -> vm.addTask(text) }
            }
        }

        item {
            DashCard(title = "Timers", tag = "${state.timers.size}") {
                if (state.timers.isEmpty()) EmptyHint("no active timers")
                else Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    state.timers.forEach { t ->
                        val remaining = ((t.endTs - System.currentTimeMillis()) / 1000).coerceAtLeast(0)
                        RowItem(t.label, "${remaining}s") { vm.cancelTimerById(t.id) }
                    }
                }
            }
        }

        item {
            DashCard(title = "Scheduled", tag = "${state.scheduled.size}") {
                if (state.scheduled.isEmpty()) EmptyHint("nothing scheduled")
                else Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    state.scheduled.forEach { s ->
                        val time = DateFormat.getTimeInstance(DateFormat.SHORT).format(Date(s.runTs))
                        RowItem(s.cmd, time) { vm.cancelScheduledById(s.id) }
                    }
                }
            }
        }

        item {
            DashCard(title = "Memory", tag = "${state.facts.size}") {
                if (state.facts.isEmpty()) EmptyHint("KEERTHI has not saved anything yet")
                else Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    state.facts.forEach { f ->
                        RowItem(f.text, null) { vm.removeFact(f.id) }
                    }
                }
            }
        }

        item {
            DashCard(
                title = "Macros",
                tag = state.macroRecording?.let { "recording \"$it\"" } ?: "${state.macros.size}"
            ) {
                if (state.macros.isEmpty()) EmptyHint("say \u201crecord a macro called demo\u201d to start")
                else Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    state.macros.forEach { (name, steps) ->
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(name, color = TextPrimary, fontSize = 13.sp, modifier = Modifier.weight(1f))
                            Text("${steps.size} steps", color = TextDim, fontFamily = FontFamily.Monospace, fontSize = 11.sp)
                            IconButton(onClick = {
                                scope.launch { ActionEngine.run("MACRO_REPLAY", name, context, vm) }
                            }, modifier = Modifier.size(28.dp)) {
                                Icon(Icons.Default.PlayArrow, contentDescription = "Replay", tint = Signal)
                            }
                            IconButton(onClick = { vm.macroDelete(name) }, modifier = Modifier.size(28.dp)) {
                                Icon(Icons.Default.Close, contentDescription = "Delete", tint = TextDim)
                            }
                        }
                    }
                }
            }
        }

        item { Spacer(Modifier.height(8.dp)) }
    }
}

@Composable
private fun DashCard(title: String, tag: String, content: @Composable ColumnScope.() -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(Panel)
            .border(1.dp, LineColor, RoundedCornerShape(14.dp))
            .padding(16.dp)
    ) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(
                title.uppercase(), color = TextSub, fontSize = 11.sp, fontWeight = FontWeight.Bold,
                letterSpacing = 1.sp
            )
            Text(tag, color = TextDim, fontFamily = FontFamily.Monospace, fontSize = 10.sp)
        }
        Spacer(Modifier.height(10.dp))
        content()
    }
}

@Composable
private fun StatRow(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = TextSub, fontSize = 12.sp)
        Text(value, color = TextPrimary, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold, fontSize = 13.sp)
    }
}

@Composable
private fun ProgressBar(pct: Int, color: androidx.compose.ui.graphics.Color) {
    val animatedFraction by animateFloatAsState(
        targetValue = pct / 100f,
        animationSpec = tween(600),
        label = "progress"
    )
    Box(
        modifier = Modifier
            .fillMaxWidth().height(6.dp)
            .clip(RoundedCornerShape(3.dp))
            .background(Panel2)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(animatedFraction)
                .fillMaxHeight()
                .clip(RoundedCornerShape(3.dp))
                .background(color)
        )
    }
}

@Composable
private fun EmptyHint(text: String) {
    Text(text, color = TextDim, fontFamily = FontFamily.Monospace, fontSize = 12.sp, modifier = Modifier.padding(vertical = 6.dp))
}

@Composable
private fun RowItem(text: String, meta: String?, onDelete: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(text, color = TextPrimary, fontSize = 13.sp, modifier = Modifier.weight(1f))
        if (meta != null) {
            Text(meta, color = TextDim, fontFamily = FontFamily.Monospace, fontSize = 11.sp, modifier = Modifier.padding(end = 6.dp))
        }
        IconButton(onClick = onDelete, modifier = Modifier.size(24.dp)) {
            Icon(Icons.Default.Close, contentDescription = "Remove", tint = TextDim, modifier = Modifier.size(15.dp))
        }
    }
}

@Composable
private fun AddRow(hint: String, onAdd: (String) -> Unit) {
    var text by remember { mutableStateOf("") }
    Row(modifier = Modifier.fillMaxWidth().padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedTextField(
            value = text,
            onValueChange = { text = it },
            modifier = Modifier.weight(1f),
            placeholder = { Text(hint, color = TextDim, fontSize = 12.sp) },
            textStyle = androidx.compose.ui.text.TextStyle(fontSize = 13.sp, color = TextPrimary),
            singleLine = true,
            shape = RoundedCornerShape(10.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = SignalDim, unfocusedBorderColor = LineColor,
                focusedTextColor = TextPrimary, unfocusedTextColor = TextPrimary, cursorColor = Signal
            )
        )
        Button(
            onClick = { if (text.isNotBlank()) { onAdd(text); text = "" } },
            colors = ButtonDefaults.buttonColors(containerColor = Panel2, contentColor = TextPrimary),
            contentPadding = PaddingValues(horizontal = 14.dp)
        ) { Text("Add", fontSize = 12.sp) }
    }
}
