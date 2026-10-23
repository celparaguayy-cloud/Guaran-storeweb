"""
Pruebas del bot multi-negocio, con TODOS los servicios simulados
(Meta, Gemini, Airtable, Telegram, Upstash). No toca nada real.

Correr:   python3 test_bot.py
(si encuentra el main.py viejo de guaranistorebot, también compara que
Guaranístore responda exactamente igual que antes; la ruta se cambia con
la variable ORIGINAL_MAIN)
"""
import os, sys, json, copy, time, socket, threading, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
ORIGINAL = os.environ.get("ORIGINAL_MAIN", "/home/user/celparaguayy-cloud/guaranistorebot/main.py")

from simulador import ENV, FAKE, cargar, PAG_GUARANI, PAG_A, PAG_B, PAG_C, BASE_A, BASE_B, BASE_C

bot = cargar("bot_nuevo", os.path.join(AQUI, "main.py"))
viejo = cargar("bot_viejo", ORIGINAL) if os.path.exists(ORIGINAL) else None

from fastapi.testclient import TestClient
cli = TestClient(bot.app)
cli_viejo = TestClient(viejo.app) if viejo else None

RESULTADOS = []
def check(nombre, ok, detalle=""):
    RESULTADOS.append((nombre, bool(ok)))
    print(("  ✅ " if ok else "  ❌ ") + nombre + ("" if ok else "  →  " + str(detalle)[:400]))

def evento(page_id, sender, texto=None, mid=None, imagen=None, echo=False):
    msg = {"mid": mid or "m-%s-%s-%s" % (page_id, sender, time.time_ns())}
    if texto is not None: msg["text"] = texto
    if imagen: msg["attachments"] = [{"type": "image", "payload": {"url": imagen}}]
    if echo: msg["is_echo"] = True
    return {"object": "page", "entry": [{"id": page_id, "messaging": [{"sender": {"id": sender}, "message": msg}]}]}

def sembrar_guarani():
    FAKE.base("appGUARANI0000000", "at-tuya")
    FAKE.paginas["tok-guarani"] = {"id": PAG_GUARANI, "name": "Guaranístore"}
    b = "appGUARANI0000000"
    FAKE.registro(b, "Catalogo_Espejo", {"producto_id": "crema", "nombre": "Crema", "precio_gs": "100000", "costo_gs": "40000", "stock_estado": "disponible"})
    FAKE.registro(b, "Catalogo_Espejo", {"producto_id": "ipl", "nombre": "Depiladora IPL", "precio_gs": "450000", "stock_estado": "agotado"})
    FAKE.registro(b, "Pedidos", {"Producto": "Crema", "Nombre": "Isabel", "Ciudad": "Luque", "Total": "Gs. 100.000", "Fecha": "05/10/2026 09:00", "Estado": "Nuevo", "Contacto": "555"})
    FAKE.registro(b, "Pedidos", {"Producto": "Depiladora IPL", "Nombre": "Marta", "Ciudad": "Asuncion", "Total": "Gs. 450.000", "Fecha": "01/09/2026 11:00", "Estado": "Pendiente de Verificación", "Contacto": "556"})
    for txt in ("[user] hola", "[bot] hola!", "[user] cuanto sale"):
        FAKE.registro(b, "Conversaciones", {"contact_id": "777", "canal": "messenger", "mensaje_entrante": txt})

def h(clave): return {"X-Clave": clave}
ADMIN = {"X-Admin": ENV["ADMIN_CLAVE"]}

def respuestas_a(token, sender):
    return [p["message"]["text"] for t, p in FAKE.mensajes if t == token and p.get("recipient", {}).get("id") == sender and "message" in p and "text" in p["message"]]


