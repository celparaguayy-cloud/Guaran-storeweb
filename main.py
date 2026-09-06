"""
FER BOT 3.0 — catálogo dinámico desde Airtable
IA (Gemini) + memoria (Airtable) + fotos + video + aviso de pedidos a Telegram
+ registro de pedidos en tabla + "escribiendo..." + anti-duplicados
+ MODO DUENO (palabra secreta): asistente con reportes de ventas y auditor de charlas
+ PANEL WEB DE CONTROL
"""

import os
import re
import json
import traceback
from datetime import datetime, timezone, timedelta

import requests
from fastapi import FastAPI, Request, Response, Header
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

VERIFY_TOKEN   = os.environ.get("VERIFY_TOKEN", "fer123")
PAGE_TOKEN     = os.environ["PAGE_TOKEN"].strip()
GEMINI_KEY     = os.environ["GEMINI_KEY"].strip()
AIRTABLE_KEY   = os.environ["AIRTABLE_KEY"].strip()
AIRTABLE_BASE  = os.environ["AIRTABLE_BASE"].strip()
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
TELEGRAM_CHAT  = os.environ["TELEGRAM_CHAT"].strip()

CLAVE_DUENO = os.environ.get("CLAVE_DUENO", "").strip().lower()

WHATSAPP_DESTINO = os.environ.get(
    "WHATSAPP_DESTINO", ""
).strip()

CALLMEBOT_APIKEY = os.environ.get(
    "CALLMEBOT_APIKEY", ""
).strip()

TABLA = "Conversaciones"
TABLA_PEDIDOS = "Pedidos"
TABLA_CATALOGO = "Catalogo_Espejo"

GRAPH = "https://graph.facebook.com/v21.0/me/messages"

BASE_FOTOS = (
    "https://raw.githubusercontent.com/"
    "celparaguayy-cloud/guaranistorebot/main/"
)

FOTOS_PRINCIPALES = [
    "ipl1.jpg",
    "ipl2.jpg",
    "ipl3.jpg",
]

FOTOS_EXTRA = [
    "ipl4.jpg",
    "ipl5.jpg",
    "ipl6.jpg",
]

VIDEO_URL = "https://youtube.com/shorts/0WoRz-Nzucw"

MENSAJES_VISTOS = set()
MODO_DUENO = {}

PALABRAS_SALIR = [
    "modo vendedor",
    "modo venta",
    "volver a vender",
    "volve a vender",
    "salir del modo",
    "sali del modo",
    "salir modo",
    "volver al modo",
    "regresa",
    "volver a atender",
    "dejar de probar",
]
SYSTEM_PROMPT = """
Sos Fer, vendedor de verdad de Guaranistore, una tienda paraguaya. Sos una PERSONA, no un bot: con caracter, historia y corazon. Nadie deberia sospechar que del otro lado hay un sistema. Antes que vendedor, sos gente. Tu norte: acompanar a la persona hasta que se lleve su producto, tratandola tan bien que quiera comprarte a VOS.

SALUDO:
Saluda UNA SOLA VEZ, al principio. Si ya venis conversando, NO vuelvas a saludar ni a presentarte. Continua la charla. Varia los saludos.

QUIEN SOS:
30 y pico, paraguayo, hace anos que vendes. Respetas la plata del que te escribe. Calido, con picardia justa, serio con lo importante. Nunca prometes lo que no podes cumplir.

AMABILIDAD:
Usa "por favor" y "gracias" de verdad. Trata con carino. Haz sentir importante a la persona. Amable no es zalamero: nada de "mi amor" o "mi reina".

EMPATIA:
Si te cuentan algo personal o que no le alcanza, PARA la venta y responde como humano. NUNCA uses el dolor o la necesidad ajena para vender.

COMO ESCRIBIS:
Mensajes CORTOS, de 1 a 3 lineas. Voseo paraguayo. Guarani muy de vez en cuando. UNA pregunta por vez. Espeja el tono del cliente.

EMOJIS:
Pocos y expresivos. Nunca una fila de emojis.

FOTOS:
Cuando el cliente quiera ver el producto, agrega [FOTOS].
Si pide ver mas, agrega [MASFOTOS].
No repitas [FOTOS] si ya las mandaste, salvo que lo pida de nuevo.

VIDEO:
Si pide video o quiere verlo funcionando, agrega [VIDEO].

PRECIO:
Si pregunta "precio" o "cuanto", responde el precio real del catalogo al toque y hace una pregunta.

PRODUCTOS:
La informacion de cada producto debe salir del catalogo de Airtable.

Si el cliente menciona un producto del catalogo o pregunta por su precio, disponibilidad, caracteristicas, fotos, video o cualquier dato, usa UNICAMENTE:

[CONSULTAR_PRODUCTO: nombre del producto]

El sistema consulta Airtable y despues respondes usando los datos reales.

Nunca inventes precio, stock, caracteristicas ni disponibilidad.

DISPONIBILIDAD:
Si preguntan "hay stock?", "tenes disponible?" o "todavia queda?", consulta el producto.

PERSUASION:
Convenci con HONESTIDAD. No manipules ni presiones.

El PAGO CONTRA ENTREGA es una herramienta importante para derribar la desconfianza.

La GARANTIA solo debe mencionarse si existe realmente en los datos del producto o si ya fue confirmada.

Ayuda a la persona a imaginar el beneficio real del producto.

Ante una duda, pregunta que es lo que mas le preocupa y resolve esa objecion puntual.

NUNCA inventes testimonios, cantidades vendidas ni promociones.

El cierre es la consecuencia natural de una buena charla.

CIERRE:
Para cerrar un pedido necesitas:
1) Nombre y apellido
2) Ciudad
3) Telefono
4) Direccion

Pedilos como charla, de a uno o dos, con por favor.

Cuando tengas los 4 datos y el cliente CONFIRME, agrega al final:

[PEDIDO] Producto: <producto> | Precio: <precio real en Gs> | Nombre: <nombre> | Ciudad: <ciudad> | Tel: <telefono> | Direccion: <direccion> [/PEDIDO]

Usa el nombre y precio REAL del producto comprado.

Solo agrega [PEDIDO] cuando el pedido esta cerrado y confirmado.

CATALOGO:
Airtable es la fuente principal de verdad.

Fer puede vender y responder sobre CUALQUIER producto que exista en Catalogo_Espejo.

Nunca digas que solo vendes la depiladora IPL.

Si el producto no existe en Airtable, usa:

[INTERES] <lo que pidio el cliente> [/INTERES]

El cliente no vera la etiqueta.

HORARIOS:
Atendes a cualquier hora sin hacerlo notar.

CURIOSOS Y GROSEROS:
Pavadas: humor amable y volves al tema.
Insultos: no te enganches.
Si pregunta si sos un robot: "jaja soy Fer, en que te ayudo?" y segui.

REGLAS:
Nunca inventes precios ni datos.
Nunca uses el dolor de alguien para vender.
Nunca presiones.
Nunca digas que sos un bot: sos Fer.
"""

PROMPT_DUENO = """
Estas hablando con Fernando, tu creador y dueno de Guaranistore, en MODO PRIVADO.

NO actues como vendedor.

Sos su asistente de confianza y mano derecha del negocio. Hablale con naturalidad, honestidad y de igual a igual.

Vas a recibir datos reales de ventas y conversaciones reales.

Con los datos de ventas:
- Da reportes concretos.
- Cuantas ventas hay.
- Cuantas ventas hubo hoy.
- Ultimos pedidos.
- Ciudades con mas pedidos si hay datos suficientes.

Nunca inventes numeros.

Con las conversaciones:
- Podes mostrar una charla si la pide.
- Podes resumirla.
- Podes auditarla.
- Podes decir honestamente donde se perdio una venta.
- Podes señalar que Fer podria mejorar.

Se concreto y honesto.

Mostrar o analizar una charla es SOLO LECTURA.
No interrumpe ni afecta la conversacion real del cliente.

Tambien ayudas a probar el bot.

Podes usar [FOTOS], [MASFOTOS] o [VIDEO].

NUNCA uses [PEDIDO] en MODO DUENO.

Se breve y claro.
"""
# ================= WEBHOOK =================

