package com.copiloto.app

import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.IBinder
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.webkit.WebView
import android.widget.FrameLayout
import android.widget.TextView
import kotlin.math.abs

/**
 * Servicio que dibuja la BURBUJA flotante encima de otras apps.
 * - Burbuja (✦): se arrastra; al tocarla se abre el panel.
 * - Panel: WebView con Copiloto; la barra de arriba se arrastra para mover,
 *   y tocar la parte derecha ("✕ cerrar") lo vuelve a la burbuja.
 */
class OverlayService : Service() {

    private lateinit var wm: WindowManager
    private var bubble: View? = null
    private var panel: View? = null
    private lateinit var bubbleParams: WindowManager.LayoutParams
    private lateinit var panelParams: WindowManager.LayoutParams

    private val overlayType =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        else
            @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        startAsForeground()
        wm = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        showBubble()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    private fun startAsForeground() {
        val chId = "copiloto_overlay"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(chId, "Copiloto flotante", NotificationManager.IMPORTANCE_MIN)
            (getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager).createNotificationChannel(ch)
        }
        val n = Notification.Builder(this, chId)
            .setContentTitle("Copiloto activo")
            .setContentText("Toca la burbuja ✦ para abrir")
            .setSmallIcon(R.drawable.ic_launcher)
            .build()
        startForeground(1, n)
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    @SuppressLint("ClickableViewAccessibility")
    private fun showBubble() {
        val tv = TextView(this)
        tv.text = "✦"
        tv.textSize = 24f
        tv.setTextColor(Color.WHITE)
        tv.gravity = Gravity.CENTER
        val bg = GradientDrawable()
        bg.shape = GradientDrawable.OVAL
        bg.colors = intArrayOf(Color.parseColor("#6C8CFF"), Color.parseColor("#9B6CFF"))
        tv.background = bg

        val size = dp(56)
        val container = FrameLayout(this)
        container.addView(tv, FrameLayout.LayoutParams(size, size))

        bubbleParams = WindowManager.LayoutParams(
            size, size, overlayType,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        )
        bubbleParams.gravity = Gravity.TOP or Gravity.START
        bubbleParams.x = dp(16)
        bubbleParams.y = dp(120)

        var downX = 0f; var downY = 0f; var px = 0; var py = 0; var moved = false
        container.setOnTouchListener { _, e ->
            when (e.action) {
                MotionEvent.ACTION_DOWN -> {
                    downX = e.rawX; downY = e.rawY; px = bubbleParams.x; py = bubbleParams.y; moved = false; true
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = (e.rawX - downX).toInt(); val dy = (e.rawY - downY).toInt()
                    if (abs(dx) > 10 || abs(dy) > 10) moved = true
                    bubbleParams.x = px + dx; bubbleParams.y = py + dy
                    wm.updateViewLayout(container, bubbleParams); true
                }
                MotionEvent.ACTION_UP -> { if (!moved) openPanel(); true }
                else -> false
            }
        }
        bubble = container
        wm.addView(container, bubbleParams)
    }

    @SuppressLint("SetJavaScriptEnabled", "ClickableViewAccessibility")
    private fun openPanel() {
        bubble?.let { runCatching { wm.removeView(it) }; bubble = null }

        val root = FrameLayout(this)
        root.setBackgroundColor(Color.parseColor("#F00B0F1A"))

        // Barra superior: título (se arrastra) + botón cerrar a la derecha.
        val bar = android.widget.LinearLayout(this)
        bar.orientation = android.widget.LinearLayout.HORIZONTAL
        bar.gravity = Gravity.CENTER_VERTICAL

        val title = TextView(this)
        title.text = "✦ Copiloto"
        title.setTextColor(Color.WHITE)
        title.textSize = 14f
        title.setPadding(dp(14), dp(12), dp(10), dp(12))
        val titleLp = android.widget.LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        bar.addView(title, titleLp)

        val closeBtn = TextView(this)
        closeBtn.text = "✕"
        closeBtn.setTextColor(Color.WHITE)
        closeBtn.textSize = 18f
        closeBtn.gravity = Gravity.CENTER
        closeBtn.setPadding(dp(18), dp(12), dp(18), dp(12))
        bar.addView(closeBtn, android.widget.LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        closeBtn.setOnClickListener { closePanel() }

        root.addView(
            bar,
            FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        )

        val web = WebView(this)
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.loadUrl("file:///android_asset/index.html")
        val wlp = FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT
        )
        wlp.topMargin = dp(48)
        root.addView(web, wlp)

        panelParams = WindowManager.LayoutParams(
            dp(340), dp(560), overlayType,
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT
        )
        panelParams.gravity = Gravity.TOP or Gravity.START
        panelParams.x = dp(16); panelParams.y = dp(80)

        var downX = 0f; var downY = 0f; var px = 0; var py = 0
        title.setOnTouchListener { _, e ->
            when (e.action) {
                MotionEvent.ACTION_DOWN -> {
                    downX = e.rawX; downY = e.rawY; px = panelParams.x; py = panelParams.y; true
                }
                MotionEvent.ACTION_MOVE -> {
                    panelParams.x = px + (e.rawX - downX).toInt()
                    panelParams.y = py + (e.rawY - downY).toInt()
                    wm.updateViewLayout(root, panelParams); true
                }
                else -> false
            }
        }

        panel = root
        wm.addView(root, panelParams)
    }

    private fun closePanel() {
        panel?.let { runCatching { wm.removeView(it) }; panel = null }
        showBubble()
    }

    override fun onDestroy() {
        super.onDestroy()
        bubble?.let { runCatching { wm.removeView(it) } }
        panel?.let { runCatching { wm.removeView(it) } }
    }
}
