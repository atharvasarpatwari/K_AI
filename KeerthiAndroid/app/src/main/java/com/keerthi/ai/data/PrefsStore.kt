package com.keerthi.ai.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

val Context.dataStore by preferencesDataStore(name = "keerthi_state")

private val STATE_KEY = stringPreferencesKey("keerthi_state_json")

private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

object PrefsStore {

    suspend fun load(context: Context): KeerthiState {
        return try {
            val prefs = context.dataStore.data.first()
            val raw = prefs[STATE_KEY] ?: return KeerthiState()
            json.decodeFromString(KeerthiState.serializer(), raw)
        } catch (e: Exception) {
            KeerthiState()
        }
    }

    suspend fun save(context: Context, state: KeerthiState) {
        context.dataStore.edit { prefs ->
            prefs[STATE_KEY] = json.encodeToString(state)
        }
    }
}
