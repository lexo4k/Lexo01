package com.androidresourcelab

import android.app.Activity
import android.app.ActivityManager
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.StatFs
import android.content.Intent
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import java.io.File
import java.util.Locale

class MainActivity : Activity() {
    private lateinit var content: LinearLayout
    private lateinit var statusText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildScreen()
        refreshDiagnostics()
    }

    private fun buildScreen() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(9, 15, 29))
            setPadding(dp(18), dp(18), dp(18), dp(24))
        }

        val scroll = ScrollView(this)
        content = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }

        val brand = label("RESOURCE LAB", 13f, Color.rgb(87, 213, 190), true)
        brand.letterSpacing = 0.12f
        content.addView(brand)

        content.addView(label("Seu Android,\npor dentro.", 30f, Color.WHITE, true).apply {
            setPadding(0, dp(8), 0, dp(8))
        })
        content.addView(label(
            "Diagnóstico real de memória e armazenamento. Sem números inventados.",
            15f, Color.rgb(183, 194, 213), false
        ).apply { setPadding(0, 0, 0, dp(18)) })

        val refresh = Button(this).apply {
            text = "VERIFICAR AGORA"
            textSize = 14f
            isAllCaps = false
            setTextColor(Color.rgb(7, 20, 29))
            background = rounded(Color.rgb(87, 213, 190), 16)
            setOnClickListener { refreshDiagnostics() }
        }
        content.addView(refresh, LinearLayout.LayoutParams(-1, dp(52)).apply {
            bottomMargin = dp(12)
        })

        statusText = label("Preparando diagnóstico…", 13f, Color.rgb(183, 194, 213), false)
        content.addView(statusText.apply { setPadding(0, 0, 0, dp(14)) })

        val storageButton = Button(this).apply {
            text = "ABRIR CONFIGURAÇÕES DE ARMAZENAMENTO"
            isAllCaps = false
            setOnClickListener {
                runCatching { startActivity(Intent(Settings.ACTION_INTERNAL_STORAGE_SETTINGS)) }
                    .onFailure { runCatching { startActivity(Intent(Settings.ACTION_SETTINGS)) } }
            }
        }
        content.addView(storageButton, LinearLayout.LayoutParams(-1, dp(50)).apply {
            bottomMargin = dp(8)
        })

        val shareButton = Button(this).apply {
            text = "COMPARTILHAR RELATÓRIO"
            isAllCaps = false
            setOnClickListener { shareReport() }
        }
        content.addView(shareButton, LinearLayout.LayoutParams(-1, dp(50)).apply {
            bottomMargin = dp(12)
        })

        scroll.addView(content)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
    }

    private fun refreshDiagnostics() {
        val manager = getSystemService(ACTIVITY_SERVICE) as ActivityManager
        val memory = ActivityManager.MemoryInfo()
        manager.getMemoryInfo(memory)

        val totalRam = memory.totalMem
        val availableRam = memory.availMem
        val usedRam = (totalRam - availableRam).coerceAtLeast(0L)

        val dataStats = StatFs(Environment.getDataDirectory().absolutePath)
        val totalStorage = dataStats.totalBytes
        val freeStorage = dataStats.availableBytes
        val usedStorage = (totalStorage - freeStorage).coerceAtLeast(0L)

        val rootSignals = findRootSignals()
        val swapStatus = readSwapStatus()
        val externalVolumes = getExternalFilesDirs(null)
            .filterNotNull()
            .map { it.absolutePath }
            .distinct()

        while (content.childCount > 7) content.removeViewAt(content.childCount - 1)

        content.addView(sectionTitle("MEMÓRIA"))
        content.addView(infoCard(
            "RAM reportada pelo Android",
            formatBytes(totalRam),
            "Disponível agora: ${formatBytes(availableRam)}\nEm uso aproximado: ${formatBytes(usedRam)}",
            "A RAM disponível varia conforme os aplicativos abertos."
        ))
        content.addView(infoCard(
            "Swap detectável",
            swapStatus.first,
            swapStatus.second,
            "A leitura pode ser bloqueada pelo Android. Swap não equivale à RAM física e pode ser mais lento."
        ))
        content.addView(infoCard(
            "Expansão de RAM do fabricante",
            "Verificação manual necessária",
            "Confira em Configurações se o fabricante oferece RAM Boost, RAM Plus ou recurso equivalente.",
            "O app não ativa opções ocultas nem altera o sistema sem suporte documentado."
        ))

        content.addView(sectionTitle("ARMAZENAMENTO"))
        content.addView(infoCard(
            "Partição de dados",
            formatBytes(totalStorage),
            "Livre: ${formatBytes(freeStorage)}\nOcupado aproximadamente: ${formatBytes(usedStorage)}",
            "Capacidade total e espaço livre são valores diferentes."
        ))
        content.addView(infoCard(
            "Volumes acessíveis",
            "${externalVolumes.size} encontrados",
            if (externalVolumes.isEmpty()) "Nenhum volume adicional foi exposto ao aplicativo." else externalVolumes.joinToString("\n"),
            "O Android pode ocultar volumes ou limitar o acesso a eles."
        ))
        val recommendation = when {
            freeStorage < 2L * 1024 * 1024 * 1024 -> "Pouco espaço livre. Revise downloads e arquivos grandes nas Configurações."
            freeStorage < 8L * 1024 * 1024 * 1024 -> "Espaço moderado. Remover arquivos que você não precisa pode ajudar."
            else -> "O espaço livre parece confortável. Não é necessário limpar só por limpar."
        }
        content.addView(infoCard(
            "Recomendação de armazenamento",
            if (freeStorage < 2L * 1024 * 1024 * 1024) "Atenção" else "Análise concluída",
            recommendation,
            "O app não apaga arquivos automaticamente. Você decide o que remover."
        ))

        content.addView(sectionTitle("INTEGRIDADE"))
        content.addView(infoCard(
            "Sinais básicos de root",
            if (rootSignals.isEmpty()) "Nenhum sinal encontrado" else "${rootSignals.size} sinal(is) encontrado(s)",
            if (rootSignals.isEmpty()) "As verificações simples não encontraram os caminhos ou marcadores pesquisados."
            else rootSignals.joinToString("\n"),
            "Verificação indicativa somente de leitura. Resultado negativo não prova ausência de root."
        ))
        content.addView(infoCard(
            "Dispositivo",
            "${Build.MANUFACTURER} ${Build.MODEL}",
            "Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})\nBuild: ${Build.DISPLAY}",
            "Informações fornecidas pelo próprio sistema."
        ))

        statusText.text = "Atualizado agora • análise local • nenhum dado enviado"
    }

    private fun readSwapStatus(): Pair<String, String> {
        return try {
            val lines = File("/proc/swaps").readLines()
            val entries = lines.drop(1).filter { it.isNotBlank() }
            if (entries.isEmpty()) {
                "Nenhum swap visível" to "O sistema não mostrou áreas de swap ativas para este aplicativo."
            } else {
                val totalKb = entries.mapNotNull { it.trim().split(Regex("\\s+")).getOrNull(2)?.toLongOrNull() }.sum()
                "Swap visível: ${formatBytes(totalKb * 1024L)}" to entries.joinToString("\n")
            }
        } catch (_: Exception) {
            "Não disponível" to "O Android bloqueou a leitura de /proc/swaps ou não expôs essa informação."
        }
    }

    private fun shareReport() {
        val manager = getSystemService(ACTIVITY_SERVICE) as ActivityManager
        val memory = ActivityManager.MemoryInfo()
        manager.getMemoryInfo(memory)
        val stats = StatFs(Environment.getDataDirectory().absolutePath)
        val report = buildString {
            appendLine("Android Resource Lab")
            appendLine("Dispositivo: ${Build.MANUFACTURER} ${Build.MODEL}")
            appendLine("Android: ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
            appendLine("RAM total reportada: ${formatBytes(memory.totalMem)}")
            appendLine("RAM disponível: ${formatBytes(memory.availMem)}")
            appendLine("Armazenamento de dados total: ${formatBytes(stats.totalBytes)}")
            appendLine("Armazenamento disponível: ${formatBytes(stats.availableBytes)}")
            appendLine("Swap: ${readSwapStatus().first}")
            appendLine("Nota: valores reportados pelo sistema; RAM virtual pode não estar incluída.")
        }
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_SUBJECT, "Relatório Android Resource Lab")
            putExtra(Intent.EXTRA_TEXT, report)
        }
        startActivity(Intent.createChooser(intent, "Compartilhar diagnóstico"))
    }

    private fun findRootSignals(): List<String> {
        val signals = mutableListOf<String>()
        val paths = listOf(
            "/system/bin/su",
            "/system/xbin/su",
            "/sbin/su",
            "/system/app/Superuser.apk",
            "/data/adb/magisk",
            "/sbin/.magisk"
        )
        paths.filter { File(it).exists() }.forEach { signals.add("Encontrado: $it") }
        if (Build.TAGS?.contains("test-keys", ignoreCase = true) == true) {
            signals.add("Build contém marcador test-keys")
        }
        return signals
    }

    private fun sectionTitle(text: String): TextView =
        label(text, 12f, Color.rgb(87, 213, 190), true).apply {
            letterSpacing = 0.1f
            setPadding(2, dp(18), 0, dp(9))
        }

    private fun infoCard(title: String, value: String, details: String, note: String): View {
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(15), dp(16), dp(15))
            background = rounded(Color.rgb(20, 30, 49), 18)
        }
        card.addView(label(title, 14f, Color.rgb(183, 194, 213), true))
        card.addView(label(value, 24f, Color.WHITE, true).apply {
            setPadding(0, dp(7), 0, dp(7))
        })
        card.addView(label(details, 13f, Color.rgb(223, 230, 241), false))
        card.addView(label(note, 11f, Color.rgb(135, 151, 177), false).apply {
            setPadding(0, dp(9), 0, 0)
        })
        return card.apply {
            layoutParams = LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(10) }
        }
    }

    private fun label(text: String, size: Float, color: Int, bold: Boolean): TextView =
        TextView(this).apply {
            this.text = text
            textSize = size
            setTextColor(color)
            typeface = if (bold) Typeface.create("sans-serif", Typeface.BOLD) else Typeface.create("sans-serif", Typeface.NORMAL)
            gravity = Gravity.START
            setLineSpacing(dp(3).toFloat(), 1f)
        }

    private fun rounded(color: Int, radiusDp: Int) = GradientDrawable().apply {
        setColor(color)
        cornerRadius = dp(radiusDp).toFloat()
    }

    private fun formatBytes(bytes: Long): String {
        if (bytes < 0) return "Indisponível"
        if (bytes < 1024L) return "$bytes B"
        val units = arrayOf("KB", "MB", "GB", "TB", "PB")
        var value = bytes.toDouble()
        var index = -1
        do {
            value /= 1024.0
            index++
        } while (value >= 1024.0 && index < units.lastIndex)
        return String.format(Locale.getDefault(), "%.2f %s", value, units[index])
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
