package com.keerthi.ai.ui

import android.app.Activity
import android.content.Intent
import android.speech.RecognizerIntent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.draw.clip
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.automirrored.filled.VolumeUp
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.keerthi.ai.brain.ActionEngine
import com.keerthi.ai.data.ChatMessage
import com.keerthi.ai.data.KeerthiViewModel
import com.keerthi.ai.ui.theme.*
import com.keerthi.ai.utils.TtsManager
import kotlinx.coroutines.launch

private val actionTagRegex = Regex("\\[ACTION:([A-Z_]+)(?::([^\\]]*))?\\]")

@Composable
fun ChatScreen(vm: KeerthiViewModel) {
    val context = LocalContext.current
    val state by vm.state.collectAsState()
    val thinking by vm.thinking.collectAsState()
    var input by remember { mutableStateOf("") }
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()

    // pending safety confirmations: messageIndex -> list of (actionName, args, resolvedText)
    var pendingActions by remember { mutableStateOf(mapOf<String, Pair<String, String>>()) }
    var resolved by remember { mutableStateOf(mapOf<String, String>()) }

    val speechLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val text = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()
            if (!text.isNullOrBlank()) input = text
        }
    }

    LaunchedEffect(state.chat.size) {
        if (state.chat.isNotEmpty()) listState.animateScrollToItem(state.chat.size - 1)
    }

    fun send() {
        val text = input.trim()
        if (text.isBlank()) return
        input = ""
        if (text == "/reset") { vm.clearChat(); return }
        vm.sendUserMessage(text) { reply ->
            val matches = actionTagRegex.findAll(reply).toList()
            matches.forEach { m ->
                val name = m.groupValues[1]
                val args = m.groupValues[2]
                val key = "${state.chat.size}_${m.range.first}"
                if (ActionEngine.isSafety(name)) {
                    pendingActions = pendingActions + (key to (name to args))
                } else {
                    scope.launch {
                        val r = ActionEngine.run(name, args, context, vm)
                        resolved = resolved + (key to r)
                    }
                }
            }
            if (state.voiceOutEnabled) {
                TtsManager.speak(reply)
            }
        }
    }

    Column(modifier = Modifier.fillMaxSize().background(Bg)) {
        LazyColumn(
            state = listState,
            modifier = Modifier.weight(1f).fillMaxWidth(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            items(state.chat) { msg ->
                MessageBubble(
                    msg = msg,
                    vm = vm,
                    pendingActions = pendingActions,
                    resolved = resolved,
                    onConfirm = { key, name, args ->
                        scope.launch {
                            val r = ActionEngine.run(name, args, context, vm)
                            resolved = resolved + (key to r)
                            pendingActions = pendingActions - key
                        }
                    },
                    onCancel = { key -> pendingActions = pendingActions - key; resolved = resolved + (key to "cancelled") }
                )
            }
            if (thinking) {
                item { ThinkingBubble() }
            }
        }

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Panel)
                .border(BorderStroke(1.dp, LineColor))
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            IconButton(
                onClick = {
                    val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                        putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                        putExtra(RecognizerIntent.EXTRA_PROMPT, "Talk to KEERTHI…")
                    }
                    try { speechLauncher.launch(intent) } catch (e: Exception) {}
                },
                modifier = Modifier.size(42.dp).clip(RoundedCornerShape(11.dp)).background(Panel2).border(1.dp, LineColor, RoundedCornerShape(11.dp))
            ) { Icon(Icons.Default.Mic, contentDescription = "Voice input", tint = TextSub) }

            IconButton(
                onClick = { vm.setVoiceOut(!state.voiceOutEnabled) },
                modifier = Modifier.size(42.dp).clip(RoundedCornerShape(11.dp))
                    .background(if (state.voiceOutEnabled) SignalDim.copy(alpha = .2f) else Panel2)
                    .border(1.dp, if (state.voiceOutEnabled) SignalDim else LineColor, RoundedCornerShape(11.dp))
            ) { Icon(Icons.AutoMirrored.Filled.VolumeUp, contentDescription = "Spoken replies", tint = if (state.voiceOutEnabled) Signal else TextSub) }

            OutlinedTextField(
                value = input,
                onValueChange = { input = it },
                modifier = Modifier.weight(1f),
                placeholder = { Text("Talk to KEERTHI…", color = TextDim) },
                shape = RoundedCornerShape(14.dp),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = SignalDim,
                    unfocusedBorderColor = LineColor,
                    focusedTextColor = TextPrimary,
                    unfocusedTextColor = TextPrimary,
                    cursorColor = Signal
                )
            )

            IconButton(
                onClick = { send() },
                modifier = Modifier.size(42.dp).clip(CircleShape).background(Signal)
            ) { Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Send", tint = Color(0xFF06130D)) }
        }
    }
}

