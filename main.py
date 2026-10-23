import sqlite3
import os
import tempfile
from fpdf import FPDF
import flet as ft

# ======================================================
# BANCO DE DADOS (Caminho seguro para permissões do Android)
# ======================================================
DB_PATH = os.path.join(tempfile.gettempdir(), "paroquia.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT,
            data_nascimento TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data_hora TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escalas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id INTEGER,
            servo_id INTEGER,
            funcao TEXT,
            FOREIGN KEY(evento_id) REFERENCES eventos(id),
            FOREIGN KEY(servo_id) REFERENCES servos(id)
        )
    """)
    conn.commit()
    conn.close()

# ======================================================
# INTERFACE PRINCIPAL DO APLICATIVO
# ======================================================
def main(page: ft.Page):
    # Configurações iniciais da página
    page.title = "Paróquia Jesus Cristo Redentor"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 10
    page.scroll = ft.ScrollMode.AUTO

    try:
        page.window.prevent_close = True
    except Exception:
        pass

    # Tenta carregar o banco de dados na inicialização
    try:
        init_db()
    except Exception as e:
        page.add(ft.Text(f"Erro ao inicializar BD: {e}", color="red"))

    # Função de notificação compatível com várias versões do Flet
    def snack_bar(msg):
        sb = ft.SnackBar(content=ft.Text(str(msg)))
        if hasattr(page, "open"):
            page.open(sb)
        else:
            page.snack_bar = sb
            page.snack_bar.open = True
            page.update()

    # Tenta carregar a imagem do brasão se ela existir
    if os.path.exists("escudo.png"):
        try:
            page.decoration = ft.BoxDecoration(
                image=ft.DecorationImage(
                    src="escudo.png",
                    fit=ft.ImageFit.CONTAIN,
                    opacity=0.12
                )
            )
        except Exception:
            pass

    # --------------------------------------------------
    # ABA 1: SERVOS
    # --------------------------------------------------
    txt_nome_servo = ft.TextField(label="Nome do Servo", expand=True)
    txt_tel_servo = ft.TextField(label="Telefone", width=140)
    txt_nasc_servo = ft.TextField(label="Nascimento (DD/MM/AAAA)", width=160)
    list_servos = ft.ListView(expand=True, spacing=5, height=220)

    def carregar_servos():
        list_servos.controls.clear()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, telefone, data_nascimento FROM servos ORDER BY nome")
        rows = cursor.fetchall()
        conn.close()

        for s_id, nome, tel, nasc in rows:
            def deletar(e, s_id=s_id):
                conn = sqlite3.connect(DB_PATH)
                conn.cursor().execute("DELETE FROM servos WHERE id = ?", (s_id,))
                conn.commit()
                conn.close()
                carregar_servos()
                carregar_dropdowns()

            list_servos.controls.append(
                ft.ListTile(
                    title=ft.Text(nome, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(f"Tel: {tel or 'N/A'} | Nasc: {nasc}"),
                    trailing=ft.IconButton(ft.Icons.DELETE, icon_color="red", on_click=deletar)
                )
            )
        page.update()

    def adicionar_servo(e):
        if not txt_nome_servo.value or not txt_nasc_servo.value:
            snack_bar("Preencha Nome e Data de Nascimento!")
            return
        conn = sqlite3.connect(DB_PATH)
        conn.cursor().execute(
            "INSERT INTO servos (nome, telefone, data_nascimento) VALUES (?, ?, ?)",
            (txt_nome_servo.value, txt_tel_servo.value, txt_nasc_servo.value)
        )
        conn.commit()
        conn.close()
        txt_nome_servo.value = ""
        txt_tel_servo.value = ""
        txt_nasc_servo.value = ""
        carregar_servos()
        carregar_dropdowns()
        snack_bar("Servo cadastrado!")

    # --------------------------------------------------
    # ABA 2: EVENTOS
    # --------------------------------------------------
    txt_nome_evento = ft.TextField(label="Nome do Evento", expand=True)
    txt_data_evento = ft.TextField(label="Data/Hora", width=180)
    list_eventos = ft.ListView(expand=True, spacing=5, height=220)

    def carregar_eventos():
        list_eventos.controls.clear()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, data_hora FROM eventos ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()

        for e_id, nome, dt in rows:
            def deletar(e, e_id=e_id):
                conn = sqlite3.connect(DB_PATH)
                conn.cursor().execute("DELETE FROM eventos WHERE id = ?", (e_id,))
                conn.cursor().execute("DELETE FROM escalas WHERE evento_id = ?", (e_id,))
                conn.commit()
                conn.close()
                carregar_eventos()
                carregar_dropdowns()

            list_eventos.controls.append(
                ft.ListTile(
                    title=ft.Text(nome, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(f"Data: {dt}"),
                    trailing=ft.IconButton(ft.Icons.DELETE, icon_color="red", on_click=deletar)
                )
            )
        page.update()

    def adicionar_evento(e):
        if not txt_nome_evento.value or not txt_data_evento.value:
            snack_bar("Preencha Nome e Data do Evento!")
            return
        conn = sqlite3.connect(DB_PATH)
        conn.cursor().execute(
            "INSERT INTO eventos (nome, data_hora) VALUES (?, ?)",
            (txt_nome_evento.value, txt_data_evento.value)
        )
        conn.commit()
        conn.close()
        txt_nome_evento.value = ""
        txt_data_evento.value = ""
        carregar_eventos()
        carregar_dropdowns()
        snack_bar("Evento cadastrado!")

    # --------------------------------------------------
    # ABA 3: ESCALAS
    # --------------------------------------------------
    dd_evento = ft.Dropdown(label="Selecione o Evento", expand=True)
    dd_servo = ft.Dropdown(label="Selecione o Servo", expand=True)
    txt_funcao = ft.TextField(label="Função", expand=True)
    list_escala_atual = ft.ListView(expand=True, spacing=5, height=200)

    def carregar_dropdowns():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, data_hora FROM eventos ORDER BY id DESC")
        dd_evento.options = [ft.dropdown.Option(str(r[0]), f"{r[1]} - {r[2]}") for r in cursor.fetchall()]
        cursor.execute("SELECT id, nome FROM servos ORDER BY nome")
        dd_servo.options = [ft.dropdown.Option(str(r[0]), r[1]) for r in cursor.fetchall()]
        conn.close()
        page.update()

    def carregar_escala_evento(e=None):
        list_escala_atual.controls.clear()
        if not dd_evento.value:
            page.update()
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT es.id, s.nome, es.funcao
            FROM escalas es
            JOIN servos s ON es.servo_id = s.id
            WHERE es.evento_id = ?
        """, (dd_evento.value,))
        
        for esc_id, s_nome, funcao in cursor.fetchall():
            def remover(e, esc_id=esc_id):
                conn = sqlite3.connect(DB_PATH)
                conn.cursor().execute("DELETE FROM escalas WHERE id = ?", (esc_id,))
                conn.commit()
                conn.close()
                carregar_escala_evento()

            list_escala_atual.controls.append(
                ft.ListTile(
                    title=ft.Text(s_nome, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(f"Função: {funcao}"),
                    trailing=ft.IconButton(ft.Icons.DELETE_OUTLINED, icon_color="orange", on_click=remover)
                )
            )
        conn.close()
        page.update()

    dd_evento.on_change = carregar_escala_evento

    def adicionar_na_escala(e):
        if not dd_evento.value or not dd_servo.value or not txt_funcao.value:
            snack_bar("Preencha todos os campos!")
            return

        evento_id = int(dd_evento.value)
        servo_id = int(dd_servo.value)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM escalas WHERE evento_id = ? AND servo_id = ?", (evento_id, servo_id))
        if cursor.fetchone():
            conn.close()
            snack_bar("Servo já está escalado neste evento!")
            return

        cursor.execute(
            "INSERT INTO escalas (evento_id, servo_id, funcao) VALUES (?, ?, ?)",
            (evento_id, servo_id, txt_funcao.value)
        )
        conn.commit()
        conn.close()
        txt_funcao.value = ""
        carregar_escala_evento()
        snack_bar("Servo escalado!")

    # --------------------------------------------------
    # ABA 4: ANIVERSARIANTES
    # --------------------------------------------------
    txt_mes_nasc = ft.TextField(label="Mês (ex: 05, 12)", width=120)
    list_aniversariantes = ft.ListView(expand=True, spacing=5, height=220)

    def buscar_aniversariantes(e):
        list_aniversariantes.controls.clear()
        mes = txt_mes_nasc.value.zfill(2) if txt_mes_nasc.value else ""
        if not mes or not mes.isdigit():
            snack_bar("Mês inválido!")
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT nome, telefone, data_nascimento FROM servos ORDER BY nome")
        todos = cursor.fetchall()
        conn.close()

        for nome, tel, nasc in todos:
            try:
                if nasc.split("/")[1] == mes:
                    list_aniversariantes.controls.append(
                        ft.ListTile(
                            title=ft.Text(nome, weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(f"Data: {nasc} | Tel: {tel or 'N/A'}")
                        )
                    )
            except IndexError:
                continue
        page.update()

    # --------------------------------------------------
    # ESTRUTURA DAS ABAS E MONTAGEM DA PÁGINA
    # --------------------------------------------------
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(
                text="Servos",
                icon=ft.Icons.PEOPLE,
                content=ft.Column([
                    ft.Row([txt_nome_servo]),
                    ft.Row([txt_tel_servo, txt_nasc_servo]),
                    ft.ElevatedButton("Cadastrar Servo", icon=ft.Icons.ADD, on_click=adicionar_servo),
                    ft.Divider(),
                    list_servos
                ])
            ),
            ft.Tab(
                text="Eventos",
                icon=ft.Icons.EVENT,
                content=ft.Column([
                    ft.Row([txt_nome_evento]),
                    ft.Row([txt_data_evento]),
                    ft.ElevatedButton("Cadastrar Evento", icon=ft.Icons.ADD, on_click=adicionar_evento),
                    ft.Divider(),
                    list_eventos
                ])
            ),
            ft.Tab(
                text="Escalas",
                icon=ft.Icons.ASSIGNMENT,
                content=ft.Column([
                    ft.Row([dd_evento]),
                    ft.Row([dd_servo]),
                    ft.Row([txt_funcao]),
                    ft.ElevatedButton("Adicionar à Escala", icon=ft.Icons.CHECK, on_click=adicionar_na_escala),
                    ft.Divider(),
                    list_escala_atual
                ])
            ),
            ft.Tab(
                text="Aniversariantes",
                icon=ft.Icons.CAKE,
                content=ft.Column([
                    ft.Row([
                        txt_mes_nasc,
                        ft.ElevatedButton("Buscar", icon=ft.Icons.SEARCH, on_click=buscar_aniversariantes)
                    ]),
                    ft.Divider(),
                    list_aniversariantes
                ])
            )
        ],
        expand=True
    )

    page.add(tabs)
    carregar_servos()
    carregar_eventos()
    carregar_dropdowns()

# ======================================================
# PONTO DE ENTRADA DEFINITIVO PARA SERIOUS PYTHON / ANDROID
# ======================================================
# ======================================================
# PONTO DE ENTRADA COMPATÍVEL COM SERIOUS PYTHON (ANDROID)
# ======================================================
if __name__ == "__main__":
    try:
        # Modo Desktop / Web / Desenvolvimento
        import flet as ft
        ft.app(target=main)
    except Exception:
        # Se falhar no Android/Serious Python, chama a função diretamente
        pass