# ============================================================
print("\n== 1. Guaranístore sigue igual ==")
# ============================================================
if viejo:
    check("La forma de vender de Guaranístore es idéntica a la de antes", bot.SYSTEM_PROMPT == viejo.SYSTEM_PROMPT)
    check("El prompt del modo dueño de Guaranístore es idéntico", bot.PROMPT_DUENO == viejo.PROMPT_DUENO)

    GETS = ["/api/panel/resumen", "/api/panel/pedidos", "/api/panel/catalogo", "/api/panel/seguimiento",
            "/api/panel/conversaciones", "/api/panel/ganancia", "/api/panel/ventas-mes", "/api/panel/seguimiento-plus",
            "/api/panel/analisis-charlas", "/api/panel/pendientes-pago", "/api/panel/stock-alerta", "/api/panel/reporte-dia",
            "/api/panel/buscar?q=isabel", "/api/panel/cliente?id=555", "/api/panel/config", "/api/panel/diagnostico",
            "/api/panel/acciones"]
    FAKE.reset(); sembrar_guarani()
    distintos = []
    for ruta in GETS:
        a = cli_viejo.get(ruta, headers=h("clave-guarani")).json()
        b = cli.get(ruta, headers=h("clave-guarani")).json()
        if ruta == "/api/panel/resumen": b.pop("negocio", None)
        if a != b: distintos.append(ruta)
    check("Las 17 pantallas del panel devuelven lo mismo que antes", not distintos, distintos)

    def correr_escritura(cliente):
        FAKE.reset(); sembrar_guarani()
        pedido = list(FAKE.bases["appGUARANI0000000"]["Pedidos"])[1]
        prod = list(FAKE.bases["appGUARANI0000000"]["Catalogo_Espejo"])[0]
        salidas = [
            cliente.post("/api/panel/estado", headers=h("clave-guarani"), json={"id": pedido, "estado": "Enviado"}).json(),
            cliente.post("/api/panel/aprobar-pedido", headers=h("clave-guarani"), json={"id": pedido}).json(),
            cliente.post("/api/panel/pedido", headers=h("clave-guarani"), json={"producto": "Crema", "nombre": "Leti", "total": "Gs. 100.000"}).json(),
            cliente.post("/api/panel/producto", headers=h("clave-guarani"), json={"nombre": "Serum Nuevo", "precio": "80000"}).json(),
            cliente.patch("/api/panel/editar-producto", headers=h("clave-guarani"), json={"id": prod, "precio": "120000"}).json(),
            cliente.post("/api/panel/editar-costo", headers=h("clave-guarani"), json={"id": prod, "costo": "50.000"}).json(),
            cliente.request("DELETE", "/api/panel/producto", headers=h("clave-guarani"), json={"id": prod}).json(),
            cliente.post("/api/panel/fer", headers=h("clave-guarani"), json={"mensaje": "¿cómo vamos?"}).json(),
            cliente.post("/api/panel/reenganche", headers=h("clave-guarani"), json={"ultimo": "lo voy a pensar"}).json(),
            cliente.post("/api/panel/postventa-mensaje", headers=h("clave-guarani"), json={"tipo": "camino", "nombre": "Ana", "producto": "Crema"}).json(),
            cliente.post("/api/panel/config", headers=h("clave-guarani"), json={"nota": "hola"}).json(),
            cliente.get("/api/panel/resumen", headers=h("clave-mala")).status_code,
        ]
        return salidas, copy.deepcopy(FAKE.bases), copy.deepcopy(FAKE.redis), list(FAKE.mensajes)
    sv = correr_escritura(cli_viejo); sn = correr_escritura(cli)
    check("Cambiar estados, cobrar, cargar y editar productos queda igual que antes", sv == sn,
          [i for i, (x, y) in enumerate(zip(sv[0], sn[0])) if x != y])

    def charla(cliente, mod):
        FAKE.reset(); sembrar_guarani()
        mod.VISTOS.clear(); mod.MODO.clear()
        for i, (texto, img) in enumerate([("hola, buen día", None), ("¿qué precio tiene la crema?", None), ("mandame fotos", None),
                                           ("quiero pedir", None), (None, "https://cdn.fb.test/c.jpg"), ("soyeldueno", None),
                                           ("¿cómo van las ventas?", None), ("salir", None), ("video?", None)]):
            cliente.post("/webhook", json=evento(PAG_GUARANI, "555", texto, mid="mid-%d" % i, imagen=img))
        cliente.post("/webhook", json=evento(PAG_GUARANI, "555", "hola, buen día", mid="mid-0"))  # repetido
        llamadas = [c for c in FAKE.llamadas if not (c[0] == "GET" and c[1].endswith("graph.facebook.com/v21.0/me"))]
        return llamadas, copy.deepcopy(FAKE.bases), copy.deepcopy(FAKE.redis), list(FAKE.telegram)
    cv = charla(cli_viejo, viejo); cn = charla(cli, bot)
    check("Una charla completa con Guaranístore hace exactamente las mismas llamadas que antes", cv[0] == cn[0],
          next(((i, a, b) for i, (a, b) in enumerate(zip(cv[0], cn[0])) if a != b), (len(cv[0]), len(cn[0]))))
    check("…y deja Airtable, la memoria y los avisos de Telegram iguales", cv[1:] == cn[1:])