@Composable
private fun ThinkingBubble() {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Avatar("K", SignalDim, Signal)
        Text("thinking…", color = TextDim, fontFamily = FontFamily.Monospace, fontSize = 12.sp)
    }
}

@Composable
private fun Avatar(label: String, borderColor: Color, textColor: Color) {
    Box(
        modifier = Modifier.size(26.dp).clip(RoundedCornerShape(7.dp)).background(Panel2).border(1.dp, borderColor, RoundedCornerShape(7.dp)),
        contentAlignment = Alignment.Center
    ) { Text(label, color = textColor, fontSize = 10.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace) }
}

@Composable
private fun MessageBubble(
    msg: ChatMessage,
    vm: KeerthiViewModel,
    pendingActions: Map<String, Pair<String, String>>,
    resolved: Map<String, String>,
    onConfirm: (String, String, String) -> Unit,
    onCancel: (String) -> Unit
) {
    val isUser = msg.role == "user"
    val clean = msg.text.replace(actionTagRegex, "").trim()
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Avatar(if (isUser) "YOU" else "K", if (isUser) LineColor else SignalDim, if (isUser) TextSub else Signal)
        Column(modifier = Modifier.weight(1f)) {
            Text(
                if (isUser) "you" else "keerthi",
                color = TextDim, fontFamily = FontFamily.Monospace, fontSize = 10.sp
            )
            Spacer(Modifier.height(3.dp))
            Text(clean.ifBlank { "(no reply text)" }, color = TextPrimary, fontSize = 14.sp, lineHeight = 20.sp)

            if (!isUser) {
                val matches = actionTagRegex.findAll(msg.text).toList()
                if (matches.isNotEmpty()) {
                    Column(modifier = Modifier.padding(top = 8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        matches.forEach { m ->
                            val name = m.groupValues[1]
                            val args = m.groupValues[2]
                            val key = "${vm.state.value.chat.indexOf(msg)}_${m.range.first}"
                            val done = resolved[key]
                            val pending = pendingActions[key]
                            when {
                                done != null -> ActionChip(text = "$name → $done", ok = done != "cancelled")
                                pending != null -> ConfirmCard(
                                    name = name, args = args,
                                    onConfirm = { onConfirm(key, name, args) },
                                    onCancel = { onCancel(key) }
                                )
                                else -> ActionChip(text = name + if (args.isNotBlank()) ":$args" else "", ok = true)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ActionChip(text: String, ok: Boolean) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(7.dp))
            .background(Panel2)
            .border(1.dp, if (ok) SignalDim else Amber, RoundedCornerShape(7.dp))
            .padding(horizontal = 9.dp, vertical = 5.dp)
    ) {
        Text(text, color = if (ok) Signal else Amber, fontFamily = FontFamily.Monospace, fontSize = 11.sp)
    }
}

@Composable
private fun ConfirmCard(name: String, args: String, onConfirm: () -> Unit, onCancel: () -> Unit) {
    Column(
        modifier = Modifier
            .clip(RoundedCornerShape(10.dp))
            .background(Violet.copy(alpha = .08f))
            .border(1.dp, Violet.copy(alpha = .4f), RoundedCornerShape(10.dp))
            .padding(10.dp)
    ) {
        Text(
            "⚠ SAFETY CONFIRMATION · $name" + if (args.isNotBlank()) ": $args" else "",
            color = Violet, fontFamily = FontFamily.Monospace, fontSize = 11.sp
        )
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                onClick = onConfirm,
                colors = ButtonDefaults.buttonColors(containerColor = Signal, contentColor = Color(0xFF06130D)),
                contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp)
            ) { Text("Confirm", fontSize = 12.sp, fontWeight = FontWeight.Bold) }
            OutlinedButton(
                onClick = onCancel,
                contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp)
            ) { Text("Cancel", fontSize = 12.sp) }
        }
    }
}
