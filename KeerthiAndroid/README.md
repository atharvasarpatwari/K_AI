# KEERTHI — Android

A native Android rebuild of the KeerthiAI desktop assistant: the same persona, the same
`[ACTION:NAME:args]` command protocol, and the same 47-action command library — reimplemented
against real Android APIs wherever the platform allows it, and honestly labeled where it doesn't.

## Opening the project

1. Open Android Studio (Koala/2024.1 or newer) → **Open** → select this `KeerthiAndroid` folder.
   Or build from the command line: `gradlew.bat assembleDebug` (Windows) / `./gradlew assembleDebug`
   — the Gradle 8.7 wrapper is checked in, so no local Gradle install is needed.
2. Run on a device or emulator with **API 26+**.

> Build status: `assembleDebug` compiles clean (zero warnings) against AGP 8.5.2 / Kotlin 1.9.24 /
> compileSdk 34, and the debug APK has been installed and smoke-tested on a real device
> (Realme RMX5264, Android 15).

## Before you can chat with it

KEERTHI's brain calls the **Gemini API** directly from the device (same model family the original
desktop app used). Get a free key at aistudio.google.com/apikey, open the app's **Settings** tab,
and paste it in — it's stored only in the app's local DataStore, never sent anywhere else.

## What's real vs. simulated

| Feature | Status |
|---|---|
| Chat brain (Gemini) | ✅ real |
| Timers, tasks, scheduled reminders | ✅ real — `AlarmManager` + notifications, survive reboot |
| Memory facts, macros (record/replay) | ✅ real — persisted with Jetpack DataStore |
| Launching installed apps | ✅ real — `PackageManager` + launch intent |
| Open URL / web search / Play Store search | ✅ real |
| Volume | ✅ real — `AudioManager` |
| Brightness | ✅ real — needs the "Modify system settings" permission (Settings tab has a shortcut) |
| Screen lock / turn screen off | ✅ real — needs KEERTHI enabled as a **Device Admin** (Settings tab has a shortcut) |
| Weather | ✅ real — Open-Meteo fetch, falls back to a labeled estimate if offline |
| Voice in / voice out | ✅ real — Android `SpeechRecognizer` intent + `TextToSpeech` |
| Memory / disk / battery readouts | ✅ real device stats |
| CPU usage, process list, kill process | ⚠️ **not possible** on stock Android — third-party apps can't see or stop other apps' processes. KEERTHI says so instead of faking a number. |
| Shell commands | ⚠️ **not possible** without root — refused, not run. |
| Simulated keystrokes / mouse / screenshots | ⚠️ **not implemented** — would need an Accessibility Service / MediaProjection consent flow that isn't wired up in this build, to keep the app simple and Play-Store-safe. |
| Shutdown / restart / silent install | ⚠️ **not possible** for a regular app without root or device-owner status. |
| Window management (focus/minimize/maximize) | 🖥️ tracked on an in-app **virtual desktop** for continuity with the desktop version — Android itself has no such API for other apps' windows. |

## Project layout

```
app/src/main/java/com/keerthi/ai/
  MainActivity.kt          bottom-nav shell (Chat / Dashboard / Settings)
  KeerthiApp.kt             Application class, notification channel setup
  data/                     KeerthiState model, DataStore persistence, ViewModel
  brain/                    SystemPrompt, GeminiClient, ActionEngine, AlarmScheduler
  services/                 BroadcastReceivers: timers, scheduled tasks, boot, device admin
  ui/                       Compose screens (Chat, Dashboard, Settings) + theme
  utils/                    SystemInfo (real battery/mem/disk), TtsManager
```

## Notes

- Min SDK 26, target/compile SDK 34, Kotlin 1.9.24, Jetpack Compose (Material 3).
- No API key or secrets are baked into the project — you provide your own Gemini key at runtime.