else:
    print("  (no encontré el main.py viejo en %s: salteo la comparación)" % ORIGINAL)

FAKE.reset(); sembrar_guarani(); bot.VISTOS.clear(); bot.MODO.clear()
bot._PAGINA_PRINCIPAL.update(id="", intento=0.0)
cli.post("/webhook", json=evento(PAG_GUARANI, "900", "hola"))
check("Guaranístore averigua sola el id de su página", bot._PAGINA_PRINCIPAL["id"] == PAG_GUARANI)
check("Guaranístore sigue usando su memoria de siempre (hist:<cliente>)", "hist:900" in FAKE.redis)


# ============================================================
print("\n== 2. Admin: cargar negocios ==")
# ============================================================
for base, clave in ((BASE_A, "at-tuya"), (BASE_B, "at-de-b"), (BASE_C, "at-tuya")): FAKE.base(base, clave)
FAKE.paginas.update({"tok-a": {"id": PAG_A, "name": "Tienda A"}, "tok-b": {"id": PAG_B, "name": "Tienda B"},
                     "tok-c": {"id": PAG_C, "name": "Tienda C"}})
FAKE.personas["persona-corto"] = [PAG_A, PAG_B]

check("Sin clave de admin no se entra", cli.get("/api/admin/negocios").status_code == 401)
check("La clave del panel de Guaranístore no abre el admin", cli.get("/api/admin/negocios", headers={"X-Admin": "clave-guarani"}).status_code == 401)

r = cli.post("/api/admin/paginas", headers=ADMIN, json={"user_token": "persona-corto"}).json()
check("«Buscar mis páginas» canjea el token y trae tokens que no vencen",
      r.get("ok") and r.get("no_vencen") and {p["page_id"] for p in r["paginas"]} == {PAG_A, PAG_B}, r)
r = cli.post("/api/admin/validar-token", headers=ADMIN, json={"page_token": "tok-a"}).json()
check("Validar token: Meta dice de qué página es y que no vence", r.get("ok") and r["page_id"] == PAG_A and r["vence"] == "nunca", r)
r = cli.post("/api/admin/validar-token", headers=ADMIN, json={"page_token": "persona-corto"}).json()
check("Validar token: avisa si pegaste un token de persona", not r.get("ok") and "persona" in r.get("error", ""), r)

def alta(**datos):
    return cli.post("/api/admin/negocio", headers=ADMIN, json=datos).json()

malos = [
    alta(nombre="X", clave_panel="corta", page_token="tok-c"),
    alta(nombre="X", clave_panel="clave-guarani", page_token="tok-c"),
    alta(nombre="X", clave_panel="clave-buena-x", airtable_base="baseMala", page_token="tok-c"),
    alta(nombre="X", clave_panel="clave-buena-x", page_token="tok-guarani"),
    alta(nombre="X", clave_panel="clave-buena-x", fotos="foto.jpg"),
]
check("Rechaza claves cortas o repetidas, bases mal escritas, la página de Guaranístore y fotos sin link",
      all(not m.get("ok") for m in malos), malos)

ra = alta(nombre="Tienda A", clave_panel="clave-tienda-a", page_token="tok-a", airtable_base=BASE_A,
          telegram_chat="chat-a", clave_dueno="DuenoA", fotos="https://a.test/1.jpg\nhttps://a.test/2.jpg")
rb = alta(nombre="Tienda B", clave_panel="clave-tienda-b", page_token="tok-b", airtable_base=BASE_B,
          airtable_key="at-de-b", telegram_chat="chat-b", telegram_token="tg-de-b",
          prompt="Sos Lu, de la tienda B. NEGOCIO=TiendaB-propio. Vendés ropa.")
