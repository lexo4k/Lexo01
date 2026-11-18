package com.lexo.lumen

import java.io.File
import java.util.UUID

/**
 * Installs a staged model without deleting the previous file before the new
 * file is safely in place. A returned backup can be rolled back after a
 * runtime activation failure or discarded after activation succeeds.
 */
internal object ModelFileInstaller {
    fun install(
        temporary: File,
        target: File,
        rename: (File, File) -> Boolean = { source, destination -> source.renameTo(destination) }
    ): File? {
        require(temporary.isFile) { "O arquivo temporário do modelo não existe." }
        val temporaryParent = temporary.canonicalFile.parentFile
        val targetParent = target.canonicalFile.parentFile
        require(temporaryParent != null && temporaryParent == targetParent) {
            "O arquivo temporário e o destino precisam estar na mesma pasta."
        }

        val backup = if (target.exists()) {
            File(targetParent, target.name + ".backup-" + UUID.randomUUID())
        } else {
            null
        }
        if (backup != null && !rename(target, backup)) {
            throw IllegalStateException("Não foi possível preservar o modelo anterior antes da substituição.")
        }
        if (!rename(temporary, target)) {
            if (backup != null && !rename(backup, target)) {
                throw IllegalStateException(
                    "A instalação falhou e o modelo anterior foi preservado em " + backup.absolutePath
                )
            }
            throw IllegalStateException("O Android não conseguiu finalizar a instalação do modelo.")
        }
        return backup
    }

    fun rollback(target: File, backup: File): Boolean {
        if (target.exists() && !target.delete()) return false
        return backup.exists() && backup.renameTo(target)
    }

    fun discardBackup(backup: File?): Boolean {
        if (backup == null || !backup.exists()) return true
        return backup.delete()
    }
}
