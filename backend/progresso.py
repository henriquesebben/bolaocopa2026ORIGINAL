"""
Progressão do torneio: classificação de grupos e preenchimento automático
dos confrontos do mata-mata (32-avos → Final).
"""

from typing import Optional
from .jogos import JOGOS, JOGOS_POR_ID, TIMES_POR_GRUPO
from . import models


# ── Propagação de vencedor dentro do mata-mata ────────────────────────────────

def propagar_progressao(
    jogo_id: str,
    gols_casa: int,
    gols_fora: int,
    avanca: Optional[str],
    db,
) -> None:
    """Após salvar resultado de mata-mata, atualiza os times dos próximos confrontos."""
    jogo_meta = JOGOS_POR_ID.get(jogo_id)
    if not jogo_meta or not jogo_meta["eh_mata_mata"]:
        return

    if gols_casa > gols_fora:
        slot_vencedor, slot_perdedor = "casa", "fora"
    elif gols_fora > gols_casa:
        slot_vencedor, slot_perdedor = "fora", "casa"
    else:
        slot_vencedor = avanca
        slot_perdedor = "fora" if avanca == "casa" else "casa"

    if not slot_vencedor:
        return

    nome_real = db.query(models.JogoNomeReal).filter(models.JogoNomeReal.jogo_id == jogo_id).first()
    if slot_vencedor == "casa":
        nome_vencedor = (nome_real.casa_real if nome_real and nome_real.casa_real else None) or jogo_meta["casa"]
        nome_perdedor = (nome_real.fora_real if nome_real and nome_real.fora_real else None) or jogo_meta["fora"]
    else:
        nome_vencedor = (nome_real.fora_real if nome_real and nome_real.fora_real else None) or jogo_meta["fora"]
        nome_perdedor = (nome_real.casa_real if nome_real and nome_real.casa_real else None) or jogo_meta["casa"]

    tag_vencedor = f"Vencedor {jogo_id}"
    tag_perdedor = f"Perdedor {jogo_id}"

    for proximo in JOGOS:
        novo_casa = novo_fora = None
        if proximo["casa"] == tag_vencedor:
            novo_casa = nome_vencedor
        elif proximo["casa"] == tag_perdedor:
            novo_casa = nome_perdedor
        if proximo["fora"] == tag_vencedor:
            novo_fora = nome_vencedor
        elif proximo["fora"] == tag_perdedor:
            novo_fora = nome_perdedor

        if novo_casa is None and novo_fora is None:
            continue

        rec = db.query(models.JogoNomeReal).filter(models.JogoNomeReal.jogo_id == proximo["id"]).first()
        if rec:
            if novo_casa is not None:
                rec.casa_real = novo_casa
            if novo_fora is not None:
                rec.fora_real = novo_fora
        else:
            db.add(models.JogoNomeReal(
                jogo_id=proximo["id"],
                casa_real=novo_casa or proximo["casa"],
                fora_real=novo_fora or proximo["fora"],
            ))


# ── Classificação de grupos ───────────────────────────────────────────────────

def _calcular_classificacao(fase: str, times: list, resultados_dict: dict) -> list:
    """Retorna a lista de times do grupo ordenada: pontos, saldo, gols pró, nome."""
    tabela = {t: {"time": t, "PJ": 0, "PTS": 0, "GP": 0, "GC": 0} for t in times}

    for jogo in JOGOS:
        if jogo["fase"] != fase:
            continue
        r = resultados_dict.get(jogo["id"])
        if r is None:
            continue
        casa, fora = jogo["casa"], jogo["fora"]
        gc, gf = r.gols_casa, r.gols_fora
        tabela[casa]["PJ"] += 1; tabela[casa]["GP"] += gc; tabela[casa]["GC"] += gf
        tabela[fora]["PJ"]  += 1; tabela[fora]["GP"]  += gf; tabela[fora]["GC"] += gc
        if gc > gf:
            tabela[casa]["PTS"] += 3
        elif gf > gc:
            tabela[fora]["PTS"] += 3
        else:
            tabela[casa]["PTS"] += 1
            tabela[fora]["PTS"] += 1

    for t in tabela.values():
        t["SG"] = t["GP"] - t["GC"]

    return sorted(tabela.values(), key=lambda t: (-t["PTS"], -t["SG"], -t["GP"], t["time"]))


# ── Distribuição dos melhores 3ºs para os 8 slots do R32 ─────────────────────

# Grupos elegíveis para cada slot "Melhor 3º" do R32
_TERCEIRO_SLOTS: dict[str, set[str]] = {
    "R32-3":  {"A", "B", "C", "D", "F"},
    "R32-6":  {"C", "D", "F", "G", "H"},
    "R32-7":  {"C", "E", "F", "H", "I"},
    "R32-8":  {"E", "H", "I", "J", "K"},
    "R32-9":  {"A", "E", "H", "I", "J"},
    "R32-10": {"B", "E", "F", "I", "J"},
    "R32-11": {"E", "F", "G", "I", "J"},
    "R32-16": {"D", "E", "I", "J", "L"},
}


