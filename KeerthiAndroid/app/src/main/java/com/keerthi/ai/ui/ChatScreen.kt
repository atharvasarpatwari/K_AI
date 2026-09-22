package com.keerthi.ai.ui

import android.app.Activity
import android.content.Intent
import android.speech.RecognizerIntent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
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
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
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
    val haptics = LocalHapticFeedback.current

    // pending safety confirmations: messageIndex -> list of (actionName, args, resolvedText)
    var pendingActions by remember { mutableStateOf(mapOf<String, Pair<String, String>>()) }
    var resolved by remember { mutableStateOf(mapOf<String, String>()) }
    var sending by remember { mutableStateOf(false) }

    val speechLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val text = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()
            if (!text.isNullOrBlank()) input = text
        }
    }

    LaunchedEffect(state.chat.size, state.chat.lastOrNull()?.text?.length) {
        if (state.chat.isNotEmpty()) listState.animateScrollToItem(state.chat.size - 1)
    }

    fun send() {
        val text = input.trim()
        if (text.isBlank() || sending) return
        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
        input = ""
        if (text == "/reset") { vm.clearChat(); return }
        sending = true
        vm.sendUserMessage(text) { reply ->
            sending = false
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
            items(state.chat, key = { it.ts }) { msg ->
                MessageBubble(
                    msg = msg,
                    vm = vm,
                    pendingActions = pendingActions,
                    resolved = resolved,
                    onConfirm = { key, name, args ->
                        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                        scope.launch {
                            val r = ActionEngine.run(name, args, context, vm)
                            resolved = resolved + (key to r)
                            pendingActions = pendingActions - key
                        }
                    },
                    onCancel = { key ->
                        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                        pendingActions = pendingActions - key
                        resolved = resolved + (key to "cancelled")
                    }
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
                enabled = !sending,
                modifier = Modifier.weight(1f),
                placeholder = { Text("Talk to KEERTHI…", color = TextDim) },
                shape = RoundedCornerShape(14.dp),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { send() }),
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
                enabled = !sending,
                modifier = Modifier.size(42.dp).clip(CircleShape).background(if (sending) Panel2 else Signal)
            ) { Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Send", tint = if (sending) TextDim else Color(0xFF06130D)) }
        }
    }
}

@Composable
private fun ThinkingBubble() {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Avatar("K", SignalDim, Signal)
        TypingDots()
    }
}

@Composable
private fun TypingDots() {
    val transition = rememberInfiniteTransition(label = "typing")
    Row(
        modifier = Modifier
            .clip(bubbleShape(isUser = false))
            .background(Panel2)
            .border(1.dp, LineColor, bubbleShape(isUser = false))
            .padding(horizontal = 14.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        repeat(3) { i ->
            val alpha by transition.animateFloat(
                initialValue = 0.25f,
                targetValue = 1f,
                animationSpec = infiniteRepeatable(
                    animation = tween(500, delayMillis = i * 150, easing = LinearEasing),
                    repeatMode = RepeatMode.Reverse
                ),
                label = "dot$i"
            )
            Box(Modifier.size(6.dp).clip(CircleShape).background(Signal.copy(alpha = alpha)))
        }
    }
}

/** Chat-bubble corner shape with a flattened "tail" corner on the side pointing at the sender. */
private fun bubbleShape(isUser: Boolean) = RoundedCornerShape(
    topStart = 14.dp, topEnd = 14.dp,
    bottomStart = if (isUser) 14.dp else 4.dp,
    bottomEnd = if (isUser) 4.dp else 14.dp
)

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
    var visible by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { visible = true }

    AnimatedVisibility(
        visible = visible,
        enter = fadeIn(tween(220)) + slideInVertically(tween(220)) { it / 4 }
    ) {
        if (isUser) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                Column(horizontalAlignment = Alignment.End, modifier = Modifier.widthIn(max = 280.dp)) {
                    Text("you", color = TextDim, fontFamily = FontFamily.Monospace, fontSize = 10.sp)
                    Spacer(Modifier.height(3.dp))
                    Box(
                        modifier = Modifier
                            .clip(bubbleShape(isUser = true))
                            .background(Signal.copy(alpha = .16f))
                            .border(1.dp, SignalDim, bubbleShape(isUser = true))
                            .padding(horizontal = 12.dp, vertical = 8.dp)
                    ) {
                        Text(clean.ifBlank { "(no reply text)" }, color = TextPrimary, fontSize = 14.sp, lineHeight = 20.sp)
                    }
                }
            }
        } else {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Avatar("K", SignalDim, Signal)
                Column(modifier = Modifier.weight(1f)) {
                    Text("keerthi", color = TextDim, fontFamily = FontFamily.Monospace, fontSize = 10.sp)
                    Spacer(Modifier.height(3.dp))
                    Box(
                        modifier = Modifier
                            .clip(bubbleShape(isUser = false))
                            .background(Panel2)
                            .border(1.dp, LineColor, bubbleShape(isUser = false))
                            .padding(horizontal = 12.dp, vertical = 8.dp)
                    ) {
                        Text(clean.ifBlank { "(no reply text)" }, color = TextPrimary, fontSize = 14.sp, lineHeight = 20.sp)
                    }

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
