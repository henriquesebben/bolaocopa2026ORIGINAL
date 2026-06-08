from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_fill_color(0, 99, 65)   # verde Copa
        self.rect(0, 0, 210, 18, 'F')
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(255, 223, 0)  # amarelo Copa
        self.set_y(4)
        self.cell(0, 10, "Bolao Copa 2026 - Guia de Uso", align="C")
        self.set_text_color(0, 0, 0)
        self.ln(14)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")

    def titulo_secao(self, texto):
        self.ln(3)
        self.set_fill_color(0, 99, 65)
        self.set_text_color(255, 223, 0)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, texto, new_x="LMARGIN", new_y="NEXT", fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def subtitulo(self, texto):
        self.ln(2)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(0, 99, 65)
        self.multi_cell(0, 6, texto)
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def paragrafo(self, texto):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, texto)
        self.ln(2)

    def destaque(self, texto):
        self.set_fill_color(255, 248, 180)
        self.set_font("Helvetica", "B", 10)
        self.multi_cell(0, 6, texto, fill=True)
        self.set_font("Helvetica", "", 10)
        self.ln(2)

    def bullet(self, items):
        self.set_font("Helvetica", "", 10)
        margem = self.l_margin
        for item in items:
            self.set_x(margem + 4)
            self.multi_cell(0, 5.5, f"- {item}")
        self.ln(2)

    def tabela(self, cabecalho, linhas, larguras):
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(230, 247, 238)
        self.set_draw_color(180, 180, 180)
        for i, col in enumerate(cabecalho):
            self.cell(larguras[i], 7, col, border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", 9)
        fill = False
        self.set_fill_color(248, 248, 248)
        for linha in linhas:
            for i, cel in enumerate(linha):
                self.cell(larguras[i], 6, cel, border=1, fill=fill)
            self.ln()
            fill = not fill
        self.ln(3)


pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=18)
pdf.add_page()
pdf.set_margins(15, 22, 15)

# ── Capa / Intro ────────────────────────────────────────────────────────────
pdf.set_font("Helvetica", "B", 18)
pdf.set_text_color(0, 99, 65)
pdf.ln(2)
pdf.cell(0, 12, "Guia de Uso", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 11)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 7, "Para quem nunca usou nada parecido", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_text_color(0, 0, 0)
pdf.ln(4)

pdf.paragrafo(
    "Este app e um bolao online da Copa do Mundo 2026. Voce entra no site, cria uma conta "
    "e faz palpites de placar para as 104 partidas da Copa. Quanto mais voce acertar, mais "
    "pontos acumula. No final, quem tiver mais pontos ganhou o bolao. Nao precisa instalar "
    "nada nem saber nada de tecnologia. E so acessar o link pelo celular ou computador."
)

# ── Secao 1 ─────────────────────────────────────────────────────────────────
pdf.titulo_secao("  ANTES DE ENTRAR NO SITE PELA PRIMEIRA VEZ")

pdf.subtitulo("A tela preta (ou branca) ao abrir o site")
pdf.paragrafo(
    "Quando voce abre o link pela primeira vez no dia, o site pode demorar ate 1 minuto "
    "para carregar e mostrar a tela de login. Isso e completamente normal."
)
pdf.subtitulo("Por que isso acontece?")
pdf.paragrafo(
    "O servidor onde o app esta hospedado 'dorme' quando ninguem usa por algum tempo, "
    "para economizar recursos. Quando alguem abre o link, ele precisa 'acordar' antes de "
    "responder. Enquanto isso, o navegador fica na tela escura ou em branco."
)
pdf.destaque(
    "O que fazer: Aguarde. Nao feche, nao recarregue a pagina. Em ate 60 segundos o "
    "site vai aparecer normalmente. Depois que o servidor acordou, todo mundo que acessar "
    "nesse periodo vai entrar rapido."
)

# ── Secao 2 ─────────────────────────────────────────────────────────────────
pdf.titulo_secao("  PASSO 1 - CRIAR SUA CONTA")

pdf.paragrafo("Quando a tela de login aparecer, voce vai ver campos de Nome e Senha.")
pdf.paragrafo("Como e sua primeira vez:")
pdf.bullet([
    "Clique em 'Criar conta' (botao abaixo dos campos)",
    "Um terceiro campo vai aparecer para confirmar a senha",
    "Nome: como voce quer aparecer no ranking (apelido, primeiro nome etc. - max. 30 letras)",
    "Senha: qualquer senha que voce va lembrar (minimo 4 caracteres)",
    "Confirmar senha: repita a mesma senha",
    "Clique em 'Criar conta' - voce ja entra automaticamente",
])
pdf.destaque(
    "Atencao: o nome escolhido aparece publicamente no ranking para todos os participantes. "
    "Nao existe 'esqueci minha senha' - guarde a sua. O app lembra de voce por 7 dias; "
    "depois disso, precisara fazer login novamente."
)

