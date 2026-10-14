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
import android.view.MotionEvent
import android.view.WindowManager
import android.graphics.PixelFormat
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
    private lateinit var advancedStatusText: TextView

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
        content.addView(statusText.apply { setPadding(0, 0, 0, dp(8)) })

        val rootButton = Button(this).apply {
            text = "VERIFICAR PERMISSÃO AVANÇADA"
            isAllCaps = false
            setOnClickListener { testRootAccess() }
        }
        content.addView(rootButton, LinearLayout.LayoutParams(-1, dp(50)).apply {
            bottomMargin = dp(8)
        })

        advancedStatusText = label(
            "Acesso avançado ainda não testado. Toque no botão acima para verificar se o aparelho oferece acesso root.",
            12f, Color.rgb(183, 194, 213), false
        )
        content.addView(advancedStatusText.apply { setPadding(0, 0, 0, dp(12)) })

        val overlayButton = Button(this).apply {
            text = "ATIVAR JANELA FLUTUANTE"
            isAllCaps = false
            setOnClickListener { requestOverlayAndShow() }
        }
        content.addView(overlayButton, LinearLayout.LayoutParams(-1, dp(50)).apply {
            bottomMargin = dp(8)
        })

        val developerButton = Button(this).apply {
            text = "ABRIR OPÇÕES DO DESENVOLVEDOR"
            isAllCaps = false
            setOnClickListener {
                runCatching {
                    startActivity(Intent(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS))
                }.onFailure {
                    runCatching { startActivity(Intent(Settings.ACTION_SETTINGS)) }
                }
            }
        }
        content.addView(developerButton, LinearLayout.LayoutParams(-1, dp(48)).apply {
            bottomMargin = dp(8)
        })

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
        val availableRam = memory.availMem.coerceAtMost(totalRam)
        val usedRam = (totalRam - availableRam).coerceAtLeast(0L)

        val dataStats = StatFs(Environment.getDataDirectory().absolutePath)
        val totalStorage = dataStats.totalBytes
        val freeStorage = dataStats.availableBytes
        val usedStorage = (totalStorage - freeStorage).coerceAtLeast(0L)

        val rootSignals = findRootSignals()
        val swapStatus = readSwapStatus()
        val zramStatus = readZramStatus()
        val externalVolumes = getExternalFilesDirs(null)
            .filterNotNull()
            .distinctBy { it.absolutePath }
            .mapNotNull { dir ->
                runCatching {
                    val stats = StatFs(dir.absolutePath)
                    val total = stats.totalBytes
                    val free = stats.availableBytes
                    val label = if (Environment.isExternalStorageRemovable(dir)) "Removível/cartão SD" else "Volume externo ou adotado"
                    "$label\nCapacidade acessível: ${formatBytes(total)} • Livre: ${formatBytes(free)}"
                }.getOrNull()
            }

        while (content.childCount > 11) content.removeViewAt(content.childCount - 1)

        content.addView(sectionTitle("MEMÓRIA"))
        content.addView(infoCard(
            "RAM física reportada pelo Android",
            formatBytes(totalRam),
            "Disponível agora: ${formatBytes(availableRam)}\nUso aproximado: ${formatBytes(usedRam)}",
            "A RAM disponível muda conforme os aplicativos e o sistema. Esta é a RAM que o Android reporta, não uma estimativa de RAM virtual."
        ))
        content.addView(infoCard(
            "zRAM (compressão de memória)",
            zramStatus.first,
            zramStatus.second,
            "zRAM comprime dados na própria RAM. A capacidade configurada não é RAM física adicional e os detalhes dependem do kernel."
        ))
        content.addView(infoCard(
            "Swap do sistema",
            swapStatus.first,
            swapStatus.second,
            "Swap usa armazenamento como apoio quando configurado pelo sistema. Não equivale à RAM física e pode ser muito mais lento."
        ))
        content.addView(infoCard(
            "Expansão de RAM do fabricante",
            "Não confirmável por API pública geral",
            "Se o fabricante oferecer RAM Boost, RAM Plus ou expansão de memória, confira nas Configurações do aparelho.",
            "O Android pode não expor esse ajuste ao aplicativo. Não vamos afirmar que está ativo sem evidência."
        ))

        content.addView(sectionTitle("ARMAZENAMENTO"))
        content.addView(infoCard(
            "Partição de dados interna",
            formatBytes(totalStorage),
            "Livre: ${formatBytes(freeStorage)}\nOcupado aproximadamente: ${formatBytes(usedStorage)}",
            "Capacidade total e espaço livre são valores diferentes. O aplicativo não altera a capacidade física."
        ))
        content.addView(infoCard(
            "Cartão SD / volumes acessíveis",
            "${externalVolumes.size} volume(s) acessível(is)",
            if (externalVolumes.isEmpty()) "Nenhum volume adicional foi exposto ao aplicativo." else externalVolumes.joinToString("\n\n"),
            "O Android limita o acesso a alguns volumes. O cartão SD não pode ser tratado automaticamente como RAM."
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

        content.addView(sectionTitle("POSSIBILIDADES DE OTIMIZAÇÃO"))
        content.addView(infoCard(
            "Modo de otimização",
            if (rootSignals.isEmpty()) "Modo seguro: sem root confirmado" else "Sinais de root encontrados",
            "Esta versão mede RAM, zRAM, swap e volumes acessíveis. Ainda não altera parâmetros do kernel nem cria swap.",
            "Antes de qualquer operação avançada, precisamos confirmar suporte do kernel, permissões de root e um método reversível. Nenhum ganho será simulado."
        ))

        content.addView(sectionTitle("INTEGRIDADE"))
        content.addView(infoCard(
            "Indicadores básicos de root",
            if (rootSignals.isEmpty()) "Nenhum sinal encontrado" else "${rootSignals.size} sinal(is) encontrado(s)",
            if (rootSignals.isEmpty()) "As verificações simples não encontraram os caminhos ou marcadores pesquisados."
            else rootSignals.joinToString("\n"),
            "Verificação indicativa somente de leitura. Resultado negativo não prova ausência de root nem confirma que o app pode executar comandos privilegiados."
        ))
        content.addView(infoCard(
            "Dispositivo",
            "${Build.MANUFACTURER} ${Build.MODEL}",
            "Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})\nBuild: ${Build.DISPLAY}",
            "Informações fornecidas pelo próprio sistema."
        ))

        statusText.text = "Atualizado agora • diagnóstico local • nenhuma alteração aplicada"
    }

    /**
     * Read-only root capability check. A root manager may display its own authorization prompt.
     * This does not change RAM, swap, zRAM, partitions, or kernel settings.
     */
    private fun testRootAccess() {
        advancedStatusText.text = "Verificando acesso privilegiado…"
        Thread {
            var process: Process? = null
            val result = try {
                val p = ProcessBuilder("su", "-c", "id").redirectErrorStream(true).start()
                process = p
                val completed = p.waitFor(4, java.util.concurrent.TimeUnit.SECONDS)
                if (!completed) {
                    p.destroyForcibly()
                    "Tempo esgotado. O aparelho não confirmou acesso root. Nenhuma alteração foi feita."
                } else {
                    val output = p.inputStream.bufferedReader().use { it.readText().trim() }
                    if (p.exitValue() == 0 && output.contains("uid=0")) {
                        "ACESSO ROOT CONFIRMADO. O comando de teste foi somente leitura. Isso não garante que o kernel permita alterar zRAM/swap."
                    } else {
                        "Acesso root negado ou indisponível. ${output.take(180).ifBlank { "O Android não autorizou o comando." }} Nenhuma alteração foi feita."
                    }
                }
            } catch (e: Exception) {
                "Root não disponível para este app (${e.javaClass.simpleName}). Em Android sem root, não existe uma permissão comum que libere alterações no kernel."
            } finally {
                runCatching { process?.destroy() }
            }
            runOnUiThread {
                advancedStatusText.text = result
                statusText.text = if (result.startsWith("ACESSO ROOT CONFIRMADO")) {
                    "Teste concluído • acesso privilegiado confirmado"
                } else {
                    "Teste concluído • nenhuma alteração aplicada"
                }
            }
        }.start()
    }

    private fun requestOverlayAndShow() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(this)) {
            advancedStatusText.text = "Autorize a janela flutuante na tela de configurações que abriu. Depois volte ao app e toque novamente no botão."
            runCatching {
                startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, android.net.Uri.parse("package:$packageName")))
            }.onFailure {
                startActivity(Intent(Settings.ACTION_SETTINGS))
            }
            return
        }
        showFloatingPanel()
    }

    private fun showFloatingPanel() {
        val wm = getSystemService(WINDOW_SERVICE) as WindowManager
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(12), dp(14), dp(12))
            background = rounded(Color.rgb(20, 30, 49), 18)
        }
        val title = label("RESOURCE LAB • FLUTUANTE", 13f, Color.rgb(87, 213, 190), true)
        panel.addView(title)
        val values = label(floatingStatsText(), 13f, Color.WHITE, false).apply {
            setPadding(0, dp(8), 0, dp(8))
        }
        panel.addView(values)
        val actions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        val update = Button(this).apply {
            text = "Atualizar"
            isAllCaps = false
            setOnClickListener { values.text = floatingStatsText() }
        }
        val close = Button(this).apply {
            text = "Fechar"
            isAllCaps = false
            setOnClickListener { runCatching { wm.removeView(panel) } }
        }
        actions.addView(update, LinearLayout.LayoutParams(0, dp(44), 1f))
        actions.addView(close, LinearLayout.LayoutParams(0, dp(44), 1f))
        panel.addView(actions)

        val params = WindowManager.LayoutParams(
            dp(280),
            WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY else WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = dp(12)
            y = dp(100)
        }
        var startX = 0
        var startY = 0
        var touchX = 0f
        var touchY = 0f
        title.setOnTouchListener { _, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    startX = params.x
                    startY = params.y
                    touchX = event.rawX
                    touchY = event.rawY
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    params.x = startX + (event.rawX - touchX).toInt()
                    params.y = startY + (event.rawY - touchY).toInt()
                    runCatching { wm.updateViewLayout(panel, params) }
                    true
                }
                else -> false
            }
        }
        runCatching { wm.addView(panel, params) }
            .onFailure { advancedStatusText.text = "Não foi possível abrir a janela flutuante: ${it.javaClass.simpleName}. Confira a permissão de sobreposição nas Configurações." }
    }

    private fun floatingStatsText(): String {
        val manager = getSystemService(ACTIVITY_SERVICE) as ActivityManager
        val memory = ActivityManager.MemoryInfo()
        manager.getMemoryInfo(memory)
        val stats = StatFs(Environment.getDataDirectory().absolutePath)
        return "RAM total: ${formatBytes(memory.totalMem)}\nRAM disponível: ${formatBytes(memory.availMem)}\nArmazenamento total: ${formatBytes(stats.totalBytes)}\nArmazenamento livre: ${formatBytes(stats.availableBytes)}\n\nJanela de diagnóstico. Não lê nem modifica a memória de outros apps."
    }

    private fun readSwapStatus(): Pair<String, String> {
        return try {
            val lines = File("/proc/swaps").readLines()
            val entries = lines.drop(1).filter { it.isNotBlank() }
            val memInfo = readMemInfo()
            val totalKb = memInfo["SwapTotal"] ?: 0L
            val freeKb = memInfo["SwapFree"] ?: 0L
            if (entries.isEmpty()) {
                val summary = if (totalKb > 0L) {
                    "MemInfo informa swap total de ${formatBytes(totalKb * 1024L)} e livre de ${formatBytes(freeKb * 1024L)}, mas /proc/swaps não expôs entradas."
                } else {
                    "Nenhuma área de swap ativa foi exposta pelas interfaces de leitura disponíveis."
                }
                "Nenhum swap listado" to summary
            } else {
                val listedKb = entries.mapNotNull {
                    it.trim().split(Regex("\\s+")).getOrNull(2)?.toLongOrNull()
                }.sum()
                "Swap listado: ${formatBytes(listedKb * 1024L)}" to
                    (entries.joinToString("\n") + "\nMemInfo: total ${formatBytes(totalKb * 1024L)}, livre ${formatBytes(freeKb * 1024L)}.")
            }
        } catch (_: Exception) {
            "Não disponível" to "O Android bloqueou a leitura de /proc/swaps ou não expôs essa informação."
        }
    }

    private fun readZramStatus(): Pair<String, String> {
        return try {
            val devices = File("/sys/block").listFiles()
                ?.filter { it.isDirectory && it.name.matches(Regex("zram\\d+")) }
                .orEmpty()

            if (devices.isEmpty()) {
                return "Nenhum dispositivo zRAM detectado" to
                    "O kernel não expôs dispositivos zRAM em /sys/block, ou o acesso foi bloqueado."
            }

            val details = devices.map { device ->
                val diskBytes = readLongFile(File(device, "disksize"))
                val mmStats = runCatching { File(device, "mm_stat").readText().trim().split(Regex("\\s+")) }.getOrNull()
                val originalBytes = mmStats?.getOrNull(0)?.toLongOrNull()
                val compressedBytes = mmStats?.getOrNull(1)?.toLongOrNull()
                val memoryBytes = mmStats?.getOrNull(2)?.toLongOrNull()
                buildString {
                    append(device.name)
                    append(": capacidade configurada ")
                    append(diskBytes?.let { formatBytes(it) } ?: "indisponível")
                    if (originalBytes != null && compressedBytes != null && memoryBytes != null) {
                        append("\nDados originais: ${formatBytes(originalBytes)}")
                        append("\nDados comprimidos: ${formatBytes(compressedBytes)}")
                        append("\nRAM usada pela zRAM: ${formatBytes(memoryBytes)}")
                    } else {
                        append("\nEstatísticas de compressão não acessíveis.")
                    }
                }
            }
            "zRAM detectada (${devices.size})" to details.joinToString("\n\n")
        } catch (_: Exception) {
            "Não disponível" to "Não foi possível ler as informações zRAM expostas pelo kernel."
        }
    }

    private fun readLongFile(file: File): Long? =
        runCatching { file.readText().trim().toLongOrNull() }.getOrNull()

    private fun readMemInfo(): Map<String, Long> {
        return runCatching {
            File("/proc/meminfo").readLines().mapNotNull { line ->
                val parts = line.split(Regex("\\s+"))
                val key = parts.firstOrNull()?.removeSuffix(":") ?: return@mapNotNull null
                val value = parts.getOrNull(1)?.toLongOrNull() ?: return@mapNotNull null
                key to value
            }.toMap()
        }.getOrDefault(emptyMap())
    }

    private fun shareReport() {
        val manager = getSystemService(ACTIVITY_SERVICE) as ActivityManager
        val memory = ActivityManager.MemoryInfo()
        manager.getMemoryInfo(memory)
        val stats = StatFs(Environment.getDataDirectory().absolutePath)
        val zram = readZramStatus()
        val swap = readSwapStatus()
        val report = buildString {
            appendLine("Android Resource Lab")
            appendLine("Dispositivo: ${Build.MANUFACTURER} ${Build.MODEL}")
            appendLine("Android: ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
            appendLine("RAM total reportada: ${formatBytes(memory.totalMem)}")
            appendLine("RAM disponível: ${formatBytes(memory.availMem)}")
            appendLine("zRAM: ${zram.first}")
            appendLine(zram.second)
            appendLine("Swap: ${swap.first}")
            appendLine(swap.second)
            appendLine("Armazenamento interno total: ${formatBytes(stats.totalBytes)}")
            appendLine("Armazenamento interno disponível: ${formatBytes(stats.availableBytes)}")
            appendLine("Nota: RAM virtual, swap e RAM física são conceitos diferentes; os dados dependem do que o sistema expõe.")
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
