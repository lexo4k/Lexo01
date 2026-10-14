package com.androidresourcelab

import android.app.Activity
import android.app.AlertDialog
import android.os.Bundle
import android.graphics.Color
import android.graphics.Typeface
import android.text.InputType
import android.view.Gravity
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/** Educational sandbox: only values owned by this Activity can be searched or edited. */
class MemoryLabActivity : Activity() {
    private data class Cell(val id: Int, val name: String, val type: String, var value: String)

    private val initialCells = listOf(
        Cell(1001, "Inteiro de teste A", "INT", "120"),
        Cell(1002, "Inteiro de teste B", "INT", "250"),
        Cell(1003, "Inteiro de teste C", "INT", "120"),
        Cell(2001, "Decimal de teste", "FLOAT", "1.25"),
        Cell(3001, "Flag de teste", "BOOL", "false"),
        Cell(4001, "Contador local", "LONG", "4096")
    )
    private val cells = initialCells.map { it.copy() }.toMutableList()
    private lateinit var results: LinearLayout
    private lateinit var queryInput: EditText
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        renderResults(cells)
    }

    private fun buildUi() {
        val outer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(18), dp(18), dp(22))
            setBackgroundColor(Color.rgb(9, 15, 29))
        }
        val scroll = ScrollView(this)
        val body = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        body.addView(label("RESOURCE LAB • MEMORY LAB", 12f, Color.rgb(87, 213, 190), true))
        body.addView(label("Busca de valores local", 27f, Color.WHITE, true).apply {
            setPadding(0, dp(8), 0, dp(8))
        })
        body.addView(label(
            "Laboratório funcional para testar busca e edição de valores mantidos pelo próprio app. Não lê memória de jogos nem de outros aplicativos.",
            14f, Color.rgb(183, 194, 213), false
        ).apply { setPadding(0, 0, 0, dp(16)) })

        queryInput = EditText(this).apply {
            hint = "Valor para buscar (ex.: 120)"
            setSingleLine(true)
            inputType = InputType.TYPE_CLASS_TEXT
            setTextColor(Color.WHITE)
            setHintTextColor(Color.rgb(135, 151, 177))
            setPadding(dp(12), dp(8), dp(12), dp(8))
            setBackgroundColor(Color.rgb(20, 30, 49))
        }
        body.addView(queryInput, LinearLayout.LayoutParams(-1, dp(52)).apply {
            bottomMargin = dp(8)
        })

        val actions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        val search = Button(this).apply {
            text = "BUSCAR"
            isAllCaps = false
            setOnClickListener { searchValues() }
        }
        val reset = Button(this).apply {
            text = "REINICIAR"
            isAllCaps = false
            setOnClickListener {
                cells.clear()
                cells.addAll(initialCells.map { it.copy() })
                queryInput.setText("")
                renderResults(cells)
                status.text = "Valores locais restaurados."
            }
        }
        actions.addView(search, LinearLayout.LayoutParams(0, dp(48), 1f))
        actions.addView(reset, LinearLayout.LayoutParams(0, dp(48), 1f))
        body.addView(actions)

        status = label("Pronto para buscar nos valores de teste.", 12f, Color.rgb(183, 194, 213), false)
        body.addView(status.apply { setPadding(0, dp(10), 0, dp(10)) })
        body.addView(label("RESULTADOS", 12f, Color.rgb(87, 213, 190), true).apply {
            setPadding(0, dp(8), 0, dp(8))
        })
        results = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        body.addView(results)

        val back = Button(this).apply {
            text = "VOLTAR AO PAINEL"
            isAllCaps = false
            setOnClickListener { finish() }
        }
        body.addView(back, LinearLayout.LayoutParams(-1, dp(48)).apply {
            topMargin = dp(12)
        })
        scroll.addView(body)
        outer.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(outer)
    }

    private fun searchValues() {
        val query = queryInput.text.toString().trim()
        val found = if (query.isEmpty()) cells else cells.filter {
            it.value.contains(query, ignoreCase = true) || it.name.contains(query, ignoreCase = true)
        }
        renderResults(found)
        status.text = "${found.size} resultado(s) • busca somente nos valores locais deste app."
    }

    private fun renderResults(items: List<Cell>) {
        results.removeAllViews()
        if (items.isEmpty()) {
            results.addView(label("Nenhum valor local corresponde à busca.", 14f, Color.WHITE, false))
            return
        }
        items.forEach { cell ->
            val card = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(14), dp(12), dp(14), dp(12))
                setBackgroundColor(Color.rgb(20, 30, 49))
            }
            card.addView(label(cell.name, 15f, Color.WHITE, true))
            card.addView(label(
                "ID local: ${cell.id}  •  Tipo: ${cell.type}\nValor atual: ${cell.value}",
                13f, Color.rgb(183, 194, 213), false
            ).apply { setPadding(0, dp(6), 0, dp(8)) })
            val edit = Button(this).apply {
                text = "EDITAR VALOR DE TESTE"
                isAllCaps = false
                setOnClickListener { editCell(cell) }
            }
            card.addView(edit)
            results.addView(card, LinearLayout.LayoutParams(-1, -2).apply {
                bottomMargin = dp(10)
            })
        }
    }

    private fun editCell(cell: Cell) {
        val input = EditText(this).apply {
            setSingleLine(true)
            setText(cell.value)
            inputType = InputType.TYPE_CLASS_TEXT
        }
        AlertDialog.Builder(this)
            .setTitle("Editar valor local")
            .setMessage("Este teste altera apenas o valor mantido dentro do Android Resource Lab.")
            .setView(input)
            .setNegativeButton("Cancelar", null)
            .setPositiveButton("Salvar") { _, _ ->
                val next = input.text.toString().trim()
                if (next.isNotEmpty()) {
                    cell.value = next
                    val query = queryInput.text.toString().trim()
                    val visible = if (query.isEmpty()) cells else cells.filter {
                        it.value.contains(query, ignoreCase = true) || it.name.contains(query, ignoreCase = true)
                    }
                    renderResults(visible)
                    status.text = "Valor local atualizado. Nenhum outro app foi alterado."
                }
            }
            .show()
    }

    private fun label(text: String, size: Float, color: Int, bold: Boolean) =
        TextView(this).apply {
            this.text = text
            textSize = size
            setTextColor(color)
            typeface = if (bold) Typeface.DEFAULT_BOLD else Typeface.DEFAULT
            gravity = Gravity.START
            setLineSpacing(dp(3).toFloat(), 1f)
        }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