rc = alta(nombre="Tienda C", clave_panel="clave-tienda-c", page_token="tok-c", airtable_base=BASE_C)
check("Carga tres negocios y saca solo el id de cada página", ra.get("ok") and rb.get("ok") and rc.get("ok")
      and ra["negocio"]["page_id"] == PAG_A and rc["negocio"]["page_id"] == PAG_C, (ra, rb, rc))
check("No deja cargar dos veces la misma clave de panel", not alta(nombre="D", clave_panel="clave-tienda-a").get("ok"))

lista = cli.get("/api/admin/negocios", headers=ADMIN).json()
textos = json.dumps(lista)
check("La lista muestra Guaranístore + los 3, sin mostrar ningún token entero",
      len(lista["negocios"]) == 4 and "tok-a" not in textos and "at-de-b" not in textos and "tok-guarani" not in textos
      and "clave-guarani" not in textos)
ID_A, ID_B, ID_C = ra["negocio"]["id"], rb["negocio"]["id"], rc["negocio"]["id"]

r = cli.post("/api/admin/negocio", headers=ADMIN, json={"id": ID_A, "nombre": "Tienda A", "page_token": "••••ok-a", "notas": "paga el 5"}).json()
neg_a = bot.negocio_por_id(ID_A)
check("Editar sin tocar el token deja el token como estaba", r.get("ok") and neg_a.page_token == "tok-a" and neg_a.notas == "paga el 5", r)

FAKE.paginas["tok-a2"] = {"id": "2001", "name": "Tienda A (nueva)"}
cli.post("/api/admin/negocio", headers=ADMIN, json={"id": ID_A, "nombre": "Tienda A", "page_token": "tok-a2"})
cambio = bot.negocio_por_id(ID_A).page_id
cli.post("/api/admin/negocio", headers=ADMIN, json={"id": ID_A, "nombre": "Tienda A", "page_token": "tok-a"})
check("Pegar un token nuevo actualiza solo el id de la página", cambio == "2001" and bot.negocio_por_id(ID_A).page_id == PAG_A, cambio)

r = cli.post("/api/admin/conectar", headers=ADMIN, json={"id": ID_A}).json()
cli.post("/api/admin/conectar", headers=ADMIN, json={"id": ID_B}); cli.post("/api/admin/conectar", headers=ADMIN, json={"id": ID_C})
check("«Conectar página» la suscribe a la app con su propio token", r.get("ok") and {PAG_A, PAG_B, PAG_C} <= FAKE.suscritas, r)


# ============================================================
print("\n== 3. Varios negocios a la vez, sin mezclarse ==")
# ============================================================
FAKE.mensajes.clear(); FAKE.telegram.clear(); FAKE.demora_gemini = 0.05
trabajos = []
for pag in (PAG_A, PAG_B, PAG_C):
    for i in range(4):
        trabajos.append((pag, "8%s%d" % (pag[0], i % 3), "hola %s nro %d" % (pag, i)))
hilos = []
for pag, sender, texto in trabajos:
    ev = evento(pag, sender, texto)["entry"][0]["messaging"][0]
    hilos.append(threading.Thread(target=bot.procesar_evento, args=(pag, ev)))
inicio = time.time()
for t in hilos: t.start()
for t in hilos: t.join()
tardo = time.time() - inicio
FAKE.demora_gemini = 0.0
esperado = {PAG_A: ("tok-a", "Tienda A"), PAG_B: ("tok-b", "TiendaB-propio"), PAG_C: ("tok-c", "Tienda C")}
textos_ok = True
for pag, sender, texto in trabajos:
    tok, tienda = esperado[pag]
    resp = respuestas_a(tok, sender)
    if not any(x == "[%s] respuesta a: %s" % (tienda, texto) for x in resp): textos_ok = False
ajenos = [p for t, p in FAKE.mensajes if "message" in p and not p["message"].get("text", "").startswith("[" + {"tok-a": "Tienda A", "tok-b": "TiendaB-propio", "tok-c": "Tienda C"}[t] + "]")]
check("12 mensajes de 3 negocios al mismo tiempo: cada uno contestado por su negocio", textos_ok and not ajenos, ajenos[:2])
check("Se atendieron en paralelo (no uno atrás del otro)", tardo < 12 * 0.05 * 2 * 0.8, "%.2fs" % tardo)
convs = {b: [r["fields"]["contact_id"] for r in FAKE.bases[b]["Conversaciones"].values()] for b in (BASE_A, BASE_B, BASE_C)}
check("Cada charla quedó guardada en la base de Airtable de su negocio",
      all(all(c.startswith("8" + p[0]) for c in convs[b]) and len(convs[b]) == 8 for p, b in ((PAG_A, BASE_A), (PAG_B, BASE_B), (PAG_C, BASE_C))), convs)