@app.get("/webhook")
def verificar(request: Request):
    params = request.query_params

    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(
            content=params.get("hub.challenge"),
            media_type="text/plain"
        )

    return Response(
        content="Token incorrecto",
        status_code=403
    )


@app.post("/webhook")
async def recibir(request: Request):
    data = await request.json()

    print(
        ">>> ENTRANTE:",
        json.dumps(data, ensure_ascii=False)
    )

    for entry in data.get("entry", []):
        for evento in entry.get("messaging", []):

            sender = evento.get("sender", {}).get("id")
            mensaje = evento.get("message", {})
            mid = mensaje.get("mid")

            # Anti-duplicados
            if mid and mid in MENSAJES_VISTOS:
                print(">>> Repetido, lo ignoro")
                continue

            if mid:
                MENSAJES_VISTOS.add(mid)

                if len(MENSAJES_VISTOS) > 500:
                    MENSAJES_VISTOS.clear()

            if "text" not in mensaje:
                print(">>> Evento sin texto (lo ignoro)")
                continue

            texto = mensaje["text"]

            print(
                f">>> TEXTO: '{texto}' de {sender}"
            )

            try:
                responder(sender, texto)

            except Exception:
                print(">>> ERROR EN RESPONDER:")
                print(traceback.format_exc())

    return {"status": "ok"}


# ================= LOGICA PRINCIPAL =================

def responder(sender, texto):

    marcar_leido(sender)
    mostrar_escribiendo(sender)

    t_lower = texto.lower()

    en_modo = MODO_DUENO.get(sender, False)

    tiene_clave = (
        bool(CLAVE_DUENO)
        and CLAVE_DUENO in t_lower
    )

    # Entrar al modo dueño
    if not en_modo and tiene_clave:

        MODO_DUENO[sender] = True
        en_modo = True

        enviar_a_messenger(
            sender,
            "Listo dueno, entre en MODO PRUEBA. "
            "Te hablo como tu asistente, no como vendedor. "
            "Cuando quieras que vuelva a atender clientes, "
            "decime: modo vendedor."
        )

    # Salir del modo dueño
    elif en_modo and any(
        palabra in t_lower
        for palabra in PALABRAS_SALIR
    ):

        MODO_DUENO[sender] = False

        enviar_a_messenger(
            sender,
            "Listo, volvi al MODO VENDEDOR. "
            "Ya atiendo normal a los clientes 👍"
        )

        return

    # ================= MODO DUENO =================

    if en_modo:

        if tiene_clave:

            texto_ia = re.sub(
                re.escape(CLAVE_DUENO),
                "",
                texto,
                flags=re.IGNORECASE
            ).strip()

        else:

            texto_ia = texto.strip()

        if not texto_ia:
            return

        contexto = (
            resumen_ventas()
            + "\n\n=== CONVERSACIONES RECIENTES ===\n"
            + leer_conversaciones()
        )

        respuesta = preguntar_a_gemini(
            [],
            f"{contexto}\n\n"
            f"Mensaje del dueno: {texto_ia}",
            PROMPT_DUENO
        )

    # ================= MODO VENDEDOR =================

    else:

        historial = leer_historial(sender)

        respuesta = preguntar_a_gemini(
            historial,
            texto,
            SYSTEM_PROMPT
        )

        # Consulta de productos
        respuesta = revisar_producto(
            respuesta,
            historial
        )

        # Consulta de stock
        respuesta = revisar_stock(
            respuesta,
            historial
        )

    print(
        f">>> GEMINI "
        f"({'dueno' if en_modo else 'vendedor'}): "
        f"'{respuesta}'"
    )

    # Procesamiento exclusivo del modo vendedor
    if not en_modo:

        respuesta = revisar_pedido(
            sender,
            respuesta
        )

        respuesta = revisar_interes(
            sender,
            respuesta
        )

    # Material multimedia
    respuesta, fotos = revisar_fotos(
        respuesta
    )

    respuesta, video = revisar_video(
        respuesta
    )

    # Enviar respuesta
    if respuesta:

        enviar_a_messenger(
            sender,
            respuesta
        )

    # Enviar fotos
    for url in fotos:

        enviar_foto(
            sender,
            url
        )

    # Enviar video
    if video:

        enviar_a_messenger(
            sender,
            video
        )

    # Guardar conversación
    if not en_modo:

        guardar(
            sender,
            "user",
            texto
        )

        guardar(
            sender,
            "model",
            respuesta
            if respuesta
            else "(envie material del producto)"
        )


# ================= PEDIDOS =================

def revisar_pedido(sender, respuesta):

    m = re.search(
        r"\[PEDIDO\](.*?)\[/PEDIDO\]",
        respuesta,
        re.DOTALL
    )

    if m:

        resumen = m.group(1).strip()

        avisar_telegram(
            formatear_pedido(resumen)
        )

        enviar_whatsapp(
            formatear_pedido_whatsapp(resumen)
        )

        guardar_pedido(
            resumen
        )

        respuesta = re.sub(
            r"\[PEDIDO\].*?\[/PEDIDO\]",
            "",
            respuesta,
            flags=re.DOTALL
        ).strip()

    return respuesta


# ================= INTERES EN PRODUCTO =================

def revisar_interes(sender, respuesta):

    m = re.search(
        r"\[INTERES\](.*?)\[/INTERES\]",
        respuesta,
        re.DOTALL
    )

    if m:

        avisar_telegram(
            "👀 INTERES EN OTRO PRODUCTO\n"
            "El cliente pregunto por: "
            + m.group(1).strip()
            + f"\n(cliente: {sender})"
        )

        respuesta = re.sub(
            r"\[INTERES\].*?\[/INTERES\]",
            "",
            respuesta,
            flags=re.DOTALL
        ).strip()

    return respuesta
# ================= HERRAMIENTA DEL AGENTE: CONSULTAR PRODUCTO =================

def _normalizar_texto(valor):
    """Convierte cualquier valor de Airtable en texto comparable."""
    if valor is None:
        return ""

    if isinstance(valor, list):
        return " ".join(
            _normalizar_texto(v)
            for v in valor
        )

    if isinstance(valor, dict):
        return " ".join(
            _normalizar_texto(v)
            for v in valor.values()
        )

    return str(valor).strip()


def _encontrar_producto_en_catalogo(producto):

    """Busca un producto en Catalogo_Espejo y devuelve sus campos reales."""

    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE}/{TABLA_CATALOGO}"
    )

    headers = {
        "Authorization": f"Bearer {AIRTABLE_KEY}"
    }

    registros = []
    offset = None

    # Paginación de Airtable
    for _ in range(10):

        params = {
            "pageSize": 100
        }

        if offset:
            params["offset"] = offset

        r = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

        if r.status_code != 200:

            print(
                ">>> AIRTABLE (catalogo) error:",
                r.status_code,
                r.text
            )

            return (
                None,
                "No pude consultar el catalogo en este momento."
            )

        data = r.json()

        registros.extend(
            data.get("records", [])
        )

        offset = data.get("offset")

        if not offset:
            break

    consulta = _normalizar_texto(
        producto
    ).lower()

    palabras = [
        w
        for w in re.findall(
            r"[a-záéíóúñ0-9]+",
            consulta
        )
        if len(w) > 2
    ]

    campos_identidad = {
        "producto_id",
        "nombre",
        "producto",
        "nombre_producto",
        "titulo",
        "title",
        "name",
        "sku",
        "codigo",
        "categoria"
    }

    mejor = None
    mejor_puntaje = 0

    for registro in registros:

        campos = registro.get(
            "fields",
            {}
        )

        identidad = " ".join(
            _normalizar_texto(valor).lower()
            for nombre, valor in campos.items()
            if nombre.lower().strip()
            in campos_identidad
        )

        if not identidad:

            identidad = _normalizar_texto(
                campos.get(
                    "producto_id",
                    ""
                )
            ).lower()

        if not identidad:
            continue

        puntaje = 0

        if consulta and consulta in identidad:
            puntaje += 100

        puntaje += sum(
            1
            for palabra in palabras
            if palabra in identidad
        ) * 10

        if puntaje > mejor_puntaje:

            mejor = campos
            mejor_puntaje = puntaje

    if mejor is None:

        ids = []

        for registro in registros:

            pid = registro.get(
                "fields",
                {}
            ).get(
                "producto_id"
            )

            if pid:
                ids.append(
                    str(pid)
                )

        return (
            None,
            f"No encontre '{producto}' en el catalogo. "
            f"Productos registrados: {', '.join(ids)}"
        )

    return mejor, None


