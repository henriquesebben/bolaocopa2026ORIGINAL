TIMES_POR_GRUPO = {
    "A": ["México", "África do Sul", "Coreia do Sul", "Tchéquia"],
    "B": ["Canadá", "Bósnia-Herzegovina", "Catar", "Suíça"],
    "C": ["Brasil", "Marrocos", "Haiti", "Escócia"],
    "D": ["Estados Unidos", "Paraguai", "Austrália", "Turquia"],
    "E": ["Alemanha", "Curaçao", "Costa do Marfim", "Equador"],
    "F": ["Holanda", "Japão", "Suécia", "Tunísia"],
    "G": ["Bélgica", "Egito", "Irã", "Nova Zelândia"],
    "H": ["Espanha", "Cabo Verde", "Arábia Saudita", "Uruguai"],
    "I": ["França", "Senegal", "Iraque", "Noruega"],
    "J": ["Argentina", "Argélia", "Áustria", "Jordânia"],
    "K": ["Portugal", "RD Congo", "Uzbequistão", "Colômbia"],
    "L": ["Inglaterra", "Croácia", "Gana", "Panamá"],
}

TODOS_TIMES = sorted({t for times in TIMES_POR_GRUPO.values() for t in times})

FASES_MATA_MATA = {"32-avos", "Oitavas", "Quartas", "Semifinal", "FINAL"}


def _j(id, fase, mult, mata, casa, fora, data, hora):
    return {
        "id": id, "fase": fase, "multiplicador": mult, "eh_mata_mata": mata,
        "casa": casa, "fora": fora, "data": data, "horario": hora,
    }