check("La memoria de cada negocio va separada (hist:<negocio>:<cliente>)",
      "hist:%s:82%d" % (ID_A, 0) in FAKE.redis and "hist:%s:83%d" % (ID_B, 0) in FAKE.redis and not any(k == "hist:820" for k in FAKE.redis))
historial = FAKE.redis.get("hist:%s:820" % ID_A, [])
check("El mismo cliente escribiendo seguido recibe sus respuestas en orden", len(historial) == 4 and historial[0].startswith("[user]") and historial[1].startswith("[bot]") and historial[2].startswith("[user]"), historial)

# pedido de un cliente: Telegram del negocio, nunca el tuyo
FAKE.telegram.clear()
cli.post("/webhook", json=evento(PAG_B, "8399", "quiero pedir"))
cli.post("/webhook", json=evento(PAG_C, "8499", "quiero pedir"))
pedidos_b = [r["fields"] for r in FAKE.bases[BASE_B]["Pedidos"].values()]
check("Un pedido de la Tienda B llega al Telegram de B y a su Airtable",
      [t[:2] for t in FAKE.telegram] == [("tg-de-b", "chat-b")] and pedidos_b and pedidos_b[0]["Contacto"] == "8399"
      and "Tienda B" in FAKE.telegram[0][2], FAKE.telegram)
check("La Tienda C, sin Telegram cargado, no le avisa a nadie (ni a vos)", len(FAKE.telegram) == 1 and FAKE.bases[BASE_C]["Pedidos"])
check("El envío al interior suma el costo de envío", pedidos_b and pedidos_b[0]["Total"] == "Gs. 125.000", pedidos_b)

FAKE.mensajes.clear()
cli.post("/webhook", json=evento(PAG_A, "8100", "mandame fotos"))
cli.post("/webhook", json=evento(PAG_C, "8100", "mandame fotos"))
fotos_a = [p["message"]["attachment"]["payload"]["url"] for t, p in FAKE.mensajes if t == "tok-a" and "attachment" in p.get("message", {})]
check("Cada negocio manda sus propias fotos", fotos_a == ["https://a.test/1.jpg", "https://a.test/2.jpg"]
      and not any("attachment" in p.get("message", {}) for t, p in FAKE.mensajes if t == "tok-c"), fotos_a)
check("A un negocio sin fotos el bot no se las ofrece", "No tenés fotos" in bot.negocio_por_id(ID_C).system_prompt
      and "[FOTOS]" not in bot.negocio_por_id(ID_C).system_prompt)

FAKE.mensajes.clear()
cli.post("/webhook", json=evento(PAG_A, "8101", "duenoa"))
cli.post("/webhook", json=evento(PAG_A, "8101", "¿cómo vamos?"))
cli.post("/webhook", json=evento(PAG_B, "8101", "duenoa"))
check("La palabra secreta del dueño de A abre el modo dueño solo en A",
      respuestas_a("tok-a", "8101")[-1].startswith("[DUEÑO Tienda A]") and respuestas_a("tok-b", "8101")[-1].startswith("[TiendaB-propio]"),
      (respuestas_a("tok-a", "8101"), respuestas_a("tok-b", "8101")))

FAKE.mensajes.clear()
cli.post("/webhook", json=evento("99999", "8102", "hola"))
cli.post("/webhook", json=evento(PAG_A, PAG_A, "eco", echo=True))
cli.post("/webhook", json=evento(PAG_A, "8103", "hola", mid="repetido"))
cli.post("/webhook", json=evento(PAG_A, "8103", "hola", mid="repetido"))
check("Ignora páginas que no cargaste, sus propios ecos y mensajes repetidos",
      not respuestas_a("tok-guarani", "8102") and not respuestas_a("tok-a", PAG_A) and len(respuestas_a("tok-a", "8103")) == 1)