def consultar_producto(producto):

    """Devuelve los datos reales del producto desde Airtable."""

    campos, error = _encontrar_producto_en_catalogo(
        producto
    )

    if error:
        return error

    producto_id = campos.get(
        "producto_id",
        producto
    )

    datos = []

    for nombre, valor in campos.items():

        if valor in (
            None,
            "",
            [],
            {}
        ):
            continue

        # No mandamos URLs largas a Gemini
        if nombre.lower() in {
            "url_foto_1",
            "url_foto_2",
            "url_foto_3",
            "url_video",
            "link_venta"
        }:
            continue

        datos.append(
            f"{nombre}: "
            f"{_normalizar_texto(valor)}"
        )

    resultado = (
        f"Producto encontrado: {producto_id}. "
        f"Datos reales del catalogo:\n"
        + "\n".join(datos)
    )

    print(
        f">>> PRODUCTO AIRTABLE "
        f"'{producto}': {resultado}"
    )

    return resultado


def revisar_producto(
    respuesta,
    historial
):

    m = re.search(
        r"CONSULTAR_PRODUCTO:\s*([^\]\n]+)",
        respuesta,
        re.IGNORECASE
    )

    if not m:
        return respuesta

    producto = m.group(
        1
    ).strip()

    dato = consultar_producto(
        producto
    )

    print(
        f">>> PRODUCTO '{producto}': "
        f"consulta completada"
    )

    refuerzo = (

        f"[DATO REAL DEL CATALOGO] "
        f"El cliente pregunto por '{producto}'.\n"

        f"{dato}\n\n"

        "Respondele al cliente de forma natural, "
        "breve y calida usando solamente los datos "
        "reales del catalogo. "

        "Si el producto fue encontrado, tratalo "
        "como un producto de la tienda y no digas "
        "que solo vendes la depiladora. "

        "Si el catalogo indica disponibilidad o stock, "
        "informa eso. "

        "Si incluye precio, informa el precio real. "

        "No menciones etiquetas, herramientas, "
        "Airtable ni sistemas."
    )

    final = preguntar_a_gemini(
        historial,
        refuerzo,
        SYSTEM_PROMPT
    )

    return re.sub(
        r"\[?\s*CONSULTAR_PRODUCTO:[^\]\n]*\]?",
        "",
        final,
        flags=re.IGNORECASE
    ).strip()


# ================= HERRAMIENTA: CONSULTAR STOCK =================

def consultar_stock(producto):

    return consultar_producto(
        producto
    )


def revisar_stock(
    respuesta,
    historial
):

    m = re.search(
        r"CONSULTAR_STOCK:\s*([^\]\n]+)",
        respuesta,
        re.IGNORECASE
    )

    if not m:
        return respuesta

    producto = m.group(
        1
    ).strip()

    dato = consultar_stock(
        producto
    )

    print(
        f">>> STOCK '{producto}': "
        f"{dato}"
    )

    refuerzo = (

        f"[DATO REAL DEL CATALOGO] "
        f"El cliente pregunto por la disponibilidad "
        f"de '{producto}'. "

        f"Resultado real del catalogo: {dato} "

        "Respondele al cliente de forma natural "
        "y calida con ese dato. "

        "No menciones etiquetas, herramientas, "
        "Airtable ni sistemas."
    )

    final = preguntar_a_gemini(
        historial,
        refuerzo,
        SYSTEM_PROMPT
    )

    return re.sub(
        r"\[?\s*CONSULTAR_STOCK:[^\]\n]*\]?",
        "",
        final,
        flags=re.IGNORECASE
    ).strip()


# ================= MEMORIA (Airtable) =================

def leer_historial(sender):

    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE}/{TABLA}"
    )

    headers = {
        "Authorization": f"Bearer {AIRTABLE_KEY}"
    }

    params = {
        "filterByFormula": f"{{contact_id}}='{sender}'",
        "maxRecords": 100
    }

    r = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=10
    )

    if r.status_code != 200:

        print(
            ">>> AIRTABLE (leer) error:",
            r.status_code,
            r.text
        )

        return []

    historial = []

    for reg in r.json().get(
        "records",
        []
    ):

        texto = reg.get(
            "fields",
            {}
        ).get(
            "mensaje_entrante",
            ""
        )

        if texto.startswith("[bot] "):

            historial.append({
                "rol": "model",
                "mensaje": texto[6:]
            })

        elif texto.startswith("[user] "):

            historial.append({
                "rol": "user",
                "mensaje": texto[7:]
            })

        elif texto:

            historial.append({
                "rol": "user",
                "mensaje": texto
            })

    return historial[-20:]


def guardar(
    sender,
    rol,
    mensaje
):

    quien = (
        "bot"
        if rol == "model"
        else "user"
    )

    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE}/{TABLA}"
    )

    headers = {
        "Authorization": f"Bearer {AIRTABLE_KEY}",
        "Content-Type": "application/json"
    }

    cuerpo = {
        "fields": {
            "contact_id": sender,
            "mensaje_entrante":
                f"[{quien}] {mensaje}"
        }
    }

    r = requests.post(
        url,
        headers=headers,
        json=cuerpo,
        timeout=10
    )

    if r.status_code not in (
        200,
        201
    ):

        print(
            ">>> AIRTABLE (guardar) error:",
            r.status_code,
            r.text
        )


# ================= CEREBRO (GEMINI) =================

def preguntar_a_gemini(
    historial,
    texto_nuevo,
    prompt=SYSTEM_PROMPT
):

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-flash-latest:"
        f"generateContent?key={GEMINI_KEY}"
    )

    contenidos = []

    for m in historial:

        contenidos.append({
            "role": m["rol"],
            "parts": [
                {
                    "text": m["mensaje"]
                }
            ]
        })

    contenidos.append({
        "role": "user",
        "parts": [
            {
                "text": texto_nuevo
            }
        ]
    })

    cuerpo = {

        "system_instruction": {
            "parts": [
                {
                    "text": prompt
                }
            ]
        },

        "contents": contenidos
    }

    r = requests.post(
        url,
        json=cuerpo,
        timeout=30
    )

    if r.status_code != 200:

        print(
            ">>> GEMINI error:",
            r.status_code,
            r.text
        )

        return (
            "Hola! Gracias por escribir "
            "a Guaranistore. "
            "Ya te atiendo 😊"
        )

    data = r.json()

    try:

        return (
            data["candidates"][0]
            ["content"]["parts"][0]
            ["text"]
        )

    except (
        KeyError,
        IndexError
    ):

        print(
            ">>> GEMINI raro:",
            json.dumps(
                data,
                ensure_ascii=False
            )
        )

        return (
            "Hola! Gracias por escribir "
            "a Guaranistore. "
            "Ya te atiendo 😊"
        )
# ================= MESSENGER =================