def _assign_terceiros(top8: list[dict]) -> dict[str, str]:
    """
    Distribui os 8 melhores 3ºs para os slots via backtracking (mais restrito primeiro).
    top8: [{"grupo": "A", "time": "Brasil", "stats": {...}}, ...] ordenado por ranking.
    Retorna {jogo_id_R32: nome_time}.
    """
    grupos_disp = {t["grupo"] for t in top8}

    # Ordena slots do mais restrito (menos grupos elegíveis disponíveis) para o menos
    slots_ordenados = sorted(
        _TERCEIRO_SLOTS.items(),
        key=lambda kv: len(kv[1] & grupos_disp),
    )

    result: dict[str, str] = {}
    usados: set[str] = set()

    def bt(idx: int) -> bool:
        if idx == len(slots_ordenados):
            return True
        slot_id, elegiveis = slots_ordenados[idx]
        disponiveis = (elegiveis & grupos_disp) - usados
        for t in top8:
            if t["grupo"] not in disponiveis:
                continue
            result[slot_id] = t["time"]
            usados.add(t["grupo"])
            if bt(idx + 1):
                return True
            del result[slot_id]
            usados.remove(t["grupo"])
        return False

    bt(0)
    return result


def _resolver_slot(slot_text: str, classificados: dict, terceiro_por_slot: dict, jogo_id: str) -> Optional[str]:
    """
    Converte texto de slot ("1º Grupo A", "2º Grupo B", "Melhor 3º (...)") em nome real.
    Retorna None se o dado ainda não está disponível.
    """
    if slot_text.startswith("1º Grupo "):      # "1º Grupo "
        letra = slot_text[9:]
        times = classificados.get(letra)
        return times[0] if times else None
    if slot_text.startswith("2º Grupo "):      # "2º Grupo "
        letra = slot_text[9:]
        times = classificados.get(letra)
        return times[1] if times and len(times) >= 2 else None
    if slot_text.startswith("Melhor 3º"):      # "Melhor 3º"
        return terceiro_por_slot.get(jogo_id)
    return None


# ── Função principal ──────────────────────────────────────────────────────────

def popular_confrontos_r32(db) -> dict:
    """
    Calcula classificados da fase de grupos e preenche JogoNomeReal para os 32-avos.
    Executa apenas para grupos que já têm todos os resultados.
    Os slots "Melhor 3º" só são resolvidos quando todos os 12 grupos terminam.
    Não comita — o chamador é responsável pelo commit.
    """
    todos_resultados = {r.jogo_id: r for r in db.query(models.Resultado).all()}

    # Classificação de cada grupo completo
    classificados: dict[str, list[str]] = {}   # letra → [1º, 2º, 3º, 4º]
    terceiros_info: list[dict] = []
    for letra, times in TIMES_POR_GRUPO.items():
        fase = f"Grupo {letra}"
        jogos_grupo = [j for j in JOGOS if j["fase"] == fase]
        if not all(j["id"] in todos_resultados for j in jogos_grupo):
            continue  # grupo incompleto, pula
        tabela = _calcular_classificacao(fase, times, todos_resultados)
        classificados[letra] = [t["time"] for t in tabela]
        if len(tabela) >= 3:
            terceiros_info.append({"grupo": letra, "time": tabela[2]["time"], "stats": tabela[2]})

    # Melhores 3ºs só são definitivos quando TODOS os 12 grupos terminam
    terceiro_por_slot: dict[str, str] = {}
    top8: list[dict] = []
    if len(terceiros_info) == 12:
        terceiros_info.sort(key=lambda x: (-x["stats"]["PTS"], -x["stats"]["SG"], -x["stats"]["GP"], x["time"]))
        top8 = terceiros_info[:8]
        terceiro_por_slot = _assign_terceiros(top8)

    # Preenche JogoNomeReal para cada jogo dos 32-avos
    r32_jogos = [j for j in JOGOS if j["fase"] == "32-avos"]
    atualizados = 0
    for jogo in r32_jogos:
        novo_casa = _resolver_slot(jogo["casa"], classificados, terceiro_por_slot, jogo["id"])
        novo_fora = _resolver_slot(jogo["fora"], classificados, terceiro_por_slot, jogo["id"])

        if novo_casa is None and novo_fora is None:
            continue  # nada resolvido ainda para este confronto

        rec = db.query(models.JogoNomeReal).filter(models.JogoNomeReal.jogo_id == jogo["id"]).first()
        if rec:
            changed = False
            if novo_casa is not None and rec.casa_real != novo_casa:
                rec.casa_real = novo_casa
                changed = True
            if novo_fora is not None and rec.fora_real != novo_fora:
                rec.fora_real = novo_fora
                changed = True
            if changed:
                atualizados += 1
        else:
            db.add(models.JogoNomeReal(
                jogo_id=jogo["id"],
                casa_real=novo_casa or jogo["casa"],
                fora_real=novo_fora or jogo["fora"],
            ))
            atualizados += 1

    return {
        "grupos_computados": len(classificados),
        "terceiros_qualificados": len(top8),
        "confrontos_atualizados": atualizados,
    }