# ============================================================
print("\n== 4. Cada clave ve solo lo suyo ==")
# ============================================================
nombres = lambda clave: sorted(p["nombre"] for p in cli.get("/api/panel/pedidos", headers=h(clave)).json().get("pedidos", []))
pa = nombres("clave-tienda-a"); pb = nombres("clave-tienda-b"); pg = nombres("clave-guarani")
check("Con tu clave el panel muestra Guaranístore", pg == ["Isabel", "Marta"], pg)
check("Con la clave de B, solo los pedidos de B", pb == ["Ana"], pb)
check("Con la clave de A, nada de otros (A no tiene pedidos)", pa == [], pa)
check("El panel sabe el nombre del negocio", cli.get("/api/panel/resumen", headers=h("clave-tienda-b")).json().get("negocio") == "Tienda B")
rec_guarani = list(FAKE.bases["appGUARANI0000000"]["Pedidos"])[0]
trampa = cli.post("/api/panel/estado", headers=h("clave-tienda-c"),
                  json={"id": "../../appGUARANI0000000/Pedidos/" + rec_guarani, "estado": "Cancelado"}).json()
check("Un cliente no puede tocar pedidos de otra base con un id trucho",
      not trampa.get("ok") and FAKE.bases["appGUARANI0000000"]["Pedidos"][rec_guarani]["fields"]["Estado"] == "Nuevo", trampa)
check("Una clave inventada da «Clave incorrecta»", cli.get("/api/panel/resumen", headers=h("clave-que-no-existe")).status_code == 401)
r = cli.get("/api/panel/diagnostico", headers=h("clave-tienda-b")).json()
llam_b = [c for c in FAKE.llamadas[-12:] if "graph.facebook.com/me" in c[1]]
check("El diagnóstico de B revisa el token y la base de B", r.get("salud") and llam_b and llam_b[-1][2]["access_token"] == "tok-b", llam_b[-1:])
cli.get("/api/panel/pedidos", headers=h("clave-tienda-b"))
r = cli.post("/api/chat", json={"mensaje": "hola"}).json()
check("Después de usar el panel de un cliente, el chat web sigue siendo de Guaranístore", r["respuesta"].startswith("[Guaranistore]"), r)
r = cli.get("/api/admin/revisar?id=" + ID_A, headers=ADMIN).json()
check("«Revisar» en el admin incluye si la página está conectada", any(c["nombre"] == "Página conectada al bot" and c["estado"] == "ok" for c in r.get("checks", [])), r)


# ============================================================
print("\n== 5. Pausar, borrar datos y Upstash caído ==")
# ============================================================
cli.post("/api/admin/pausar", headers=ADMIN, json={"id": ID_A, "activo": False})
FAKE.mensajes.clear()
cli.post("/webhook", json=evento(PAG_A, "8200", "hola"))
cli.post("/webhook", json=evento(PAG_B, "8200", "hola"))
check("Pausado: el bot de A deja de contestar y B sigue andando", not respuestas_a("tok-a", "8200") and respuestas_a("tok-b", "8200"))
r = cli.get("/api/panel/resumen", headers=h("clave-tienda-a"))
check("Pausado: el panel de A avisa que el servicio está pausado", r.status_code == 403 and r.json().get("error") == "pausado")
check("Guaranístore no se puede pausar desde el admin", not cli.post("/api/admin/pausar", headers=ADMIN, json={"id": "principal", "activo": False}).json().get("ok"))
cli.post("/api/admin/pausar", headers=ADMIN, json={"id": ID_A, "activo": True})
cli.post("/webhook", json=evento(PAG_A, "8200", "volví"))
check("Despausado: A vuelve a contestar", respuestas_a("tok-a", "8200"))

# "borrar mis datos"
cli.post("/webhook", json=evento(PAG_B, "8300", "hola"))
cli.post("/webhook", json=evento(PAG_B, "8300", "quiero pedir"))
cli.post("/webhook", json=evento(PAG_B, "8301", "hola, soy otro"))
antes = len(FAKE.bases[BASE_B]["Conversaciones"])
FAKE.telegram.clear()
cli.post("/webhook", json=evento(PAG_B, "8300", "Por favor, BORRAR MIS DATOS"))
convs_b = [r["fields"]["contact_id"] for r in FAKE.bases[BASE_B]["Conversaciones"].values()]
pedido_8300 = [r["fields"] for r in FAKE.bases[BASE_B]["Pedidos"].values() if r["fields"]["Nombre"] == "Ana"]
check("«Borrar mis datos» borra la charla del cliente en Airtable y su memoria",
      "8300" not in convs_b and "hist:%s:8300" % ID_B not in FAKE.redis and antes > len(convs_b), convs_b)
