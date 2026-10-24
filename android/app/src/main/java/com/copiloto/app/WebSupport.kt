package com.copiloto.app

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.webkit.JavascriptInterface
import android.webkit.WebView

/**
 * Puentes entre la web (Copiloto) y Android:
 *  - AndroidStore: guarda claves/datos en SharedPreferences (a prueba de fallos).
 *  - AndroidSpeech: micrófono nativo que detecta la pausa y devuelve el texto.
 */
object WebSupport {
    fun configure(ctx: Context, web: WebView) {
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        @Suppress("DEPRECATION")
        web.settings.databaseEnabled = true
        web.settings.allowFileAccess = true
        web.addJavascriptInterface(Store(ctx.applicationContext), "AndroidStore")
        web.addJavascriptInterface(Speech(ctx.applicationContext, web), "AndroidSpeech")
    }
}

/** Almacenamiento persistente real (SharedPreferences). */
class Store(ctx: Context) {
    private val p = ctx.getSharedPreferences("copiloto", Context.MODE_PRIVATE)

    @JavascriptInterface
    fun getItem(key: String): String = p.getString(key, "") ?: ""

    @JavascriptInterface
    fun setItem(key: String, value: String) {
        p.edit().putString(key, value).apply()
    }

    @JavascriptInterface
    fun removeItem(key: String) {
        p.edit().remove(key).apply()
    }
}

/** Micrófono nativo con SpeechRecognizer (es-ES). */
class Speech(private val ctx: Context, private val web: WebView) {
    private val handler = Handler(Looper.getMainLooper())

    @JavascriptInterface
    fun start() {
        handler.post { startRecognition() }
    }

    private fun startRecognition() {
        if (!SpeechRecognizer.isRecognitionAvailable(ctx)) {
            callback("", "no-disponible")
            return
        }
        val sr = SpeechRecognizer.createSpeechRecognizer(ctx)
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE, "es-ES")
            .putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)

        sr.setRecognitionListener(object : RecognitionListener {
            override fun onResults(results: Bundle) {
                val txt = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull() ?: ""
                callback(txt, "final")
                sr.destroy()
            }
            override fun onPartialResults(partial: Bundle) {
                val txt = partial.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull() ?: ""
                if (txt.isNotEmpty()) callback(txt, "partial")
            }
            override fun onError(error: Int) {
                callback("", "error")
                sr.destroy()
            }
            override fun onReadyForSpeech(params: Bundle?) {}
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rmsdB: Float) {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() {}
            override fun onEvent(eventType: Int, params: Bundle?) {}
        })
        sr.startListening(intent)
    }

    private fun callback(text: String, state: String) {
        val esc = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
        handler.post {
            web.evaluateJavascript("window.copilotoVoice && window.copilotoVoice('$esc','$state')", null)
        }
    }
}