def gerar_jogos():
    # ── Fase de grupos (72 jogos — calendário oficial BRT) ────────────────────
    grupos = [
        _j("G-1",  "Grupo A", 1, False, "México",            "África do Sul",      "2026-06-11", "16:00"),
        _j("G-2",  "Grupo A", 1, False, "Coreia do Sul",      "Tchéquia",           "2026-06-11", "23:00"),
        _j("G-3",  "Grupo B", 1, False, "Canadá",             "Bósnia-Herzegovina", "2026-06-12", "16:00"),
        _j("G-4",  "Grupo D", 1, False, "Estados Unidos",     "Paraguai",           "2026-06-12", "22:00"),
        _j("G-5",  "Grupo D", 1, False, "Austrália",          "Turquia",            "2026-06-14", "01:00"),
        _j("G-6",  "Grupo B", 1, False, "Catar",              "Suíça",              "2026-06-13", "16:00"),
        _j("G-7",  "Grupo C", 1, False, "Brasil",             "Marrocos",           "2026-06-13", "19:00"),
        _j("G-8",  "Grupo C", 1, False, "Haiti",              "Escócia",            "2026-06-13", "22:00"),
        _j("G-9",  "Grupo E", 1, False, "Alemanha",           "Curaçao",            "2026-06-14", "14:00"),
        _j("G-10", "Grupo F", 1, False, "Holanda",            "Japão",              "2026-06-14", "17:00"),
        _j("G-11", "Grupo E", 1, False, "Costa do Marfim",    "Equador",            "2026-06-14", "20:00"),
        _j("G-12", "Grupo F", 1, False, "Suécia",             "Tunísia",            "2026-06-14", "23:00"),
        _j("G-13", "Grupo H", 1, False, "Espanha",            "Cabo Verde",         "2026-06-15", "13:00"),
        _j("G-14", "Grupo G", 1, False, "Bélgica",            "Egito",              "2026-06-15", "16:00"),
        _j("G-15", "Grupo H", 1, False, "Arábia Saudita",     "Uruguai",            "2026-06-15", "19:00"),
        _j("G-16", "Grupo G", 1, False, "Irã",                "Nova Zelândia",      "2026-06-15", "22:00"),
        _j("G-17", "Grupo J", 1, False, "Áustria",            "Jordânia",           "2026-06-17", "01:00"),
        _j("G-18", "Grupo I", 1, False, "França",             "Senegal",            "2026-06-16", "16:00"),
        _j("G-19", "Grupo I", 1, False, "Iraque",             "Noruega",            "2026-06-16", "19:00"),
        _j("G-20", "Grupo J", 1, False, "Argentina",          "Argélia",            "2026-06-16", "22:00"),
        _j("G-21", "Grupo K", 1, False, "Portugal",           "RD Congo",           "2026-06-17", "14:00"),
        _j("G-22", "Grupo L", 1, False, "Inglaterra",         "Croácia",            "2026-06-17", "17:00"),
        _j("G-23", "Grupo L", 1, False, "Gana",               "Panamá",             "2026-06-17", "20:00"),
        _j("G-24", "Grupo K", 1, False, "Uzbequistão",        "Colômbia",           "2026-06-17", "23:00"),
        _j("G-25", "Grupo A", 1, False, "Tchéquia",           "África do Sul",      "2026-06-18", "13:00"),
        _j("G-26", "Grupo B", 1, False, "Suíça",              "Bósnia-Herzegovina", "2026-06-18", "16:00"),
        _j("G-27", "Grupo B", 1, False, "Canadá",             "Catar",              "2026-06-18", "19:00"),
        _j("G-28", "Grupo A", 1, False, "México",             "Coreia do Sul",      "2026-06-18", "22:00"),
        _j("G-29", "Grupo D", 1, False, "Turquia",            "Paraguai",           "2026-06-20", "00:00"),
        _j("G-30", "Grupo D", 1, False, "Estados Unidos",     "Austrália",          "2026-06-19", "16:00"),
        _j("G-31", "Grupo C", 1, False, "Escócia",            "Marrocos",           "2026-06-19", "19:00"),
        _j("G-32", "Grupo C", 1, False, "Brasil",             "Haiti",              "2026-06-19", "21:30"),
        _j("G-33", "Grupo F", 1, False, "Tunísia",            "Japão",              "2026-06-21", "01:00"),
        _j("G-34", "Grupo F", 1, False, "Holanda",            "Suécia",             "2026-06-20", "14:00"),
        _j("G-35", "Grupo E", 1, False, "Alemanha",           "Costa do Marfim",    "2026-06-20", "17:00"),
        _j("G-36", "Grupo E", 1, False, "Equador",            "Curaçao",            "2026-06-20", "21:00"),
        _j("G-37", "Grupo H", 1, False, "Espanha",            "Arábia Saudita",     "2026-06-21", "13:00"),
        _j("G-38", "Grupo G", 1, False, "Bélgica",            "Irã",                "2026-06-21", "16:00"),
        _j("G-39", "Grupo H", 1, False, "Uruguai",            "Cabo Verde",         "2026-06-21", "19:00"),
        _j("G-40", "Grupo G", 1, False, "Nova Zelândia",      "Egito",              "2026-06-21", "22:00"),
        _j("G-41", "Grupo J", 1, False, "Jordânia",           "Argélia",            "2026-06-23", "00:00"),
        _j("G-42", "Grupo J", 1, False, "Argentina",          "Áustria",            "2026-06-22", "14:00"),
        _j("G-43", "Grupo I", 1, False, "França",             "Iraque",             "2026-06-22", "18:00"),
        _j("G-44", "Grupo I", 1, False, "Noruega",            "Senegal",            "2026-06-22", "21:00"),
        _j("G-45", "Grupo K", 1, False, "Portugal",           "Uzbequistão",        "2026-06-23", "14:00"),
        _j("G-46", "Grupo L", 1, False, "Inglaterra",         "Gana",               "2026-06-23", "17:00"),
        _j("G-47", "Grupo L", 1, False, "Panamá",             "Croácia",            "2026-06-23", "20:00"),
        _j("G-48", "Grupo K", 1, False, "Colômbia",           "RD Congo",           "2026-06-23", "23:00"),
        _j("G-49", "Grupo B", 1, False, "Suíça",              "Canadá",             "2026-06-24", "16:00"),
        _j("G-50", "Grupo B", 1, False, "Bósnia-Herzegovina", "Catar",              "2026-06-24", "16:00"),
        _j("G-51", "Grupo C", 1, False, "Escócia",            "Brasil",             "2026-06-24", "19:00"),
        _j("G-52", "Grupo C", 1, False, "Marrocos",           "Haiti",              "2026-06-24", "19:00"),
        _j("G-53", "Grupo A", 1, False, "Tchéquia",           "México",             "2026-06-24", "22:00"),
        _j("G-54", "Grupo A", 1, False, "África do Sul",      "Coreia do Sul",      "2026-06-24", "22:00"),
        _j("G-55", "Grupo E", 1, False, "Curaçao",            "Costa do Marfim",    "2026-06-25", "17:00"),
        _j("G-56", "Grupo E", 1, False, "Equador",            "Alemanha",           "2026-06-25", "17:00"),
        _j("G-57", "Grupo F", 1, False, "Japão",              "Suécia",             "2026-06-25", "20:00"),
        _j("G-58", "Grupo F", 1, False, "Tunísia",            "Holanda",            "2026-06-25", "20:00"),
        _j("G-59", "Grupo D", 1, False, "Turquia",            "Estados Unidos",     "2026-06-25", "23:00"),
        _j("G-60", "Grupo D", 1, False, "Paraguai",           "Austrália",          "2026-06-25", "23:00"),
        _j("G-61", "Grupo G", 1, False, "Egito",              "Irã",                "2026-06-27", "00:00"),
        _j("G-62", "Grupo G", 1, False, "Nova Zelândia",      "Bélgica",            "2026-06-27", "00:00"),
        _j("G-63", "Grupo I", 1, False, "Noruega",            "França",             "2026-06-26", "16:00"),
        _j("G-64", "Grupo I", 1, False, "Senegal",            "Iraque",             "2026-06-26", "16:00"),
        _j("G-65", "Grupo H", 1, False, "Cabo Verde",         "Arábia Saudita",     "2026-06-26", "21:00"),
        _j("G-66", "Grupo H", 1, False, "Uruguai",            "Espanha",            "2026-06-26", "21:00"),
        _j("G-67", "Grupo L", 1, False, "Panamá",             "Inglaterra",         "2026-06-27", "18:00"),
        _j("G-68", "Grupo L", 1, False, "Croácia",            "Gana",               "2026-06-27", "18:00"),
        _j("G-69", "Grupo K", 1, False, "Colômbia",           "Portugal",           "2026-06-27", "20:30"),
        _j("G-70", "Grupo K", 1, False, "RD Congo",           "Uzbequistão",        "2026-06-27", "20:30"),
        _j("G-71", "Grupo J", 1, False, "Argélia",            "Áustria",            "2026-06-27", "23:00"),
        _j("G-72", "Grupo J", 1, False, "Jordânia",           "Argentina",          "2026-06-27", "23:00"),
    ]

    # ── 16-avos (28/jun–03/jul) ───────────────────────────────────────────────
    r32 = [
        _j("R32-1",  "32-avos", 1, True, "2º Grupo A",        "2º Grupo B",         "2026-06-28", "16:00"),
        _j("R32-2",  "32-avos", 1, True, "1º Grupo C",        "2º Grupo F",         "2026-06-29", "14:00"),
        _j("R32-3",  "32-avos", 1, True, "1º Grupo E",        "Melhor 3º (ABCDF)",  "2026-06-29", "17:30"),
        _j("R32-4",  "32-avos", 1, True, "1º Grupo F",        "2º Grupo C",         "2026-06-29", "22:00"),
        _j("R32-5",  "32-avos", 1, True, "2º Grupo E",        "2º Grupo I",         "2026-06-30", "14:00"),
        _j("R32-6",  "32-avos", 1, True, "1º Grupo I",        "Melhor 3º (CDFGH)",  "2026-06-30", "18:00"),
        _j("R32-7",  "32-avos", 1, True, "1º Grupo A",        "Melhor 3º (CEFHI)",  "2026-06-30", "22:00"),
        _j("R32-8",  "32-avos", 1, True, "1º Grupo L",        "Melhor 3º (EHIJK)",  "2026-07-01", "13:00"),
        _j("R32-9",  "32-avos", 1, True, "1º Grupo G",        "Melhor 3º (AEHIJ)",  "2026-07-01", "17:00"),
        _j("R32-10", "32-avos", 1, True, "1º Grupo D",        "Melhor 3º (BEFIJ)",  "2026-07-01", "21:00"),
        _j("R32-11", "32-avos", 1, True, "1º Grupo B",        "Melhor 3º (EFGIJ)",  "2026-07-03", "00:00"),
        _j("R32-12", "32-avos", 1, True, "1º Grupo H",        "2º Grupo J",         "2026-07-02", "16:00"),
        _j("R32-13", "32-avos", 1, True, "2º Grupo K",        "2º Grupo L",         "2026-07-02", "20:00"),
        _j("R32-14", "32-avos", 1, True, "2º Grupo D",        "2º Grupo G",         "2026-07-03", "15:00"),
        _j("R32-15", "32-avos", 1, True, "1º Grupo J",        "2º Grupo H",         "2026-07-03", "19:00"),
        _j("R32-16", "32-avos", 1, True, "1º Grupo K",        "Melhor 3º (DEIJL)",  "2026-07-03", "22:30"),
    ]

    # ── Oitavas (04/jul–07/jul) ───────────────────────────────────────────────
    r16 = [
        _j("R16-1", "Oitavas", 1, True, "Vencedor R32-1",  "Vencedor R32-4",  "2026-07-04", "14:00"),
        _j("R16-2", "Oitavas", 1, True, "Vencedor R32-3",  "Vencedor R32-6",  "2026-07-04", "18:00"),
        _j("R16-3", "Oitavas", 1, True, "Vencedor R32-2",  "Vencedor R32-5",  "2026-07-05", "17:00"),
        _j("R16-4", "Oitavas", 1, True, "Vencedor R32-7",  "Vencedor R32-8",  "2026-07-05", "21:00"),
        _j("R16-5", "Oitavas", 1, True, "Vencedor R32-13", "Vencedor R32-12", "2026-07-06", "16:00"),
        _j("R16-6", "Oitavas", 1, True, "Vencedor R32-10", "Vencedor R32-9",  "2026-07-06", "21:00"),
        _j("R16-7", "Oitavas", 1, True, "Vencedor R32-15", "Vencedor R32-14", "2026-07-07", "13:00"),
        _j("R16-8", "Oitavas", 1, True, "Vencedor R32-11", "Vencedor R32-16", "2026-07-07", "17:00"),
    ]

    # ── Quartas (09/jul–11/jul) ───────────────────────────────────────────────
    qf = [
        _j("QF-1", "Quartas", 2, True, "Vencedor R16-2", "Vencedor R16-1", "2026-07-09", "17:00"),
        _j("QF-2", "Quartas", 2, True, "Vencedor R16-5", "Vencedor R16-6", "2026-07-10", "16:00"),
        _j("QF-3", "Quartas", 2, True, "Vencedor R16-3", "Vencedor R16-4", "2026-07-11", "18:00"),
        _j("QF-4", "Quartas", 2, True, "Vencedor R16-7", "Vencedor R16-8", "2026-07-11", "22:00"),
    ]

    # ── Semis, 3° lugar e Final ───────────────────────────────────────────────
    extras = [
        _j("SF-1",  "Semifinal", 3, True,  "Vencedor QF-1", "Vencedor QF-2", "2026-07-14", "16:00"),
        _j("SF-2",  "Semifinal", 3, True,  "Vencedor QF-3", "Vencedor QF-4", "2026-07-15", "16:00"),
        _j("3L",    "3º Lugar",  1, True,  "Perdedor SF-1", "Perdedor SF-2", "2026-07-18", "18:00"),
        _j("FINAL", "FINAL",     4, True,  "Vencedor SF-1", "Vencedor SF-2", "2026-07-19", "16:00"),
    ]

    return grupos + r32 + r16 + qf + extras


JOGOS = gerar_jogos()
JOGOS_POR_ID = {j["id"]: j for j in JOGOS}
