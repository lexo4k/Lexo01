package com.lexo.lumen

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.webkit.PermissionRequest
import android.webkit.JavascriptInterface
import dev.ffmpegkit.llama.Llama
import dev.ffmpegkit.llama.LlamaConfig
import dev.ffmpegkit.llama.LlamaModel
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView

class MainActivity : Activity() {
    private lateinit var web: WebView
    private lateinit var progress: ProgressBar
    private var fileCallback: ValueCallback<Array<Uri>>? = null
    private var pendingWebPermission: PermissionRequest? = null
    private val localScope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    @Volatile private var localModel: LlamaModel? = null
    @Volatile private var modelBusy = false
    private val modelUrl = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
    private val modelFile: File by lazy { File(getExternalFilesDir("models"), "nexora-qwen-0.5b-q4km.gguf") }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Color.rgb(7, 17, 31)
        window.navigationBarColor = Color.rgb(7, 17, 31)
        buildUi()
        web.addJavascriptInterface(NexoraBridge(), "NexoraNative")
        web.loadUrl("file:///android_asset/index.html")
    }

    private fun buildUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(7, 17, 31))
        }
        val bar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = android.view.Gravity.CENTER_VERTICAL
            setPadding(14, 5, 14, 5)
        }
        val title = TextView(this).apply {
            text = "NEXORA AI"
            textSize = 17f
            setTextColor(Color.WHITE)
            letterSpacing = .12f
        }
        bar.addView(title, LinearLayout.LayoutParams(0, 46, 1f))
        val config = Button(this).apply {
            text = "Configurar"
            isAllCaps = false
            setOnClickListener { web.evaluateJavascript("show('settings')", null) }
        }
        bar.addView(config)
        root.addView(bar)
        progress = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            visibility = View.GONE
        }
        root.addView(progress, LinearLayout.LayoutParams(-1, 3))
        web = WebView(this).apply {
            setBackgroundColor(Color.rgb(7, 17, 31))
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = true
            settings.allowContentAccess = false
            settings.allowFileAccessFromFileURLs = false
            settings.allowUniversalAccessFromFileURLs = false
            settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW
            settings.javaScriptCanOpenWindowsAutomatically = false
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                    val uri = request?.url ?: return true
                    if (uri.scheme == "file" && uri.path?.contains("/android_asset/") == true) return false
                    if (uri.scheme == "https") startActivity(Intent(Intent.ACTION_VIEW, uri))
                    return true
                }
            }
            webChromeClient = object : WebChromeClient() {
                override fun onProgressChanged(view: WebView?, newProgress: Int) {
                    this@MainActivity.progress.progress = newProgress
                    this@MainActivity.progress.visibility = if (newProgress in 1..99) View.VISIBLE else View.GONE
                }
                override fun onPermissionRequest(request: PermissionRequest) {
                    runOnUiThread {
                        val audioOnly = request.resources.all { it == PermissionRequest.RESOURCE_AUDIO_CAPTURE }
                        if (!audioOnly) {
                            request.deny()
                            return@runOnUiThread
                        }
                        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                            request.grant(arrayOf(PermissionRequest.RESOURCE_AUDIO_CAPTURE))
                        } else {
                            pendingWebPermission?.deny()
                            pendingWebPermission = request
                            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), AUDIO_PERMISSION_REQUEST)
                        }
                    }
                }
                override fun onShowFileChooser(webView: WebView?, callback: ValueCallback<Array<Uri>>?, params: FileChooserParams?): Boolean {
                    fileCallback?.onReceiveValue(null)
                    fileCallback = callback
                    val intent = Intent(Intent.ACTION_GET_CONTENT).apply {
                        addCategory(Intent.CATEGORY_OPENABLE)
                        type = "image/*"
                    }
                    return try {
                        startActivityForResult(Intent.createChooser(intent, "Escolher imagem"), FILE_REQUEST)
                        true
                    } catch (_: Exception) {
                        fileCallback = null
                        false
                    }
                }
            }
        }
        root.addView(web, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
    }


    inner class NexoraBridge {
        @JavascriptInterface fun modelState(): String {
            return when {
                localModel != null -> "ready"
                modelBusy -> "working"
                modelFile.exists() && modelFile.length() > 300_000_000L -> "downloaded"
                else -> "missing"
            }
        }

        @JavascriptInterface fun downloadModel() {
            if (modelBusy || localModel != null) return
            modelBusy = true
            notifyModel("downloading", "Baixando o modelo local (aprox. 470 MiB). Mantenha o app aberto e use Wi-Fi.")
            localScope.launch {
                try {
                    withContext(Dispatchers.IO) {
                        val parent = modelFile.parentFile ?: throw IllegalStateException("Pasta privada do modelo indisponível")
                        if (!parent.exists() && !parent.mkdirs()) throw IllegalStateException("Não foi possível criar a pasta do modelo")
                        val temp = File(parent, modelFile.name + ".part")
                        val connection = (URL(modelUrl).openConnection() as HttpURLConnection).apply {
                            connectTimeout = 30000
                            readTimeout = 60000
                            instanceFollowRedirects = true
                            setRequestProperty("User-Agent", "NEXORA-AI-Android")
                        }
                        try {
                            connection.connect()
                            if (connection.responseCode !in 200..299) throw IllegalStateException("Download HTTP ${connection.responseCode}")
                            val total = connection.contentLengthLong
                            connection.inputStream.use { input ->
                                temp.outputStream().buffered().use { output ->
                                    val buffer = ByteArray(64 * 1024)
                                    var count: Int
                                    var received = 0L
                                    var lastPercent = -1
                                    while (input.read(buffer).also { count = it } != -1) {
                                        output.write(buffer, 0, count)
                                        received += count
                                        if (total > 0) {
                                            val percent = ((received * 100) / total).toInt()
                                            if (percent != lastPercent) {
                                                lastPercent = percent
                                                runOnUiThread { notifyModel("downloading", "Baixando o modelo local: $percent%") }
                                            }
                                        }
                                    }
                                }
                            }
                            if (temp.length() < 300_000_000L) throw IllegalStateException("Arquivo do modelo incompleto")
                            if (modelFile.exists()) modelFile.delete()
                            if (!temp.renameTo(modelFile)) throw IllegalStateException("Não foi possível finalizar o arquivo do modelo")
                        } finally {
                            connection.disconnect()
                            if (temp.exists()) temp.delete()
                        }
                    }
                    loadLocalModel()
                } catch (e: Exception) {
                    modelBusy = false
                    notifyModel("error", e.message ?: "Falha ao baixar ou carregar o modelo")
                }
            }
        }

        @JavascriptInterface fun sendLocalMessage(prompt: String, history: String) {
            if (modelBusy) {
                notifyAnswer("A IA local ainda está carregando. Aguarde alguns instantes.", true)
                return
            }
            localScope.launch {
                try {
                    val active = localModel ?: loadLocalModel()
                    val system = "Você é a NEXORA, uma assistente de IA independente que funciona localmente no aparelho. Responda em português brasileiro, com clareza, honestidade e utilidade. Não invente pesquisas, ações executadas, fatos ou capacidades. Se não souber, diga. Use o contexto recente apenas como histórico da conversa.\n\nHistórico recente:\n" + history
                    val result = withContext(Dispatchers.IO) {
                        Llama.complete(active, prompt.take(5000), systemPrompt = system.take(7000), maxTokens = 220)
                    }
                    notifyAnswer(result.text.ifBlank { "O modelo não gerou uma resposta. Tente reformular a mensagem." }, false)
                } catch (e: Exception) {
                    notifyAnswer("A IA local encontrou um erro: ${e.message ?: "falha de inferência"}", true)
                }
            }
        }
    }

    private suspend fun loadLocalModel(): LlamaModel {
        localModel?.let { return it }
        if (!modelFile.exists() || modelFile.length() < 300_000_000L) throw IllegalStateException("O modelo ainda não foi baixado. Abra Configurar e toque em Baixar e ativar IA local.")
        modelBusy = true
        notifyModel("loading", "Carregando o modelo no aparelho. Na primeira vez pode demorar um pouco.")
        return try {
            val loaded = withContext(Dispatchers.IO) {
                Llama.loadModel(
                    modelPath = modelFile.absolutePath,
                    config = LlamaConfig(contextSize = 2048, threads = Runtime.getRuntime().availableProcessors().coerceIn(2, 4))
                )
            }
            localModel = loaded
            modelBusy = false
            notifyModel("ready", "IA local pronta. As conversas podem funcionar sem servidor.")
            loaded
        } catch (e: Exception) {
            modelBusy = false
            notifyModel("error", e.message ?: "Não foi possível carregar o modelo")
            throw e
        }
    }

    private fun notifyModel(state: String, detail: String) {
        val script = "window.onNexoraModelState && window.onNexoraModelState(${JSONObject.quote(state)},${JSONObject.quote(detail)})"
        if (::web.isInitialized) runOnUiThread { web.evaluateJavascript(script, null) }
    }

    private fun notifyAnswer(answer: String, failed: Boolean) {
        val script = "window.onNexoraNativeAnswer && window.onNexoraNativeAnswer(${JSONObject.quote(answer)},$failed)"
        if (::web.isInitialized) runOnUiThread { web.evaluateJavascript(script, null) }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == AUDIO_PERMISSION_REQUEST) {
            val request = pendingWebPermission
            pendingWebPermission = null
            if (request != null) {
                if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
                    request.grant(arrayOf(PermissionRequest.RESOURCE_AUDIO_CAPTURE))
                } else {
                    request.deny()
                }
            }
        }
    }

    @Deprecated("Deprecated in Android API, retained for broad device compatibility")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == FILE_REQUEST) {
            val result = if (resultCode == RESULT_OK && data?.data != null) arrayOf(data.data!!) else null
            fileCallback?.onReceiveValue(result)
            fileCallback = null
        }
    }

    override fun onBackPressed() {
        if (::web.isInitialized && web.canGoBack()) web.goBack() else super.onBackPressed()
    }

    override fun onDestroy() {
        localScope.cancel()
        localModel?.let { Llama.releaseModel(it) }
        localModel = null
        if (::web.isInitialized) web.destroy()
        super.onDestroy()
    }

    companion object { private const val FILE_REQUEST = 7104; private const val AUDIO_PERMISSION_REQUEST = 7105 }
}