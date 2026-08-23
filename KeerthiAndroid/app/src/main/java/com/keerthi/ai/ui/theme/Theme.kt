package com.keerthi.ai.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val Bg = Color(0xFF0A0D12)
val Panel = Color(0xFF11151C)
val Panel2 = Color(0xFF161B24)
val LineColor = Color(0xFF232A36)
val TextPrimary = Color(0xFFE7ECF3)
val TextSub = Color(0xFF8A93A6)
val TextDim = Color(0xFF5B6478)
val Signal = Color(0xFF3DDC97)
val SignalDim = Color(0xFF1F6B4D)
val Amber = Color(0xFFE8A33D)
val Violet = Color(0xFF8B7CF6)
val Red = Color(0xFFE5596A)

private val KeerthiColorScheme = darkColorScheme(
    primary = Signal,
    onPrimary = Color(0xFF06130D),
    secondary = Violet,
    background = Bg,
    surface = Panel,
    onBackground = TextPrimary,
    onSurface = TextPrimary,
    error = Red
)

@Composable
fun KeerthiTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = KeerthiColorScheme,
        typography = MaterialTheme.typography,
        content = content
    )
}
