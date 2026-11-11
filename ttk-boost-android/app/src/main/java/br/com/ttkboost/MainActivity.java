package br.com.ttkboost;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.provider.Settings;
import android.graphics.Color;
import android.graphics.Typeface;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class MainActivity extends Activity {
    private LinearLayout root;
    private TextView status, detectedAt, note;
    private final BroadcastReceiver receiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) { refresh(); }
    };
    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        buildUi();
        registerReceiver(receiver, new IntentFilter("br.com.ttkboost.UPLOAD_DETECTED"), Context.RECEIVER_NOT_EXPORTED);
        refresh();
    }
    private int dp(int v) { return (int)(v * getResources().getDisplayMetrics().density); }
    private TextView text(String value, int size, int color) {
        TextView t = new TextView(this); t.setText(value); t.setTextSize(size); t.setTextColor(color); return t;
    }
    private void buildUi() {
        root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setPadding(dp(22), dp(28), dp(22), dp(20)); root.setBackgroundColor(Color.rgb(9,9,20));
        setContentView(root);
        TextView brand = text("TTK BOOST", 27, Color.WHITE); brand.setTypeface(null, Typeface.BOLD); root.addView(brand);
        TextView sub = text("INTELIGÊNCIA DE PUBLICAÇÃO", 11, Color.rgb(167,139,250)); sub.setPadding(0,dp(4),0,dp(22)); root.addView(sub);
        TextView hero = text("Seu vídeo.\nMonitorado desde o primeiro sinal.", 25, Color.WHITE); hero.setTypeface(null,Typeface.BOLD); root.addView(hero);
        TextView desc = text("O app observa notificações do TikTok para reconhecer um possível aviso de publicação. Não altera nem força a distribuição do TikTok.", 14, Color.rgb(180,180,198)); desc.setPadding(0,dp(12),0,dp(20)); root.addView(desc);
        LinearLayout panel = new LinearLayout(this); panel.setOrientation(LinearLayout.VERTICAL); panel.setPadding(dp(16),dp(16),dp(16),dp(16)); panel.setBackgroundColor(Color.rgb(25,24,43));
        status = text("MONITOR AGUARDANDO", 15, Color.rgb(196,181,253)); status.setTypeface(null,Typeface.BOLD); panel.addView(status);
        detectedAt = text("Nenhuma publicação detectada ainda.", 14, Color.WHITE); detectedAt.setPadding(0,dp(10),0,dp(4)); panel.addView(detectedAt);
        note = text("Os resultados de visualizações e retenção não são fornecidos automaticamente por uma API pública para qualquer conta. Este painel não inventa métricas.", 12, Color.rgb(180,180,198)); note.setPadding(0,dp(10),0,0); panel.addView(note);
        LinearLayout.LayoutParams pp = new LinearLayout.LayoutParams(-1,-2); pp.bottomMargin=dp(18); root.addView(panel,pp);
        Button enable = new Button(this); enable.setText("ATIVAR MONITORAMENTO"); enable.setOnClickListener(v -> startActivity(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))); root.addView(enable,new LinearLayout.LayoutParams(-1,-2));
        Button refresh = new Button(this); refresh.setText("ATUALIZAR STATUS"); refresh.setOnClickListener(v -> refresh()); root.addView(refresh,new LinearLayout.LayoutParams(-1,-2));
        TextView foot = text("Privacidade: o monitor filtra notificações do TikTok no próprio aparelho. Não lê mensagens privadas nem interage com sua conta.", 11, Color.rgb(130,130,150)); foot.setPadding(0,dp(20),0,0); root.addView(foot);
    }
    private void refresh() {
        boolean enabled = false;
        String listeners = android.provider.Settings.Secure.getString(getContentResolver(), "enabled_notification_listeners");
        if (listeners != null && listeners.contains(getPackageName())) enabled = true;
        long ts = getSharedPreferences("ttkboost",MODE_PRIVATE).getLong("last_detected",0);
        if (!enabled) { status.setText("MONITOR DESATIVADO"); detectedAt.setText("Ative a permissão de acesso às notificações para detectar avisos do TikTok."); }
        else if (ts > 0) { status.setText("SINAL DE PUBLICAÇÃO DETECTADO"); detectedAt.setText("Notificação recebida em " + new SimpleDateFormat("dd/MM/yyyy 'às' HH:mm", Locale.getDefault()).format(new Date(ts)) + ". Confirme no TikTok se o vídeo foi publicado."); }
        else { status.setText("MONITOR ATIVO • AGUARDANDO"); detectedAt.setText("Aguardando uma notificação do TikTok que indique publicação."); }
    }
    @Override protected void onResume() { super.onResume(); if (status != null) refresh(); }
    @Override protected void onDestroy() { super.onDestroy(); try { unregisterReceiver(receiver); } catch (Exception ignored) {} }
}