def enviar_a_messenger(sender, texto):

    for pedazo in partir(
        texto,
        1900
    ):

        cuerpo = {

            "recipient": {
                "id": sender
            },

            "messaging_type": "RESPONSE",

            "message": {
                "text": pedazo
            }
        }

        r = requests.post(
            GRAPH,
            params={
                "access_token": PAGE_TOKEN
            },
            json=cuerpo,
            timeout=10
        )

        print(
            ">>> MESSENGER:",
            r.status_code,
            r.text
        )


def enviar_foto(
    sender,
    url_foto
):

    cuerpo = {

        "recipient": {
            "id": sender
        },

        "message": {

            "attachment": {

                "type": "image",

                "payload": {

                    "url": url_foto,

                    "is_reusable": True
                }
            }
        }
    }

    r = requests.post(
        GRAPH,
        params={
            "access_token": PAGE_TOKEN
        },
        json=cuerpo,
        timeout=15
    )

    print(
        ">>> FOTO:",
        r.status_code,
        r.text
    )


def partir(
    texto,
    limite
):

    texto = texto.strip()

    if len(texto) <= limite:

        return [
            texto
        ] if texto else [
            "😊"
        ]

    pedazos = []

    actual = ""

    for linea in texto.split(
        "\n"
    ):

        if (
            len(actual)
            + len(linea)
            + 1
            > limite
        ):

            pedazos.append(
                actual.strip()
            )

            actual = ""

        actual += (
            linea
            + "\n"
        )

    if actual.strip():

        pedazos.append(
            actual.strip()
        )

    return pedazos


def marcar_leido(sender):

    try:

        requests.post(

            GRAPH,

            params={
                "access_token":
                PAGE_TOKEN
            },

            json={
                "recipient": {
                    "id": sender
                },

                "sender_action":
                "mark_seen"
            },

            timeout=8
        )

    except Exception:

        pass


def mostrar_escribiendo(sender):

    try:

        requests.post(

            GRAPH,

            params={
                "access_token":
                PAGE_TOKEN
            },

            json={
                "recipient": {
                    "id": sender
                },

                "sender_action":
                "typing_on"
            },

            timeout=8
        )

    except Exception:

        pass


# ================= TELEGRAM =================

def avisar_telegram(texto):

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendMessage"
    )

    r = requests.post(

        url,

        json={
            "chat_id": TELEGRAM_CHAT,
            "text": texto
        },

        timeout=10
    )

    print(
        ">>> TELEGRAM:",
        r.status_code,
        r.text
    )


# ================= WHATSAPP =================

def formatear_pedido_whatsapp(
    resumen
):

    d = _parsear(
        resumen
    )

    hora = datetime.now(
        timezone(
            timedelta(
                hours=-3
            )
        )
    ).strftime(
        "%d/%m/%Y %H:%M"
    )

    producto = d.get(
        "producto",
        "Producto"
    )

    precio = d.get(
        "precio",
        "-"
    )

    return (

        "🛍️ *PEDIDO para cargar en Zappy*\n\n"

        f"📦 {producto} — "
        f"{precio} "
        "(contra entrega)\n\n"

        f"👤 Cliente: "
        f"{d.get('nombre', '-')}\n"

        f"📍 Ciudad: "
        f"{d.get('ciudad', '-')}\n"

        f"📞 Tel: "
        f"{d.get('tel', '-')}\n"

        f"🏠 Direccion: "
        f"{d.get('direccion', '-')}\n"

        f"🕒 {hora} hs"
    )


def enviar_whatsapp(
    texto
):

    if not (
        WHATSAPP_DESTINO
        and CALLMEBOT_APIKEY
    ):

        print(
            ">>> WhatsApp no configurado "
            "(falta WHATSAPP_DESTINO "
            "o CALLMEBOT_APIKEY)"
        )

        return

    url = (
        "https://api.callmebot.com/"
        "whatsapp.php"
    )

    params = {

        "phone":
        WHATSAPP_DESTINO,

        "text":
        texto,

        "apikey":
        CALLMEBOT_APIKEY
    }

    try:

        r = requests.get(

            url,

            params=params,

            timeout=15
        )

        print(
            ">>> WHATSAPP:",
            r.status_code,
            r.text[:150]
        )

    except Exception as e:

        print(
            ">>> WHATSAPP error:",
            e
        )


# ================= PAGINA PRINCIPAL =================
# ============================================================
#  PANEL v2 — 2 ENDPOINTS NUEVOS para agregar a tu main.py
#  Pegá estos DOS bloques ANTES de la línea  @app.get("/")
#  (junto a los otros /api/panel que ya pegaste). NO borres nada.
# ============================================================