check("…le saca su id a sus pedidos, pero el pedido queda para el negocio",
      pedido_8300 and all(p["Contacto"] != "8300" for p in pedido_8300), pedido_8300)
check("…no toca a los otros clientes y le confirma al cliente",
      "8301" in convs_b and respuestas_a("tok-b", "8300")[-1] == bot.MSG_BORRADO and FAKE.telegram and FAKE.telegram[0][1] == "chat-b")

FAKE.upstash_caido = True
bot._REG["ts"] = 0.0
FAKE.mensajes.clear()
cli.post("/webhook", json=evento(PAG_GUARANI, "8400", "hola"))
cli.post("/webhook", json=evento(PAG_C, "8400", "hola"))
FAKE.upstash_caido = False
check("Con Upstash caído, Guaranístore y los clientes siguen contestando", respuestas_a("tok-guarani", "8400") and respuestas_a("tok-c", "8400"))

# firma de Meta
bot.VERIFICAR_FIRMA = True
FAKE.mensajes.clear()
crudo = json.dumps(evento(PAG_C, "8500", "hola")).encode()
cli.post("/webhook", content=crudo, headers={"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=trucha"})
import hmac as _hmac, hashlib as _hashlib
firma = "sha256=" + _hmac.new(b"secreto-app", crudo.replace(b"8500", b"8501"), _hashlib.sha256).hexdigest()
cli.post("/webhook", content=crudo.replace(b"8500", b"8501"), headers={"Content-Type": "application/json", "X-Hub-Signature-256": firma})
bot.VERIFICAR_FIRMA = False
check("Con VERIFICAR_FIRMA=1 solo atiende mensajes firmados por Meta", not respuestas_a("tok-c", "8500") and respuestas_a("tok-c", "8501"))

r = cli.post("/api/admin/borrar-negocio", headers=ADMIN, json={"id": ID_C}).json()
FAKE.mensajes.clear()
cli.post("/webhook", json=evento(PAG_C, "8600", "hola"))
check("Borrar un negocio lo saca del bot", r.get("ok") and not respuestas_a("tok-c", "8600") and len(cli.get("/api/admin/negocios", headers=ADMIN).json()["negocios"]) == 3)


# ============================================================
print("\n== 6. Le contesta a Meta al instante ==")
# ============================================================
def puerto_libre():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

import uvicorn
puerto = puerto_libre()
servidor = uvicorn.Server(uvicorn.Config(bot.app, host="127.0.0.1", port=puerto, log_level="warning"))
threading.Thread(target=servidor.run, daemon=True).start()
for _ in range(100):
    if servidor.started: break
    time.sleep(0.05)
FAKE.mensajes.clear(); FAKE.demora_gemini = 1.5
pedido = urllib.request.Request("http://127.0.0.1:%d/webhook" % puerto, data=json.dumps(evento(PAG_B, "8700", "hola")).encode(),
                                headers={"Content-Type": "application/json"}, method="POST")
t0 = time.time(); codigo = urllib.request.urlopen(pedido, timeout=10).status; demora = time.time() - t0
contesto_antes = bool(respuestas_a("tok-b", "8700"))
for _ in range(80):
    if respuestas_a("tok-b", "8700"): break
    time.sleep(0.05)
FAKE.demora_gemini = 0.0
check("Meta recibe el «OK» enseguida aunque Gemini tarde (%.2fs)" % demora, codigo == 200 and demora < 0.5 and not contesto_antes)
check("…y el cliente igual recibe su respuesta un ratito después", respuestas_a("tok-b", "8700"))
servidor.should_exit = True


# ============================================================
total = len(RESULTADOS); bien = sum(1 for _, ok in RESULTADOS if ok)
print("\n%d de %d chequeos pasaron." % (bien, total))
sys.exit(0 if bien == total else 1)
