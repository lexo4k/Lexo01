package com.lexo.lumen

import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import java.io.File
import java.io.FileOutputStream
import java.util.Locale

/**
 * Exporta artefatos de texto criados na conversa para Downloads/AURION AI.
 * Não executa código gerado. O usuário decide como abrir ou usar cada arquivo.
 */
object ArtifactStore {
    private const val MAX_BYTES = 1_048_576L
    private val allowedExtensions = setOf("md", "txt", "json", "csv", "html", "css", "js", "kt", "py", "xml")

    fun save(context: Context, requestedName: String, content: String): String {
        val safeContent = content.trim()
        require(safeContent.isNotEmpty()) { "O conteúdo está vazio." }
        require(safeContent.toByteArray(Charsets.UTF_8).size <= MAX_BYTES) {
            "O arquivo ultrapassa o limite de 1 MB desta versão."
        }

        val cleaned = requestedName
            .replace(Regex("[\\\\/:*?\"<>|\\\\p{Cntrl}]"), "_")
            .trim()
            .trim('.')
            .take(80)
            .ifBlank { "criacao-aurion.md" }
        val extension = cleaned.substringAfterLast('.', "").lowercase(Locale.ROOT)
        require(extension in allowedExtensions) {
            "Formato não permitido. Use MD, TXT, JSON, CSV, HTML, CSS, JS, KT, PY ou XML."
        }
        val displayName = if (cleaned.contains('.')) cleaned else "$cleaned.md"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, displayName)
                put(MediaStore.MediaColumns.MIME_TYPE, "text/plain")
                put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/AURION AI/")
                put(MediaStore.MediaColumns.IS_PENDING, 1)
            }
            val uri = context.contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                ?: error("O Android não conseguiu criar o arquivo em Downloads/AURION AI.")
            try {
                context.contentResolver.openOutputStream(uri, "w")?.bufferedWriter(Charsets.UTF_8)?.use {
                    it.write(safeContent)
                } ?: error("Não foi possível gravar o conteúdo.")
                val ready = ContentValues().apply { put(MediaStore.MediaColumns.IS_PENDING, 0) }
                context.contentResolver.update(uri, ready, null, null)
                return "Arquivo salvo em Downloads/AURION AI/$displayName"
            } catch (error: Exception) {
                context.contentResolver.delete(uri, null, null)
                throw error
            }
        }

        val directory = File(context.getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS), "AURION AI")
        if (!directory.exists() && !directory.mkdirs()) error("Não foi possível criar a pasta de exportação.")
        val output = File(directory, displayName)
        FileOutputStream(output).bufferedWriter(Charsets.UTF_8).use { it.write(safeContent) }
        return "Arquivo salvo em " + output.absolutePath
    }
}
