"""
Servicios simulados para probar el bot sin tocar nada real:
Meta, Gemini, Airtable, Telegram y Upstash viven en memoria.
Lo usan test_bot.py y la prueba de admin.html en el navegador.
"""
import os, re, json, copy, time, threading, importlib.util

ENV = {
    "PAGE_TOKEN": "tok-guarani", "GEMINI_KEY": "gem-tuya", "AIRTABLE_KEY": "at-tuya",
    "AIRTABLE_BASE": "appGUARANI0000000", "TELEGRAM_TOKEN": "tg-tuyo", "TELEGRAM_CHAT": "chat-tuyo",
    "CLAVE_PANEL": "clave-guarani", "CLAVE_DUENO": "soyeldueno", "ADMIN_CLAVE": "admin-super-secreta-99",
    "UPSTASH_REDIS_REST_URL": "https://upstash.test", "UPSTASH_REDIS_REST_TOKEN": "up-token",
    "META_APP_ID": "111", "META_APP_SECRET": "secreto-app",
}
os.environ.update(ENV)
os.environ.pop("PAGE_ID", None)

PAG_GUARANI, PAG_A, PAG_B, PAG_C = "1000", "2000", "3000", "4000"
BASE_A, BASE_B, BASE_C = "appTIENDAA0000000", "appTIENDAB0000000", "appTIENDAC0000000"


# ============================================================
#   SERVICIOS SIMULADOS
# ============================================================
class Resp:
    def __init__(self, status=200, data=None, content=None, headers=None):
        self.status_code = status
        self._data = data
        self.content = content if content is not None else (json.dumps(data).encode() if data is not None else b"")
        self.headers = headers or {"Content-Type": "application/json"}
    def json(self):
        if self._data is None: raise ValueError("sin json")
        return self._data
    @property
    def text(self):
        return json.dumps(self._data, ensure_ascii=False) if self._data is not None else self.content.decode(errors="ignore")


