package com.memdroid;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.view.Gravity;
import android.widget.*;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class MainActivity extends Activity {
    static final class Cell {
        final int id;
        int value;
        Cell(int id, int value) { this.id = id; this.value = value; }
    }

    private final List<Cell> cells = new ArrayList<>();
    private final List<Cell> hits = new ArrayList<>();
    private LinearLayout root, results;
    private EditText searchBox, newValueBox;
    private TextView status;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        buildUi();
        resetLab();
    }

    private int dp(int v) {
        return (int)(v * getResources().getDisplayMetrics().density + 0.5f);
    }

    private TextView text(String s, int size) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(size);
        t.setTextColor(Color.rgb(28, 35, 48));
        return t;
    }

    private Button button(String label, Runnable action) {
        Button b = new Button(this);
        b.setText(label);
        b.setOnClickListener(v -> action.run());
        return b;
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(16), dp(18), dp(24));
        scroll.addView(root);
        setContentView(scroll);

        TextView title = text("MemDroid", 28);
        title.setGravity(Gravity.CENTER_VERTICAL);
        title.setTypeface(null, 1);
        root.addView(title);

        TextView subtitle = text("Scanner numérico • laboratório sem root", 14);
        subtitle.setTextColor(Color.rgb(85, 98, 115));
        root.addView(subtitle);

        TextView notice = text("MODO DE TESTE: os valores abaixo pertencem ao próprio MemDroid. Este protótipo não lê a memória de outros apps.", 14);
        notice.setPadding(dp(12), dp(12), dp(12), dp(12));
        notice.setBackgroundColor(Color.rgb(232, 240, 254));
        notice.setTextColor(Color.rgb(28, 57, 105));
        LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(-1, -2);
        np.topMargin = dp(14);
        root.addView(notice, np);

        root.addView(button("Carregar laboratório", this::resetLab));
        root.addView(button("Restaurar laboratório", this::resetLab));

        searchBox = new EditText(this);
        searchBox.setSingleLine(true);
        searchBox.setInputType(android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_FLAG_SIGNED);
        searchBox.setHint("Valor inteiro para buscar");
        root.addView(searchBox);

        newValueBox = new EditText(this);
        newValueBox.setSingleLine(true);
        newValueBox.setInputType(android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_FLAG_SIGNED);
        newValueBox.setHint("Novo valor para editar");
        root.addView(newValueBox);

        root.addView(button("Buscar valor", this::search));
        root.addView(button("Refinar busca", this::refine));
        root.addView(button("Aplicar novo valor aos resultados", this::writeHits));

        status = text("", 14);
        status.setPadding(0, dp(10), 0, dp(10));
        root.addView(status);

        TextView header = text("Valores do laboratório", 18);
        header.setTypeface(null, 1);
        root.addView(header);

        results = new LinearLayout(this);
        results.setOrientation(LinearLayout.VERTICAL);
        root.addView(results);
    }

    private void resetLab() {
        cells.clear();
        hits.clear();
        int[] values = {100, 250, 100, 75, 999, 250, 40, 100, 500, 75, 12, 250};
        for (int i = 0; i < values.length; i++) cells.add(new Cell(i + 1, values[i]));
        status.setText("Laboratório pronto: " + cells.size() + " valores de teste.");
        render(cells);
    }

    private Integer parseSearch() {
        try {
            return Integer.parseInt(searchBox.getText().toString().trim());
        } catch (Exception e) {
            status.setText("Digite um número inteiro válido.");
            return null;
        }
    }

    private void search() {
        Integer value = parseSearch();
        if (value == null) return;
        hits.clear();
        for (Cell c : cells) if (c.value == value) hits.add(c);
        status.setText(hits.size() + " resultado(s) para " + value + ". Você pode editar ou refinar.");
        render(hits);
    }

    private void refine() {
        Integer value = parseSearch();
        if (value == null) return;
        if (hits.isEmpty()) {
            status.setText("Faça uma busca primeiro. Se não houver resultados, busque outro valor.");
            return;
        }
        List<Cell> keep = new ArrayList<>();
        for (Cell c : hits) if (c.value == value) keep.add(c);
        hits.clear();
        hits.addAll(keep);
        status.setText("Busca refinada: " + hits.size() + " resultado(s) restantes.");
        render(hits);
    }

    private void writeHits() {
        if (hits.isEmpty()) {
            status.setText("Nenhum resultado encontrado. Faça uma busca primeiro.");
            return;
        }
        final int value;
        try {
            value = Integer.parseInt(newValueBox.getText().toString().trim());
        } catch (Exception e) {
            status.setText("Digite um novo valor inteiro.");
            return;
        }
        for (Cell c : hits) c.value = value;
        status.setText("Alterados " + hits.size() + " valor(es) no laboratório para " + value + ".");
        render(hits);
    }

    private void render(List<Cell> list) {
        results.removeAllViews();
        if (list.isEmpty()) {
            TextView empty = text("Nenhum resultado para mostrar.", 14);
            empty.setPadding(0, dp(8), 0, dp(8));
            results.addView(empty);
            return;
        }
        for (Cell c : list) {
            TextView row = text(String.format(Locale.US, "ID %02d      valor: %d", c.id, c.value), 16);
            row.setPadding(dp(12), dp(12), dp(12), dp(12));
            row.setBackgroundColor(c.id % 2 == 0 ? Color.rgb(245, 247, 250) : Color.WHITE);
            results.addView(row);
        }
    }
}
