package br.com.ttkboost;

import android.app.Notification;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

public class TikTokNotificationListener extends NotificationListenerService {
    @Override public void onNotificationPosted(StatusBarNotification sbn) {
        String pkg = sbn.getPackageName();
        if (!pkg.equals("com.zhiliaoapp.musically") && !pkg.equals("com.ss.android.ugc.trill")) return;
        Notification n = sbn.getNotification();
        if (n == null || n.extras == null) return;
        CharSequence title = n.extras.getCharSequence(Notification.EXTRA_TITLE);
        CharSequence text = n.extras.getCharSequence(Notification.EXTRA_TEXT);
        CharSequence big = n.extras.getCharSequence(Notification.EXTRA_BIG_TEXT);
        String content = ((title == null ? "" : title.toString()) + " " + (text == null ? "" : text.toString()) + " " + (big == null ? "" : big.toString())).toLowerCase(java.util.Locale.ROOT);
        boolean uploadSignal = content.contains("posted") || content.contains("published") || content.contains("publicado") || content.contains("publicada") || content.contains("foi publicado") || content.contains("video is live") || content.contains("vídeo foi");
        if (uploadSignal) {
            getSharedPreferences("ttkboost", MODE_PRIVATE).edit().putLong("last_detected", System.currentTimeMillis()).putString("last_notice", title == null ? "Notificação de publicação do TikTok" : title.toString()).apply();
            android.content.Intent intent = new android.content.Intent("br.com.ttkboost.UPLOAD_DETECTED");
            intent.setPackage(getPackageName());
            sendBroadcast(intent);
        }
    }
}
