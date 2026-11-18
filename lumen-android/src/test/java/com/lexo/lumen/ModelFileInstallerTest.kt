package com.lexo.lumen

import java.nio.file.Files
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ModelFileInstallerTest {
    @Test
    fun installKeepsPreviousModelAvailableForRollback() {
        val directory = Files.createTempDirectory("aurion-model-install").toFile()
        try {
            val temporary = directory.resolve("new.gguf").apply { writeText("new-model") }
            val target = directory.resolve("model.gguf").apply { writeText("old-model") }

            val backup = ModelFileInstaller.install(temporary, target)

            assertEquals("new-model", target.readText())
            assertFalse(temporary.exists())
            assertNotNull(backup)
            assertEquals("old-model", backup!!.readText())
            assertTrue(ModelFileInstaller.rollback(target, backup))
            assertEquals("old-model", target.readText())
            assertFalse(backup.exists())
        } finally {
            directory.deleteRecursively()
        }
    }

    @Test
    fun failedInstallRestoresPreviousModel() {
        val directory = Files.createTempDirectory("aurion-model-failure").toFile()
        try {
            val temporary = directory.resolve("new.gguf").apply { writeText("new-model") }
            val target = directory.resolve("model.gguf").apply { writeText("old-model") }
            var renameCalls = 0

            val error = runCatching {
                ModelFileInstaller.install(temporary, target) { source, destination ->
                    renameCalls += 1
                    if (renameCalls == 2) false else source.renameTo(destination)
                }
            }.exceptionOrNull()

            assertNotNull(error)
            assertEquals("old-model", target.readText())
            assertTrue(temporary.exists())
            assertEquals(3, renameCalls)
        } finally {
            directory.deleteRecursively()
        }
    }

    @Test
    fun installIntoEmptyTargetDoesNotCreateBackup() {
        val directory = Files.createTempDirectory("aurion-model-empty").toFile()
        try {
            val temporary = directory.resolve("new.gguf").apply { writeText("new-model") }
            val target = directory.resolve("model.gguf")

            val backup = ModelFileInstaller.install(temporary, target)

            assertEquals("new-model", target.readText())
            assertTrue(backup == null)
        } finally {
            directory.deleteRecursively()
        }
    }
}
