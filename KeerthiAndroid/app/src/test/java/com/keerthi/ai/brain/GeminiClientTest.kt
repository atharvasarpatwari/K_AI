package com.keerthi.ai.brain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class GeminiClientTest {

    @Test
    fun `extracts text from a valid SSE data line`() {
        val line = """data: {"candidates":[{"content":{"parts":[{"text":"hello"}]}}]}"""
        assertEquals("hello", GeminiClient.chunkTextFrom(line))
    }

    @Test
    fun `concatenates multiple parts in one chunk`() {
        val line = """data: {"candidates":[{"content":{"parts":[{"text":"foo"},{"text":"bar"}]}}]}"""
        assertEquals("foobar", GeminiClient.chunkTextFrom(line))
    }

    @Test
    fun `ignores non-data lines`() {
        assertNull(GeminiClient.chunkTextFrom(""))
        assertNull(GeminiClient.chunkTextFrom("event: ping"))
    }

    @Test
    fun `ignores data lines with no candidates`() {
        assertNull(GeminiClient.chunkTextFrom("""data: {"candidates":[]}"""))
    }

    @Test
    fun `ignores an empty text delta`() {
        val line = """data: {"candidates":[{"content":{"parts":[{"text":""}]}}]}"""
        assertNull(GeminiClient.chunkTextFrom(line))
    }
}