# ── Secao 3 ─────────────────────────────────────────────────────────────────
pdf.titulo_secao("  PASSO 2 - PALPITES BONUS (FACA ISSO PRIMEIRO!)")

pdf.destaque(
    "URGENTE - Prazo: 11 de junho de 2026 as 15h50 (horario de Brasilia). "
    "Depois desse horario os campos travam e ninguem mais consegue alterar."
)
pdf.paragrafo(
    "Clique em 'Palpites' no menu e olhe o topo da tela. Voce vai encontrar dois palpites "
    "especiais que valem 20 pontos cada:"
)
pdf.bullet([
    "Campeao da Copa: escolha qual selecao vai ganhar o torneio. Clique no campo e uma "
    "lista com os 48 paises participantes vai aparecer.",
    "Artilheiro: escreva o nome do jogador que voce acha que vai fazer mais gols. O campo "
    "tem sugestao automatica - comece a digitar e as opcoes aparecem.",
])
pdf.paragrafo("Apos preencher os dois, clique em 'Salvar bonus'.")

# ── Secao 4 ─────────────────────────────────────────────────────────────────
pdf.titulo_secao("  PASSO 3 - FAZER PALPITES DAS PARTIDAS")

pdf.paragrafo(
    "Ainda na aba 'Palpites', abaixo dos bonus, ficam os jogos da Copa organizados por data. "
    "Use as setas para navegar entre os dias."
)
pdf.paragrafo("Para cada jogo:")
pdf.bullet([
    "Voce ve os dois times e dois campos de numero (gols)",
    "Digite quantos gols voce acha que cada time vai fazer",
    "Clique em 'Salvar' - o botao vai mudar para 'Salvo' confirmando o registro",
])
pdf.subtitulo("Limite de tempo por jogo")
pdf.paragrafo(
    "Cada jogo trava automaticamente 10 minutos antes do horario de inicio. Quando travar, "
    "o campo fica cinza e nao da mais para editar."
)
pdf.subtitulo("Jogos de mata-mata (fase eliminatoria)")
pdf.paragrafo(
    "Nesses jogos, se voce prever um empate no placar, vai aparecer uma opcao extra "
    "perguntando qual time voce acha que avanca. Isso e obrigatorio porque no mata-mata "
    "sempre ha um vencedor (prorrogacao ou penaltis)."
)
pdf.paragrafo(
    "Nao se preocupe se nao fizer todos os palpites. Jogo sem palpite = 0 pontos naquele jogo. "
    "Voce pode ir fazendo aos poucos, respeitando os prazos de cada partida."
)

# ── Secao 5 ─────────────────────────────────────────────────────────────────
pdf.titulo_secao("  COMO OS PONTOS SAO CALCULADOS")

pdf.tabela(
    ["O que voce acertou", "Pontos"],
    [
        ["Placar exato (ex: voce disse 2x1, deu 2x1)", "10 pts"],
        ["Quem ganhou + pelo menos 1 numero certo", "7 pts"],
        ["So quem ganhou (resultado certo)", "5 pts"],
        ["So 1 numero certo (mas errou o resultado)", "2 pts"],
        ["Errou tudo", "0 pts"],
    ],
    [155, 25],
)

pdf.subtitulo("Fases mais avancadas valem mais (multiplicadores)")
pdf.tabela(
    ["Fase", "Multiplicador"],
    [
        ["Fase de Grupos / Fase de 32 / Oitavas", "x1 (normal)"],
        ["Quartas de final", "x2 (dobrado)"],
        ["Semifinais", "x3 (triplicado)"],
        ["3o lugar", "x1 (normal)"],
        ["Final", "x4 (quadruplicado)"],
    ],
    [130, 50],
)

pdf.subtitulo("Bonus")
pdf.bullet([
    "Acertou o campeao: +20 pontos",
    "Acertou o artilheiro: +20 pontos",
])
pdf.destaque(
    "Exemplo: voce acertou o placar exato da final (10 pts x 4 = 40 pontos). "
    "Mais 20 do campeao e 20 do artilheiro = 80 pontos de uma vez so nessa reta final."
)

# ── Secao 6 ─────────────────────────────────────────────────────────────────
pdf.titulo_secao("  ACOMPANHANDO O BOLAO")

pdf.bullet([
    "Ranking: classificacao de todos os participantes em tempo real, atualiza a cada 30 "
    "segundos automaticamente.",
    "Historico: seu desempenho jogo a jogo - quais voce acertou e quantos pontos ganhou.",
    "Todos: o que cada participante apostou em cada jogo. Os palpites ficam ocultos ate "
    "10 minutos antes do jogo comecar (para ninguem copiar na ultima hora).",
])