class Servicios:
    """Hace de requests: cada llamada del bot cae acá en vez de salir a internet."""
    def __init__(self):
        self.lock = threading.RLock()
        self.reset()

    def reset(self):
        self.redis = {}
        self.bases = {}
        self.acceso = {}          # clave de airtable -> bases que puede tocar
        self.paginas = {}         # token de página -> {"id", "name"}
        self.personas = {}        # token de persona -> [páginas]
        self.suscritas = set()
        self.llamadas = []
        self.mensajes = []        # (token de página, payload)
        self.telegram = []        # (token del bot, chat, texto)
        self.demora_gemini = 0.0
        self.upstash_caido = False
        self.seq = 0

    def base(self, base_id, clave):
        self.bases[base_id] = {"Pedidos": {}, "Catalogo_Espejo": {}, "Conversaciones": {}}
        self.acceso.setdefault(clave, set()).add(base_id)

    def registro(self, base_id, tabla, campos):
        self.seq += 1
        rid = "rec%014d" % self.seq
        self.bases[base_id][tabla][rid] = {"id": rid, "createdTime": "2026-10-%02dT12:00:%02dZ" % (1 + self.seq // 60 % 20, self.seq % 60),
                                           "fields": dict(campos)}
        return rid

    # --- la interfaz de requests ---
    def get(self, url, **kw): return self._llamar("GET", url, **kw)
    def post(self, url, **kw): return self._llamar("POST", url, **kw)
    def patch(self, url, **kw): return self._llamar("PATCH", url, **kw)
    def delete(self, url, **kw): return self._llamar("DELETE", url, **kw)

    def _llamar(self, metodo, url, params=None, json=None, headers=None, timeout=None, **_):
        with self.lock:
            self.llamadas.append((metodo, url, copy.deepcopy(params), copy.deepcopy(json)))
        if url.startswith("https://upstash.test"): return self._upstash(json)
        if "api.airtable.com" in url: return self._airtable(metodo, url, params, json, headers or {})
        if "graph.facebook.com" in url: return self._graph(metodo, url, params or {}, json)
        if "generativelanguage" in url: return self._gemini(json)
        if "api.telegram.org" in url:
            with self.lock:
                self.telegram.append((url.split("/bot")[1].split("/")[0], json["chat_id"], json["text"]))
            return Resp(200, {"ok": True})
        if "cdn.fb.test" in url: return Resp(200, None, content=b"\xff\xd8imagen", headers={"Content-Type": "image/jpeg"})
        return Resp(404, {"error": "desconocido"})

    def _upstash(self, cmd):
        if self.upstash_caido: return Resp(500, {"error": "caido"})
        op, a = cmd[0].upper(), cmd[1:]
        with self.lock:
            r = self.redis
            if op == "PING": res = "PONG"
            elif op == "GET": res = r.get(a[0])
            elif op == "SET": r[a[0]] = a[1]; res = "OK"
            elif op == "DEL": res = 1 if r.pop(a[0], None) is not None else 0
            elif op == "EXPIRE": res = 1
            elif op == "RPUSH": r.setdefault(a[0], []).extend(a[1:]); res = len(r[a[0]])
            elif op == "LRANGE":
                lst = r.get(a[0], []); ini, fin = int(a[1]), int(a[2])
                res = lst[ini:] if fin == -1 else lst[ini:fin + 1]
            elif op == "LTRIM":
                lst = r.get(a[0], []); ini = int(a[1]); r[a[0]] = lst[ini:]; res = "OK"
            elif op == "HSET": r.setdefault(a[0], {})[a[1]] = a[2]; res = 1
            elif op == "HGET": res = r.get(a[0], {}).get(a[1])
            elif op == "HDEL": res = 1 if r.get(a[0], {}).pop(a[1], None) is not None else 0
            elif op == "HGETALL":
                res = []
                for k, v in r.get(a[0], {}).items(): res += [k, v]
            else: return Resp(400, {"error": "comando " + op})
        return Resp(200, {"result": res})

    def _airtable(self, metodo, url, params, cuerpo, headers):
        partes = url.split("/v0/")[1].split("/")
        base_id, tabla, rid = partes[0], partes[1], (partes[2] if len(partes) > 2 else "")
        clave = headers.get("Authorization", "").replace("Bearer ", "")
        if base_id not in self.acceso.get(clave, set()): return Resp(403, {"error": "sin permiso"})
        if base_id not in self.bases or tabla not in self.bases[base_id]: return Resp(404, {"error": "no existe"})
        t = self.bases[base_id][tabla]
        with self.lock:
            if metodo == "GET":
                p = dict(params or {})
                regs = list(t.values())
                m = re.match(r"\{(\w+)\}='([^']*)'", p.get("filterByFormula", ""))
                if m: regs = [x for x in regs if str(x["fields"].get(m.group(1), "")) == m.group(2)]
                tope = int(p.get("maxRecords", p.get("pageSize", 100)))
                return Resp(200, {"records": copy.deepcopy(regs[:tope])})
            if metodo == "POST":
                nuevo = self.registro(base_id, tabla, cuerpo["fields"])
                return Resp(200, copy.deepcopy(t[nuevo]))
            if metodo == "PATCH":
                cambios = [{"id": rid, "fields": cuerpo["fields"]}] if rid else cuerpo["records"]
                hechos = []
                for c in cambios:
                    if c["id"] not in t: return Resp(404, {"error": "no existe el registro"})
                    t[c["id"]]["fields"].update(c["fields"]); hechos.append(copy.deepcopy(t[c["id"]]))
                return Resp(200, hechos[0] if rid else {"records": hechos})
            if metodo == "DELETE":
                ids = [rid] if rid else [v for k, v in (params or []) if k == "records[]"]
                for x in ids:
                    if x not in t: return Resp(404, {"error": "no existe el registro"})
                for x in ids: t.pop(x)
                return Resp(200, {"deleted": True, "id": ids[0]} if rid else {"records": [{"id": x, "deleted": True} for x in ids]})
        return Resp(405, {"error": "metodo"})

    def _graph(self, metodo, url, params, cuerpo):
        ruta = re.sub(r"^https://graph\.facebook\.com(/v[\d.]+)?", "", url)
        token = params.get("access_token", "")
        if ruta == "/me/messages":
            if token not in self.paginas: return Resp(400, {"error": {"message": "token inválido"}})
            with self.lock: self.mensajes.append((token, copy.deepcopy(cuerpo)))
            return Resp(200, {"recipient_id": cuerpo["recipient"]["id"]})
        if ruta == "/me" and metodo == "GET":
            if token in self.paginas:
                p = self.paginas[token]; return Resp(200, {"id": p["id"], "name": p["name"], "category": "Tienda"})
            if token in self.personas or token.startswith("LL-"):
                if "category" in params.get("fields", ""):
                    return Resp(400, {"error": {"message": "(#100) Tried accessing nonexisting field (category) on node type (User)"}})
                return Resp(200, {"id": "9", "name": "Persona"})
            return Resp(400, {"error": {"message": "Invalid OAuth access token"}})
        if ruta == "/debug_token":
            if params.get("access_token") != "111|secreto-app": return Resp(400, {"error": {"message": "app"}})
            return Resp(200, {"data": {"app_id": "111", "expires_at": 0, "scopes": ["pages_messaging", "pages_show_list"], "type": "PAGE"}})
        if ruta == "/oauth/access_token":
            if params.get("client_secret") != "secreto-app" or params.get("fb_exchange_token") not in self.personas:
                return Resp(400, {"error": {"message": "no se pudo canjear"}})
            return Resp(200, {"access_token": "LL-" + params["fb_exchange_token"]})
        if ruta == "/me/accounts":
            corto = token[3:] if token.startswith("LL-") else token
            if corto not in self.personas: return Resp(400, {"error": {"message": "token inválido"}})
            return Resp(200, {"data": [{"id": p["id"], "name": p["name"], "access_token": t}
                                       for t, p in self.paginas.items() if p["id"] in self.personas[corto]]})
        m = re.match(r"^/(\d+)/subscribed_apps$", ruta)
        if m:
            if self.paginas.get(token, {}).get("id") != m.group(1): return Resp(400, {"error": {"message": "token de otra página"}})
            if metodo == "POST": self.suscritas.add(m.group(1)); return Resp(200, {"success": True})
            return Resp(200, {"data": [{"id": "111"}] if m.group(1) in self.suscritas else []})
        return Resp(404, {"error": {"message": "ruta " + ruta}})

    def _gemini(self, cuerpo):
        if self.demora_gemini: time.sleep(self.demora_gemini)
        partes = cuerpo["contents"][-1]["parts"]
        if any("inline_data" in p for p in partes):   # comprobante
            return Resp(200, {"candidates": [{"content": {"parts": [{"text": '```json\n{"monto":"100.000","referencia":"R-1","banco_origen":"Itau"}\n```'}]}}]})
        prompt = ((cuerpo.get("system_instruction") or {}).get("parts") or [{}])[0].get("text", "")
        m = (re.search(r"tienda paraguaya (.+?)\. Hablás", prompt) or re.search(r"NEGOCIO=([\w-]+)", prompt)
             or re.search(r"dueño de (.+?) \(modo dueño\)", prompt))
        tienda = m.group(1) if m else "?"
        if "modo dueño" in prompt: tienda = "DUEÑO " + tienda
        ultimo = partes[-1].get("text", "")
        if "modo dueño" in prompt: txt = "[%s] informe" % tienda
        elif ultimo.startswith("El sistema consultó el catálogo"):
            txt = "[%s] Dato: %s" % (tienda, ultimo.split("\n")[0][32:90])
        elif "precio" in ultimo: txt = "[CONSULTAR_PRODUCTO: crema]"
        elif "quiero pedir" in ultimo:
            txt = ("[%s] ¡Listo! [PEDIDO] Producto: Crema | Precio: Gs. 100.000 | Nombre: Ana | Ciudad: Encarnacion "
                   "| Tel: 0981 | Direccion: Calle 1 [/PEDIDO]" % tienda)
        elif "fotos" in ultimo: txt = "[%s] Mirá [FOTOS]" % tienda
        elif "video" in ultimo: txt = "[%s] Mirá [VIDEO]" % tienda
        else: txt = "[%s] respuesta a: %s" % (tienda, ultimo[-60:])
        return Resp(200, {"candidates": [{"content": {"parts": [{"text": txt}]}}]})


FAKE = Servicios()


def cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.requests = FAKE
    mod.ahora = lambda: "05/10/2026 10:00"
    if not os.environ.get("VER_LOGS"): mod.print = lambda *a, **k: None
    return mod
