package com.lexo.lumen

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.view.WindowManager
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast

class MainActivity : Activity() {
    private lateinit var web: WebView
    private lateinit var progress: ProgressBar
    private lateinit var serverLabel: TextView
    private var fileCallback: ValueCallback<Array<Uri>>? = null
    private val prefs by lazy { getSharedPreferences("lumen_config", MODE_PRIVATE) }
    private val serverUrl: String get() = prefs.getString("server_url", "") ?: ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Color.rgb(8, 13, 25)
        window.navigationBarColor = Color.rgb(8, 13, 25)
        buildUi()
        if (serverUrl.isBlank()) showServerDialog() else loadServer()
    }

    private fun buildUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(8, 13, 25))
        }
        val bar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = android.view.Gravity.CENTER_VERTICAL
            setPadding(14, 8, 14, 8)
        }
        val title = TextView(this).apply {
            text = "LÚMEN AI"
            textSize = 18f
            setTextColor(Color.WHITE)
            letterSpacing = .12f
        }
        bar.addView(title, LinearLayout.LayoutParams(0, 48, 1f))
        val config = Button(this).apply {
            text = "Servidor"
            isAllCaps = false
            setOnClickListener { showServerDialog() }
        }
        bar.addView(config)
        root.addView(bar)
        progress = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            visibility = View.GONE
        }
        root.addView(progress, LinearLayout.LayoutParams(-1, 3))
        serverLabel = TextView(this).apply {
            textSize = 11f
            setTextColor(Color.LTGRAY)
            setPadding(14, 3, 14, 5)
        }
        root.addView(serverLabel)
        web = WebView(this).apply {
            setBackgroundColor(Color.rgb(8, 13, 25))
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = false
            settings.allowContentAccess = true
            settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW
            settings.javaScriptCanOpenWindowsAutomatically = false
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                    val uri = request?.url ?: return false
                    val currentHost = Uri.parse(serverUrl).host
                    if (uri.scheme == "https" && uri.host == currentHost) return false
                    if (uri.scheme == "https") {
                        startActivity(Intent(Intent.ACTION_VIEW, uri))
                        return true
                    }
                    return true
                }
            }
            webChromeClient = object : WebChromeClient() {
                override fun onProgressChanged(view: WebView?, newProgress: Int) {
                    this@MainActivity.progress.progress = newProgress
                    this@MainActivity.progress.visibility = if (newProgress in 1..99) View.VISIBLE else View.GONE
                }
                override fun onShowFileChooser(
                    webView: WebView?,
                    callback: ValueCallback<Array<Uri>>?,
                    params: FileChooserParams?
                ): Boolean {
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

    private fun showServerDialog() {
        val input = EditText(this).apply {
            hint = "https://seu-servico.onrender.com"
            setSingleLine(true)
            setText(serverUrl)
            setSelection(text.length)
        }
        AlertDialog.Builder(this)
            .setTitle("Conectar ao servidor LÚMEN")
            .setMessage("Informe o endereço HTTPS onde o LÚMEN AI CORE foi publicado. O endereço fica salvo neste aparelho.")
            .setView(input)
            .setNegativeButton("Cancelar", null)
            .setPositiveButton("Salvar e conectar") { _, _ ->
                val raw = input.text.toString().trim().trimEnd('/')
                val uri = runCatching { Uri.parse(raw) }.getOrNull()
                if (uri == null || uri.scheme != "https" || uri.host.isNullOrBlank()) {
                    Toast.makeText(this, "Use um endereço HTTPS válido.", Toast.LENGTH_LONG).show()
                } else {
                    prefs.edit().putString("server_url", raw).apply()
                    loadServer()
                }
            }
            .show()
    }

    private fun loadServer() {
        if (!::web.isInitialized || serverUrl.isBlank()) return
        serverLabel.text = serverUrl
        web.loadUrl(serverUrl)
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
        if (::web.isInitialized) web.destroy()
        super.onDestroy()
    }

    companion object {
        private const val FILE_REQUEST = 7104
    }
}