pdf.subtitulo("Empate no ranking")
pdf.paragrafo("Se dois participantes tiverem a mesma pontuacao, o desempate e feito nessa ordem:")
pdf.bullet([
    "1o: quem acertou mais placares exatos",
    "2o: quem acertou mais resultados (ganhou/perdeu/empatou)",
    "3o: quem acertou o artilheiro",
    "4o: quem acertou o campeao",
])

# ── Secao 7 ─────────────────────────────────────────────────────────────────
pdf.titulo_secao("  INSTALAR O APP NO CELULAR (OPCIONAL)")

pdf.subtitulo("Android (Chrome)")
pdf.paragrafo(
    "Abra o link, toque nos tres pontos no canto superior direito do Chrome e escolha "
    "'Adicionar a tela inicial' ou 'Instalar app'."
)
pdf.subtitulo("iPhone (Safari)")
pdf.paragrafo(
    "Abra o link no Safari, toque no icone de compartilhar (quadrado com seta para cima) "
    "e escolha 'Adicionar a Tela de Inicio'."
)
pdf.paragrafo("Depois disso, vai aparecer um icone na tela inicial como qualquer outro app.")

# ── Secao 8 ─────────────────────────────────────────────────────────────────
pdf.titulo_secao("  NOTIFICACOES DE RESULTADO")

pdf.paragrafo(
    "Quando voce entrar no site pela primeira vez, o navegador pode perguntar se voce quer "
    "receber notificacoes. Se aceitar, voce vai receber um aviso no celular sempre que um "
    "resultado for lancado no bolao, sem precisar abrir o app. Nao e obrigatorio."
)

# ── Secao 9 ─────────────────────────────────────────────────────────────────
pdf.titulo_secao("  PROBLEMAS COMUNS")

problemas = [
    (
        "Entrei nome e senha certos mas deu erro",
        "Aguarde um momento - pode ser que o servidor ainda esteja acordando. Tente novamente em 30 segundos."
    ),
    (
        "O site sumiu ou deu erro de conexao",
        "Vai aparecer um aviso vermelho no topo: 'Sem conexao com o servidor'. Aguarde - o app vai reconectar sozinho."
    ),
    (
        "Meu palpite nao salvou",
        "Se o botao voltou para 'Salvar' (nao ficou 'Salvo'), verifique se o jogo ainda nao travou e tente novamente."
    ),
    (
        "O nome do artilheiro nao aparece como sugestao",
        "Digite pelo menos 2-3 letras devagar. O campo so sugere jogadores convocados oficialmente para a Copa 2026."
    ),
    (
        "Esqueci minha senha",
        "Entre em contato com o administrador do bolao. Ele pode redefinir sua senha diretamente pelo painel Admin, "
        "sem apagar nenhum palpite. Voce recebe a nova senha e ja consegue entrar normalmente."
    ),
]

pdf.set_font("Helvetica", "", 10)
for pergunta, resposta in problemas:
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(0, 99, 65)
    pdf.multi_cell(0, 5.5, f"? {pergunta}")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_x(pdf.l_margin + 4)
    pdf.multi_cell(0, 5.5, resposta)
    pdf.ln(2)

# ── Secao 10 ────────────────────────────────────────────────────────────────
pdf.titulo_secao("  RESUMO DAS REGRAS E PRAZOS")

pdf.tabela(
    ["Prazo / Regra", "Detalhe"],
    [
        ["Palpites bonus (campeao + artilheiro)", "Travam em 11/06 as 15h50 BRT"],
        ["Palpite de cada jogo", "Trava 10 minutos antes do inicio do jogo"],
        ["Palpites dos outros participantes", "Ocultos ate o jogo travar"],
        ["Editar apos o prazo", "Nao e possivel, mesmo que o jogo nao tenha comecado"],
        ["Jogo sem palpite", "0 pontos naquele jogo"],
    ],
    [100, 80],
)

# ── Secao: Manutencao ────────────────────────────────────────────────────────
pdf.titulo_secao("  MANUTENCAO DO BOLAO")

pdf.paragrafo(
    "Qualquer mudanca que for feita no app sera avisada para todos os participantes. "
    "Para que as atualizacoes funcionem corretamente sem prejudicar a usabilidade, "
    "a cada mudanca feita no app e necessario sair da conta e fazer login de novo, "
    "para recarregar as novas mudancas."
)
pdf.subtitulo("Como fazer logout e login novamente:")
pdf.bullet([
    "No canto superior da tela, clique no seu nome de usuario",
    "Clique em 'Sair' para desconectar",
    "Digite seu nome e senha normalmente para entrar de novo",
    "O app vai carregar com todas as atualizacoes mais recentes",
])
pdf.destaque(
    "Se o app parecer com comportamento estranho apos uma atualizacao, "
    "fazer logout e login novamente resolve na maioria dos casos."
)

# ── Salvar ──────────────────────────────────────────────────────────────────
saida = r"c:\BolaoCopa2026\Guia_Bolao_Copa2026.pdf"
pdf.output(saida)
print(f"PDF gerado: {saida}")
