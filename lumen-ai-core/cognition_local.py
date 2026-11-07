"""Planejador local determinístico da NEXORA.

Não é um modelo de linguagem nem simula inteligência generativa. Organiza
objetivos em passos simples sem depender de API externa ou rede.
"""
from __future__ import annotations
import re
from typing import Any

ACTION_HINTS = (
    ("criar", "Definir o resultado e construir uma primeira versão verificável."),
    ("corrigir", "Reproduzir o problema, localizar a causa e corrigir a origem."),
    ("aprender", "Reunir material permitido, estudar e validar o que foi aprendido."),
    ("pesquisar", "Consultar fontes confiáveis e registrar as evidências."),
    ("organizar", "Separar os itens por prioridade, dependências e prazo."),
    ("testar", "Executar testes reproduzíveis e registrar os resultados."),
    ("treinar", "Verificar dados, separar validação e acompanhar métricas."),
    ("integrar", "Definir interfaces, conectar componentes e testar o fluxo completo."),
    ("publicar", "Revisar segurança, configuração e critérios de liberação."),
)

def plan_locally(goal: str, memories: list[str] | None = None,
                 knowledge: list[str] | None = None) -> dict[str, Any]:
    """Gera um plano heurístico auditável; não chama ferramentas nem altera dados."""
    clean = re.sub(r"\s+", " ", goal).strip()
    if not clean:
        raise ValueError("O objetivo não pode ficar vazio.")
    lower = clean.casefold()
    selected = []
    for keyword, action in ACTION_HINTS:
        if keyword in lower:
            selected.append(action)
    if not selected:
        selected = [
            "Especificar o resultado esperado e como será verificado.",
            "Identificar recursos, limitações e dependências.",
            "Executar uma etapa pequena e segura.",
            "Avaliar o resultado e ajustar o plano."
        ]
    steps = [{"step": i + 1, "action": action,
              "purpose": "Transformar o objetivo em progresso verificável."}
             for i, action in enumerate(selected[:6])]
    context_count = len(memories or []) + len(knowledge or [])
    return {
        "understanding": clean[:500],
        "symbolic_analysis": inspect_symbols(clean),
        "goal": clean[:1000],
        "assumptions": ["O pedido descreve o objetivo, mas pode não conter todos os requisitos."],
        "plan": steps,
        "decision": steps[0]["action"],
        "confidence": 0.25,
        "uncertainties": [
            "O planejador local usa regras e não compreende linguagem como um modelo treinado.",
            "Os detalhes técnicos e critérios de sucesso ainda precisam ser verificados."
        ],
        "approval_required": True,
        "next_action": "Confirmar os critérios de sucesso antes de qualquer ação externa.",
        "memory_context_items": context_count,
        "evaluation": {
            "quality": "revisar",
            "issues": ["Plano heurístico; não foi avaliado por um modelo de linguagem."],
            "improvements": ["Adicionar requisitos mensuráveis e validar cada etapa."]
        },
        "execution_status": "not_executed",
        "engine": "nexora-local-planner-v1",
        "warning": "Modo local independente para planejamento básico, não equivale a uma IA conversacional avançada."
    }