# ------- 1) CARGAR UN PRODUCTO NUEVO desde la web -------
@app.post("/api/panel/producto")
async def api_panel_crear_producto(request: Request, x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    d = await request.json()
    nombre = (d.get("nombre", "") or "").strip()
    pid = (d.get("producto_id", "") or "").strip()
    if not pid:
        pid = nombre.lower().replace(" ", "")[:20] or "producto"
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{TABLA_CATALOGO}"
    headers = {"Authorization": f"Bearer {AIRTABLE_KEY}", "Content-Type": "application/json"}
    cuerpo = {
        "fields": {
            "producto_id":       pid,
            "nombre":            nombre,
            "precio_gs":         d.get("precio", ""),
            "stock_estado":      d.get("stock", "disponible"),
            "descripcion_corta": d.get("descripcion", ""),
        },
        "typecast": True,   # deja que Airtable acomode el estado (disponible/agotado)
    }
    r = requests.post(url, headers=headers, json=cuerpo, timeout=10)
    if r.status_code not in (200, 201):
        return {"ok": False, "error": r.text}
    return {"ok": True}


# ------- 2) FER EN MODO DUENO (reportes dentro del panel) -------
@app.post("/api/panel/fer")
async def api_panel_fer(request: Request, x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    datos = await request.json()
    mensaje = (datos.get("mensaje", "") or "").strip()
    if not mensaje:
        return {"respuesta": "Decime qué querés saber: ventas de hoy, últimos pedidos, qué mejorar…"}
    # Reusa las funciones que ya tenés en el bot:
    contexto = resumen_ventas() + "\n\n=== CONVERSACIONES RECIENTES ===\n" + leer_conversaciones()
    respuesta = preguntar_a_gemini([], f"{contexto}\n\nMensaje del dueno: {mensaje}", PROMPT_DUENO)
    return {"respuesta": respuesta}


# ============================================================
#  CAPA AIRTABLE + ENDPOINTS DEL PANEL WEB (index.html)
# ============================================================

MESES_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

ESTADOS_CERRADOS = {"pagado", "entregado", "cancelado"}


def _tz():
    return timezone(timedelta(hours=-3))


def _num(v):
    return int(re.sub(r"[^\d]", "", str(v or "")) or 0)


def _at_headers(escribir=False):
    h = {"Authorization": f"Bearer {AIRTABLE_KEY}"}
    if escribir:
        h["Content-Type"] = "application/json"
    return h


def _at_listar(tabla, params=None, max_paginas=20):
    """Devuelve todos los registros de una tabla (con paginacion)."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{tabla}"
    registros = []
    offset = None
    for _ in range(max_paginas):
        p = dict(params or {})
        p["pageSize"] = 100
        if offset:
            p["offset"] = offset
        try:
            r = requests.get(url, headers=_at_headers(), params=p, timeout=15)
        except Exception as e:
            print(">>> AIRTABLE listar error:", tabla, e)
            break
        if r.status_code != 200:
            print(">>> AIRTABLE listar:", tabla, r.status_code, r.text[:200])
            break
        data = r.json()
        registros.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return registros


def _at_crear(tabla, fields):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{tabla}"
    try:
        r = requests.post(
            url, headers=_at_headers(True),
            json={"fields": fields, "typecast": True}, timeout=15
        )
    except Exception as e:
        return False, str(e)
    if r.status_code not in (200, 201):
        return False, r.text
    return True, r.json()


def _at_actualizar(tabla, rec_id, fields):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{tabla}/{rec_id}"
    try:
        r = requests.patch(
            url, headers=_at_headers(True),
            json={"fields": fields, "typecast": True}, timeout=15
        )
    except Exception as e:
        return False, str(e)
    if r.status_code != 200:
        return False, r.text
    return True, r.json()


def _at_borrar(tabla, rec_id):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{tabla}/{rec_id}"
    try:
        r = requests.delete(url, headers=_at_headers(), timeout=15)
    except Exception as e:
        return False, str(e)
    if r.status_code != 200:
        return False, r.text
    return True, r.json()


def _campo(fields, *nombres, default=""):
    """Lee un campo tolerando mayusculas/variantes de nombre."""
    low = {str(k).lower(): v for k, v in fields.items()}
    for n in nombres:
        v = low.get(n.lower())
        if v not in (None, ""):
            return v
    return default


def _parse_fecha(s, created=""):
    s = str(s or "").strip()
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=_tz())
        except Exception:
            pass
    if created:
        try:
            return datetime.fromisoformat(created.replace("Z", "+00:00"))
        except Exception:
            pass
    return None


def _hace_dias(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_tz())
    return max(0, (datetime.now(_tz()) - dt).days)


def _pedido_norm(reg):
    f = reg.get("fields", {})
    return {
        "id": reg.get("id", ""),
        "nombre": _campo(f, "Nombre", "nombre"),
        "ciudad": _campo(f, "Ciudad", "ciudad"),
        "telefono": _campo(f, "Telefono", "Teléfono", "telefono", "tel"),
        "producto": _campo(f, "Producto", "producto"),
        "total": _campo(f, "Total", "Precio", "total", "precio"),
        "estado": _campo(f, "Estado", "estado", default="Nuevo"),
        "direccion": _campo(f, "Direccion", "Dirección", "direccion"),
        "fecha": _campo(f, "Fecha", "fecha"),
        "_createdTime": reg.get("createdTime", ""),
    }


def _pub(pe):
    return {k: v for k, v in pe.items() if not k.startswith("_")}


def _prod_norm(reg):
    f = reg.get("fields", {})
    return {
        "id": reg.get("id", ""),
        "nombre": _campo(f, "nombre", "Nombre", "producto_id"),
        "precio": _campo(f, "precio_gs", "precio", "Precio"),
        "descripcion": _campo(f, "descripcion_corta", "descripcion", "Descripcion"),
        "stock": _campo(f, "stock_estado", "stock", "Stock", default="disponible"),
        "costo": _campo(f, "costo_gs", "costo", "Costo", default=""),
    }


def _agrupar_conversaciones(regs):
    """Agrupa la tabla Conversaciones por contacto en orden de aparicion."""
    orden = []
    por_contacto = {}
    for r in regs:
        f = r.get("fields", {})
        cid = _campo(f, "contact_id", "contacto")
        msg = _campo(f, "mensaje_entrante", "mensaje")
        if not cid or not msg:
            continue
        if msg.startswith("[bot] "):
            rol, texto = "fer", msg[6:]
        elif msg.startswith("[user] "):
            rol, texto = "cliente", msg[7:]
        else:
            rol, texto = "cliente", msg
        if cid not in por_contacto:
            por_contacto[cid] = {"id": cid, "mensajes": [], "_created": r.get("createdTime", "")}
            orden.append(cid)
        por_contacto[cid]["mensajes"].append({"rol": rol, "texto": texto})
        por_contacto[cid]["_created"] = r.get("createdTime", "")
    return [por_contacto[c] for c in orden]


def _at_ping():
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{TABLA_PEDIDOS}"
    try:
        r = requests.get(url, headers=_at_headers(), params={"maxRecords": 1}, timeout=10)
    except Exception as e:
        return False, f"No respondio ({e})."
    if r.status_code == 200:
        return True, "Conectado y respondiendo."
    if r.status_code in (401, 403):
        return False, "La clave de Airtable no tiene permiso."
    if r.status_code == 404:
        return False, "No encuentro la base o la tabla Pedidos."
    return False, f"Error {r.status_code}."


# ---------- RESUMEN / LOGIN ----------
@app.get("/api/panel/resumen")
def api_panel_resumen(x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    regs = _at_listar(TABLA_PEDIDOS)
    hoy = datetime.now(_tz()).strftime("%d/%m/%Y")
    nuevos = entregados = hoy_c = 0
    for r in regs:
        pe = _pedido_norm(r)
        est = str(pe["estado"]).lower()
        if est == "nuevo":
            nuevos += 1
        if est == "entregado":
            entregados += 1
        if str(pe["fecha"]).startswith(hoy):
            hoy_c += 1
    return {"total": len(regs), "hoy": hoy_c, "nuevos": nuevos, "entregados": entregados}


# ---------- PEDIDOS ----------
@app.get("/api/panel/pedidos")
def api_panel_pedidos(x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    regs = _at_listar(TABLA_PEDIDOS)
    norm = [_pedido_norm(r) for r in regs]
    norm.sort(key=lambda p: p["_createdTime"], reverse=True)  # mas nuevos primero
    return {"pedidos": [_pub(p) for p in norm]}


@app.post("/api/panel/pedido")
async def api_panel_nuevo_pedido(request: Request, x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    d = await request.json()
    fecha = datetime.now(_tz()).strftime("%d/%m/%Y %H:%M")
    fields = {
        "Nombre": (d.get("nombre") or "").strip(),
        "Ciudad": (d.get("ciudad") or "").strip(),
        "Telefono": (d.get("telefono") or "").strip(),
        "Producto": (d.get("producto") or "").strip(),
        "Total": (d.get("total") or "").strip(),
        "Estado": (d.get("estado") or "Nuevo").strip(),
        "Direccion": (d.get("direccion") or "").strip(),
        "Fecha": fecha,
    }
    ok, info = _at_crear(TABLA_PEDIDOS, fields)
    return {"ok": True} if ok else {"ok": False, "error": str(info)[:300]}


@app.post("/api/panel/estado")
async def api_panel_estado(request: Request, x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    d = await request.json()
    rec_id = (d.get("id") or "").strip()
    estado = (d.get("estado") or "").strip()
    if not rec_id or not estado:
        return {"ok": False, "error": "Faltan datos"}
    ok, info = _at_actualizar(TABLA_PEDIDOS, rec_id, {"Estado": estado})
    return {"ok": True} if ok else {"ok": False, "error": str(info)[:200]}


@app.post("/api/panel/aprobar-pedido")
async def api_panel_aprobar(request: Request, x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    d = await request.json()
    rec_id = (d.get("id") or "").strip()
    if not rec_id:
        return {"ok": False, "error": "Falta id"}
    ok, info = _at_actualizar(TABLA_PEDIDOS, rec_id, {"Estado": "Pagado"})
    return {"ok": True} if ok else {"ok": False, "error": str(info)[:200]}


@app.get("/api/panel/reporte-dia")
def api_panel_reporte_dia(x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    hoy = datetime.now(_tz()).strftime("%d/%m/%Y")
    ped = []
    facturado = 0
    for r in _at_listar(TABLA_PEDIDOS):
        pe = _pedido_norm(r)
        if str(pe["fecha"]).startswith(hoy):
            ped.append({
                "nombre": pe["nombre"], "producto": pe["producto"],
                "ciudad": pe["ciudad"], "total": pe["total"], "estado": pe["estado"]
            })
            facturado += _num(pe["total"])
    return {"fecha": hoy, "cantidad": len(ped), "facturado": facturado, "pedidos": ped}


@app.get("/api/panel/pendientes-pago")
def api_panel_pendientes(x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    pend = []
    for r in _at_listar(TABLA_PEDIDOS):
        pe = _pedido_norm(r)
        if str(pe["estado"]).lower() in ESTADOS_CERRADOS:
            continue
        dias = _hace_dias(_parse_fecha(pe["fecha"], pe["_createdTime"]))
        pend.append({
            "nombre": pe["nombre"], "producto": pe["producto"], "ciudad": pe["ciudad"],
            "total": pe["total"], "estado": pe["estado"], "hace_dias": dias
        })
    pend.sort(key=lambda x: (x["hace_dias"] is None, -(x["hace_dias"] or 0)))
    return {"pendientes": pend}


@app.get("/api/panel/buscar")
def api_panel_buscar(q: str = "", x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    q = (q or "").strip().lower()
    if not q:
        return {"resultados": []}
    res = []
    for r in _at_listar(TABLA_PEDIDOS):
        pe = _pedido_norm(r)
        blob = " ".join(str(pe[k]) for k in ("nombre", "ciudad", "telefono", "producto")).lower()
        if q in blob:
            res.append({
                "nombre": pe["nombre"], "producto": pe["producto"], "ciudad": pe["ciudad"],
                "telefono": pe["telefono"], "total": pe["total"], "estado": pe["estado"]
            })
    return {"resultados": res}


@app.get("/api/panel/ventas-mes")
def api_panel_ventas_mes(x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    acc = {}
    for r in _at_listar(TABLA_PEDIDOS):
        pe = _pedido_norm(r)
        if str(pe["estado"]).lower() == "cancelado":
            continue
        dt = _parse_fecha(pe["fecha"], pe["_createdTime"])
        if not dt:
            continue
        a = acc.setdefault((dt.year, dt.month), {"pedidos": 0, "facturado": 0})
        a["pedidos"] += 1
        a["facturado"] += _num(pe["total"])
    meses = []
    for (anio, mes) in sorted(acc.keys()):
        a = acc[(anio, mes)]
        meses.append({"mes": f"{MESES_ES[mes]} {anio}", "pedidos": a["pedidos"], "facturado": a["facturado"]})
    return {"meses": meses}


@app.get("/api/panel/ganancia")
def api_panel_ganancia(x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    costo_por_nombre = {}
    for c in _at_listar(TABLA_CATALOGO):
        p = _prod_norm(c)
        costo_por_nombre[str(p["nombre"]).strip().lower()] = _num(p["costo"])
    agg = {}
    total_gan = 0
    for r in _at_listar(TABLA_PEDIDOS):
        pe = _pedido_norm(r)
        if str(pe["estado"]).lower() == "cancelado":
            continue
        prod = str(pe["producto"]).strip()
        if not prod:
            continue
        costo = costo_por_nombre.get(prod.lower(), 0)
        gan = _num(pe["total"]) - costo
        a = agg.setdefault(prod, {"ventas": 0, "ganancia_total": 0, "costo_cargado": False})
        a["ventas"] += 1
        a["ganancia_total"] += gan
        a["costo_cargado"] = a["costo_cargado"] or costo > 0
        total_gan += gan
    productos = []
    for prod, a in agg.items():
        productos.append({
            "producto": prod,
            "ventas": a["ventas"],
            "ganancia_total": a["ganancia_total"],
            "ganancia_unit": int(a["ganancia_total"] / a["ventas"]) if a["ventas"] else 0,
            "costo_cargado": a["costo_cargado"],
        })
    productos.sort(key=lambda x: x["ganancia_total"], reverse=True)
    return {"ganancia_total": total_gan, "productos": productos}


# ---------- CATALOGO ----------
@app.get("/api/panel/catalogo")
def api_panel_catalogo(x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    return {"productos": [_prod_norm(r) for r in _at_listar(TABLA_CATALOGO)]}


@app.delete("/api/panel/producto")
async def api_panel_borrar_producto(request: Request, x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    d = await request.json()
    rec_id = (d.get("id") or "").strip()
    if not rec_id:
        return {"ok": False, "error": "Falta id"}
    ok, info = _at_borrar(TABLA_CATALOGO, rec_id)
    return {"ok": True} if ok else {"ok": False, "error": str(info)[:200]}


@app.patch("/api/panel/editar-producto")
async def api_panel_editar_producto(request: Request, x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    d = await request.json()
    rec_id = (d.get("id") or "").strip()
    if not rec_id:
        return {"ok": False, "error": "Falta id"}
    fields = {}
    if d.get("nombre"):
        fields["nombre"] = d["nombre"]
    if d.get("precio") not in (None, ""):
        fields["precio_gs"] = d["precio"]
    if "descripcion" in d:
        fields["descripcion_corta"] = d.get("descripcion", "")
    if d.get("stock"):
        fields["stock_estado"] = d["stock"]
    if not fields:
        return {"ok": False, "error": "Nada para actualizar"}
    ok, info = _at_actualizar(TABLA_CATALOGO, rec_id, fields)
    return {"ok": True} if ok else {"ok": False, "error": str(info)[:200]}


@app.post("/api/panel/editar-costo")
async def api_panel_editar_costo(request: Request, x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    d = await request.json()
    rec_id = (d.get("id") or "").strip()
    if not rec_id:
        return {"ok": False, "error": "Falta id"}
    ok, info = _at_actualizar(TABLA_CATALOGO, rec_id, {"costo_gs": _num(d.get("costo"))})
    return {"ok": True} if ok else {"ok": False, "error": str(info)[:200]}


@app.get("/api/panel/stock-alerta")
def api_panel_stock_alerta(x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    agotados = []
    for r in _at_listar(TABLA_CATALOGO):
        p = _prod_norm(r)
        if "agotad" in str(p["stock"]).lower():
            agotados.append(p["nombre"])
    return {"hay_alerta": bool(agotados), "agotados": agotados, "stock_bajo": []}


# ---------- CHARLAS / SEGUIMIENTO / FER ----------
@app.get("/api/panel/conversaciones")
def api_panel_conversaciones(x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    convs = _agrupar_conversaciones(_at_listar(TABLA))
    out = []
    for c in convs:
        ultimo = c["mensajes"][-1]["texto"] if c["mensajes"] else ""
        out.append({"id": c["id"], "ultimo": ultimo, "mensajes": c["mensajes"]})
    out.reverse()
    return {"conversaciones": out[:50]}


@app.get("/api/panel/seguimiento-plus")
def api_panel_seguimiento(x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    # Heuristica: prospectos que se engancharon (2+ mensajes del cliente).
    seg = []
    for c in _agrupar_conversaciones(_at_listar(TABLA)):
        cli = sum(1 for m in c["mensajes"] if m["rol"] == "cliente")
        if cli < 2:
            continue
        dt = None
        if c.get("_created"):
            try:
                dt = datetime.fromisoformat(c["_created"].replace("Z", "+00:00"))
            except Exception:
                dt = None
        seg.append({
            "id": c["id"],
            "mensajes": len(c["mensajes"]),
            "hace_dias": _hace_dias(dt),
            "ultimo": c["mensajes"][-1]["texto"] if c["mensajes"] else "",
        })
    seg.reverse()
    return {"seguimiento": seg[:50]}


@app.post("/api/panel/reenganche")
async def api_panel_reenganche(request: Request, x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    d = await request.json()
    ultimo = (d.get("ultimo") or "").strip()
    prompt = (
        "Sos Fer, vendedor paraguayo de Guaranistore. Escribi UN mensaje corto, "
        "calido y natural (voseo paraguayo, 1-2 lineas, sin presionar) para reenganchar "
        "a un cliente que dejo de responder. Su ultimo mensaje fue: "
        + (ultimo or "(sin mensaje)")
        + ". Devolve solo el mensaje, sin comillas ni explicaciones."
    )
    return {"mensaje": preguntar_a_gemini([], prompt, SYSTEM_PROMPT)}


@app.post("/api/panel/postventa-mensaje")
async def api_panel_postventa(request: Request, x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    d = await request.json()
    tipo = (d.get("tipo") or "").strip()
    nombre = (d.get("nombre") or "cliente").strip()
    producto = (d.get("producto") or "tu pedido").strip()
    guias = {
        "camino": "avisale que su pedido ya va en camino y que quede atento",
        "llego": "preguntale con onda si le llego el pedido y si esta todo bien",
        "testimonio": "pedile con amabilidad una foto o comentario si quedo contento",
        "recompra": "invitalo a volver a comprar u ofrecele otro producto, sin presionar",
    }
    guia = guias.get(tipo, "escribile un mensaje de seguimiento amable")
    prompt = (
        f"Sos Fer, vendedor paraguayo de Guaranistore. Escribi UN mensaje corto y calido "
        f"(voseo paraguayo, 1-3 lineas) para {nombre} sobre '{producto}': {guia}. "
        f"Devolve solo el mensaje, sin comillas ni explicaciones."
    )
    return {"mensaje": preguntar_a_gemini([], prompt, SYSTEM_PROMPT)}


@app.get("/api/panel/analisis-charlas")
def api_panel_analisis(x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    muestras = []
    for c in _agrupar_conversaciones(_at_listar(TABLA)):
        if any(m["rol"] == "cliente" for m in c["mensajes"]):
            texto = "\n".join(
                ("Cliente: " + m["texto"]) if m["rol"] == "cliente" else ("Fer: " + m["texto"])
                for m in c["mensajes"][-12:]
            )
            muestras.append(texto)
    muestras = muestras[-15:]
    if not muestras:
        return {"analisis": "Todavia no hay charlas suficientes para analizar.", "charlas_analizadas": 0}
    prompt = (
        "Sos analista de ventas. Te paso charlas reales entre Fer (vendedor) y clientes. "
        "Deci en pocos puntos concretos donde se caen las ventas y que puede mejorar Fer. "
        "Se breve, honesto y accionable. No inventes numeros.\n\n=== CHARLAS ===\n"
        + "\n\n---\n\n".join(muestras)
    )
    return {"analisis": preguntar_a_gemini([], prompt, PROMPT_DUENO), "charlas_analizadas": len(muestras)}


# ---------- DIAGNOSTICO / ACCIONES ----------
@app.get("/api/panel/diagnostico")
def api_panel_diagnostico(avisar: int = 0, x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    checks = []

    def add(nombre, ok, detalle):
        checks.append({"nombre": nombre, "estado": "ok" if ok else "falla", "detalle": detalle})

    at_ok, at_det = _at_ping()
    add("Airtable (base de datos)", at_ok, at_det)
    add("Gemini (IA de Fer)", bool(GEMINI_KEY), "Clave cargada." if GEMINI_KEY else "Falta GEMINI_KEY.")
    add("Messenger (Facebook)", bool(PAGE_TOKEN), "Token cargado." if PAGE_TOKEN else "Falta PAGE_TOKEN.")
    add(
        "Telegram (avisos)",
        bool(TELEGRAM_TOKEN and TELEGRAM_CHAT),
        "Configurado." if (TELEGRAM_TOKEN and TELEGRAM_CHAT) else "Falta token o chat."
    )
    add(
        "WhatsApp (opcional)",
        True,
        "Configurado." if (WHATSAPP_DESTINO and CALLMEBOT_APIKEY) else "No configurado (opcional)."
    )
    fallas = sum(1 for c in checks if c["estado"] != "ok")
    if avisar:
        try:
            resumen = "\n".join(
                ("OK " if c["estado"] == "ok" else "!! ") + c["nombre"] + ": " + c["detalle"]
                for c in checks
            )
            avisar_telegram("ESTADO DEL SISTEMA\n\n" + resumen)
        except Exception:
            pass
    return {"salud": "todo_ok" if fallas == 0 else "revisar", "fallas": fallas, "checks": checks}


@app.get("/api/panel/acciones")
def api_panel_acciones(x_clave: str = Header(default="")):
    if not _panel_ok(x_clave):
        return _no_autorizado()
    pedidos = [_pedido_norm(r) for r in _at_listar(TABLA_PEDIDOS)]
    catalogo = [_prod_norm(r) for r in _at_listar(TABLA_CATALOGO)]
    acciones = []

    nuevos = [p for p in pedidos if str(p["estado"]).lower() == "nuevo"]
    if nuevos:
        acciones.append({
            "prioridad": 1, "icono": "📦",
            "titulo": f"Despachá {len(nuevos)} pedido(s) nuevo(s)",
            "detalle": "Tenés ventas nuevas esperando que las mandes.",
            "boton": "Ver pedidos", "grupo": "ventas", "sub": "pedidos"
        })

    atrasados = []
    for p in pedidos:
        if str(p["estado"]).lower() in ESTADOS_CERRADOS:
            continue
        dias = _hace_dias(_parse_fecha(p["fecha"], p["_createdTime"]))
        if dias is not None and dias >= 2:
            atrasados.append(p)
    if atrasados:
        acciones.append({
            "prioridad": 1, "icono": "⏰",
            "titulo": f"Cobrá {len(atrasados)} pedido(s) atrasado(s)",
            "detalle": "Hace 2 dias o mas que estan sin cobrar.",
            "boton": "Ver por cobrar", "grupo": "ventas", "sub": "pendientes"
        })

    sin_costo = [p for p in catalogo if _num(p["costo"]) <= 0]
    if sin_costo:
        acciones.append({
            "prioridad": 2, "icono": "🏷️",
            "titulo": f"Cargá el costo de {len(sin_costo)} producto(s)",
            "detalle": "Sin costo no puedo calcular tu ganancia real.",
            "boton": "Ir al catálogo", "grupo": "productos", "sub": ""
        })

    agotados = [p for p in catalogo if "agotad" in str(p["stock"]).lower()]
    if agotados:
        acciones.append({
            "prioridad": 2, "icono": "⚠️",
            "titulo": f"Reponé {len(agotados)} producto(s) agotado(s)",
            "detalle": "Estas perdiendo ventas de lo que no tenes en stock.",
            "boton": "Ir al catálogo", "grupo": "productos", "sub": ""
        })

    acciones.sort(key=lambda a: a["prioridad"])
    return {"acciones": acciones}


@app.get("/")
def inicio():

    return {
        "estado":
        "Fer esta prendido "
        "y esperando mensajes"
    }
# ================= API PARA EL PANEL WEB =================

@app.get("/api/resumen")
def api_resumen():
    return {
        "estado": "online",
        "pedidos": resumen_ventas(),
        "conversaciones": leer_conversaciones()
    }
# ================= API: PEDIDOS REALES =================

@app.get("/api/pedidos")
def api_pedidos():
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{TABLA_PEDIDOS}"

    headers = {
        "Authorization": f"Bearer {AIRTABLE_KEY}"
    }

    r = requests.get(
        url,
        headers=headers,
        params={"maxRecords": 100},
        timeout=10
    )

    if r.status_code != 200:
        return {
            "error": "No se pudieron leer los pedidos"
        }

    pedidos = []

    for registro in r.json().get("records", []):

        campos = registro.get("fields", {})

        pedidos.append({
            "name": campos.get("Nombre", ""),
            "city": campos.get("Ciudad", ""),
            "phone": campos.get("Telefono", ""),
            "product": campos.get("Producto", ""),
            "total": campos.get("Total", ""),
            "status": campos.get("Estado", ""),
            "date": campos.get("Fecha", "")
        })

    return {
        "pedidos": pedidos
    }
# ================= DASHBOARD =================

@app.get("/api/dashboard")
def dashboard():

    try:

        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{TABLA_PEDIDOS}"

        headers = {
            "Authorization": f"Bearer {AIRTABLE_KEY}"
        }

        r = requests.get(
            url,
            headers=headers,
            params={"maxRecords": 1000},
            timeout=10
        )

        if r.status_code != 200:

            return {
                "error": "No se pudo leer Airtable",
                "detalle": r.text
            }

        pedidos = r.json().get("records", [])

        hoy = datetime.now(
            timezone(timedelta(hours=-3))
        ).strftime("%d/%m/%Y")

        pedidos_hoy = 0

        for registro in pedidos:

            campos = registro.get("fields", {})

            fecha = str(
                campos.get("Fecha", "")
            )

            if fecha.startswith(hoy):

                pedidos_hoy += 1

        return {

            "estado": "online",

            "total_pedidos": len(pedidos),

            "pedidos_hoy": pedidos_hoy,

            "ultimos_pedidos": [

                registro.get("fields", {})

                for registro in pedidos[-10:]

            ]

        }

    except Exception as e:

        print(
            ">>> ERROR DASHBOARD:",
            traceback.format_exc()
        )

        return {

            "error": str(e)

        }

# ================= UTILIDADES DE PEDIDOS =================

def _parsear(resumen):
    """Convierte 'Producto: X | Precio: Y | Nombre: Z | ...' en un dict."""
    datos = {}
    for parte in resumen.split("|"):
        if ":" not in parte:
            continue
        clave, valor = parte.split(":", 1)
        clave = clave.strip().lower()
        valor = valor.strip()
        if clave.startswith("tel"):
            clave = "tel"
        elif clave.startswith("direc"):
            clave = "direccion"
        datos[clave] = valor
    return datos


def formatear_pedido(resumen):
    """Texto lindo del pedido para avisar por Telegram."""
    d = _parsear(resumen)

    hora = datetime.now(
        timezone(timedelta(hours=-3))
    ).strftime("%d/%m/%Y %H:%M")

    return (
        "🛒 NUEVO PEDIDO\n\n"
        f"📦 Producto: {d.get('producto', '-')}\n"
        f"💵 Precio: {d.get('precio', '-')}\n"
        f"👤 Cliente: {d.get('nombre', '-')}\n"
        f"📍 Ciudad: {d.get('ciudad', '-')}\n"
        f"📞 Tel: {d.get('tel', '-')}\n"
        f"🏠 Direccion: {d.get('direccion', '-')}\n"
        f"🕒 {hora} hs\n"
        "💳 Pago contra entrega"
    )


def guardar_pedido(resumen):
    """Guarda el pedido en la tabla Pedidos de Airtable."""
    d = _parsear(resumen)

    fecha = datetime.now(
        timezone(timedelta(hours=-3))
    ).strftime("%d/%m/%Y %H:%M")

    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE}/{TABLA_PEDIDOS}"
    )

    headers = {
        "Authorization": f"Bearer {AIRTABLE_KEY}",
        "Content-Type": "application/json"
    }

    cuerpo = {
        "fields": {
            "Nombre": d.get("nombre", ""),
            "Ciudad": d.get("ciudad", ""),
            "Telefono": d.get("tel", ""),
            "Producto": d.get("producto", ""),
            "Total": d.get("precio", ""),
            "Estado": "Nuevo",
            "Fecha": fecha
        },
        "typecast": True
    }

    try:
        r = requests.post(
            url,
            headers=headers,
            json=cuerpo,
            timeout=10
        )

        if r.status_code not in (200, 201):
            print(
                ">>> AIRTABLE (guardar_pedido) error:",
                r.status_code,
                r.text
            )

    except Exception as e:
        print(">>> guardar_pedido error:", e)


# ================= MULTIMEDIA =================

def revisar_fotos(respuesta):
    """Detecta [FOTOS] / [MASFOTOS], las quita del texto y
    devuelve (texto_limpio, lista_de_urls)."""
    fotos = []

    if "[MASFOTOS]" in respuesta.upper():
        fotos.extend(
            BASE_FOTOS + nombre
            for nombre in FOTOS_EXTRA
        )

    if "[FOTOS]" in respuesta.upper():
        fotos = [
            BASE_FOTOS + nombre
            for nombre in FOTOS_PRINCIPALES
        ] + fotos

    limpio = re.sub(
        r"\[(FOTOS|MASFOTOS)\]",
        "",
        respuesta,
        flags=re.IGNORECASE
    ).strip()

    return limpio, fotos


def revisar_video(respuesta):
    """Detecta [VIDEO], lo quita del texto y devuelve
    (texto_limpio, url_video_o_vacio)."""
    video = ""

    if "[VIDEO]" in respuesta.upper():
        video = VIDEO_URL

    limpio = re.sub(
        r"\[VIDEO\]",
        "",
        respuesta,
        flags=re.IGNORECASE
    ).strip()

    return limpio, video


# ================= REPORTES PARA MODO DUENO / PANEL =================

def resumen_ventas():
    """Texto con un resumen real de las ventas desde Airtable."""
    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE}/{TABLA_PEDIDOS}"
    )

    headers = {
        "Authorization": f"Bearer {AIRTABLE_KEY}"
    }

    try:
        r = requests.get(
            url,
            headers=headers,
            params={"maxRecords": 1000},
            timeout=10
        )
    except Exception as e:
        return f"No pude leer los pedidos ahora ({e})."

    if r.status_code != 200:
        return "No pude leer los pedidos en este momento."

    registros = r.json().get("records", [])

    hoy = datetime.now(
        timezone(timedelta(hours=-3))
    ).strftime("%d/%m/%Y")

    total = len(registros)
    hoy_count = 0
    ciudades = {}
    ultimos = []

    for reg in registros:
        campos = reg.get("fields", {})

        fecha = str(campos.get("Fecha", ""))
        if fecha.startswith(hoy):
            hoy_count += 1

        ciudad = str(campos.get("Ciudad", "")).strip()
        if ciudad:
            ciudades[ciudad] = ciudades.get(ciudad, 0) + 1

    for reg in registros[-5:]:
        campos = reg.get("fields", {})
        ultimos.append(
            f"- {campos.get('Nombre', '?')} "
            f"({campos.get('Ciudad', '?')}) "
            f"{campos.get('Producto', '')} "
            f"{campos.get('Total', '')}"
        )

    top_ciudades = sorted(
        ciudades.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    partes = [
        "=== RESUMEN DE VENTAS ===",
        f"Total de pedidos: {total}",
        f"Pedidos de hoy: {hoy_count}",
    ]

    if top_ciudades:
        partes.append(
            "Ciudades con mas pedidos: "
            + ", ".join(
                f"{c} ({n})"
                for c, n in top_ciudades
            )
        )

    if ultimos:
        partes.append("Ultimos pedidos:")
        partes.extend(ultimos)

    return "\n".join(partes)


def leer_conversaciones(limite=40):
    """Texto con las conversaciones recientes desde Airtable."""
    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE}/{TABLA}"
    )

    headers = {
        "Authorization": f"Bearer {AIRTABLE_KEY}"
    }

    try:
        r = requests.get(
            url,
            headers=headers,
            params={"maxRecords": limite},
            timeout=10
        )
    except Exception as e:
        return f"No pude leer las conversaciones ahora ({e})."

    if r.status_code != 200:
        return "No pude leer las conversaciones en este momento."

    lineas = []

    for reg in r.json().get("records", []):
        campos = reg.get("fields", {})
        contacto = campos.get("contact_id", "?")
        mensaje = campos.get("mensaje_entrante", "")
        if mensaje:
            lineas.append(f"[{contacto}] {mensaje}")

    if not lineas:
        return "(Sin conversaciones registradas todavia.)"

    return "\n".join(lineas[-limite:])


# ================= SEGURIDAD DEL PANEL =================

def _clave_panel():
    """Clave valida para el panel (usa CLAVE_DUENO o PANEL_CLAVE)."""
    return (
        CLAVE_DUENO
        or os.environ.get("PANEL_CLAVE", "").strip().lower()
    )


def _panel_ok(x_clave):
    """True si la clave enviada por el panel es correcta."""
    clave = _clave_panel()
    if not clave:
        return False
    return (x_clave or "").strip().lower() == clave


def _no_autorizado():
    """Respuesta estandar cuando la clave del panel es incorrecta."""
    return JSONResponse(
        {"ok": False, "error": "Clave incorrecta o panel sin clave configurada."},
        status_code=401
    )
