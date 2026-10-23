# Guía: un bot para varios negocios

Esta guía va en **fases cortas**, para hacer de a una en tus francos.
Cada fase termina con una prueba, así sabés que quedó bien antes de seguir.

> Las pantallas de Meta cambian seguido. Si algo no coincide con lo que dice
> acá, mandame una captura y lo vemos juntos.

**Lo que ya está hecho (en GitHub):**

| Archivo | Qué es |
|---|---|
| `bot/main.py` | El bot nuevo. Guaranístore sigue igual con tus variables de siempre. |
| `admin.html` | Tu página para cargar, editar, pausar y revisar cada negocio. |
| `privacidad.html` y `borrar-datos.html` | Las páginas que Meta pide para aprobarte. |
| `oferta.html` | La página para mostrarle Novva a los negocios. |
| `prompt-novva.txt` | El vendedor de tu propia página Novva. |
| `bot/test_bot.py` | Las pruebas: 54 chequeos con Meta, Gemini, Airtable, Telegram y Upstash simulados. |

---

## Antes de empezar

- [ ] **Confirmá que lo que corre en Render es el `main.py` de `guaranistorebot`**
      (el del 5 de agosto). Si Gemini o alguien te lo cambió después, pasame
      el tuyo antes de subir nada: el bot nuevo parte de esa versión.
- [ ] **Pasame tu nombre o razón social, RUC y correo.** Van en las páginas de
      privacidad (ahora están marcados en amarillo).
- [ ] **Pasame tus precios y tu WhatsApp o Messenger** para `oferta.html`.

---

## Fase 1 — Subir el bot nuevo (≈ 20 min)

Si algo sale mal en esta fase, Render tiene un botón para volver atrás:
lo dejamos ubicado **antes** de tocar nada.

1. **Ubicá el botón para volver atrás.** En Render → tu servicio
   `guaranistorebot` → **Events** (o **Deploys**). Ahí está el último deploy
   que anda; cada deploy viejo tiene un botón **Rollback**.
2. **Cargá las variables nuevas.** En Render → tu servicio → **Environment**
   → **Add Environment Variable**:

   | Variable | Qué poner |
   |---|---|
   | `ADMIN_CLAVE` | Una clave larga inventada por vos (20 letras o más). Es para `admin.html`. **No** uses la del panel. |
   | `META_APP_ID` | El **Identificador de la app**: Meta for Developers → tu app → Configuración de la app → Básica. |
   | `META_APP_SECRET` | La **Clave secreta de la app**, en la misma pantalla (tocá «Mostrar»). |

   Revisá que **ya estén** `UPSTASH_REDIS_REST_URL` y `UPSTASH_REDIS_REST_TOKEN`
   (tu bot ya las usa para la memoria). Sin ellas no se pueden guardar negocios.
   Las variables de siempre (`PAGE_TOKEN`, `AIRTABLE_BASE`, `CLAVE_PANEL`, etc.)
   **no se tocan**.
3. **Subí el `main.py` nuevo a `guaranistorebot`**, como siempre:
   - En este repo (`Guaran-storeweb`) abrí `bot/main.py` → botón **⋯** →
     **Download** (o **Raw** y guardalo).
   - En el repo `guaranistorebot` → **Add file** → **Upload files** → subí el
     `main.py` (reemplaza al viejo) → **Commit changes**.
   - Render lo despliega solo en unos minutos.
   - Si preferís, decime «subilo a guaranistorebot» y lo subo yo.
4. **Probá:**
   - [ ] `https://guaranistorebot.onrender.com/` dice «Fer esta prendido».
   - [ ] Escribile a Guaranístore desde otra cuenta: contesta como siempre.
   - [ ] Entrá a tu panel con tu clave: anda igual y abajo de «Novva» dice
         **GUARANISTORE**.
   - [ ] Si algo falla: **Rollback** en el deploy anterior y mandame lo que viste.

## Fase 2 — Subir las páginas públicas (≈ 10 min)

1. Pasame tus datos (nombre o razón social, RUC, correo) y los completo.
2. Hay que pasar estos cambios a la rama `main` de `Guaran-storeweb` para que
   GitHub Pages los publique. Decime «abrí el pull request» y lo armo; vos
   solo tocás **Merge**.
3. **Probá** que abran:
   - [ ] `https://celparaguayy-cloud.github.io/Guaran-storeweb/privacidad.html`
   - [ ] `https://celparaguayy-cloud.github.io/Guaran-storeweb/borrar-datos.html`
   - [ ] `https://celparaguayy-cloud.github.io/Guaran-storeweb/oferta.html`
   - [ ] `https://celparaguayy-cloud.github.io/Guaran-storeweb/admin.html` → entrá
         con tu `ADMIN_CLAVE` y tiene que aparecer la tarjeta de Guaranístore.

   Si no abre ninguna: en el repo → **Settings** → **Pages** tiene que decir
   que se publica desde la rama `main`.

## Fase 3 — Pedirle a Meta que te deje atender páginas de otros (lo que más tarda)

Hoy tu app de Meta solo puede contestar en páginas que manejás vos. Para
atender las páginas de tus clientes, Meta tiene que **verificar tu negocio** y
**revisar tu app**. Meta a veces le dice a esto «Tech Provider» o
«acceso avanzado». Tarda días o semanas, por eso conviene mandarlo apenas
termines la Fase 2.

1. **Datos de la app.** Meta for Developers → tu app → Configuración de la
   app → **Básica**:
   - URL de la política de privacidad → la de `privacidad.html`.
   - URL de instrucciones para eliminar datos → la de `borrar-datos.html`.
   - Ícono, categoría y correo de contacto.
2. **Verificación del negocio.** Meta Business Suite → Configuración →
   **Centro de seguridad** → **Verificación del negocio**. Te pide los datos
   de tu RUC y un documento que lo pruebe.
3. **Revisión de la app.** Meta for Developers → tu app → **Revisión de la
   app** → **Permisos y funciones**. Pedí **acceso avanzado** para:
   - `pages_messaging` (contestar los mensajes)
   - `pages_show_list` (ver las páginas que te dan para manejar)
   - `pages_manage_metadata` (conectar la página al bot)

   Para cada uno te piden explicar para qué lo usás y un video corto. El
   video puede ser con Guaranístore: alguien escribe a la página, el bot
   contesta, y después mostrás `admin.html` conectando una página.
4. Mientras esperás, **todo sigue andando** con tus propias páginas.

## Fase 4 — Preparar la base de Airtable de cada cliente (≈ 15 min por cliente)

Cada cliente tiene **su propia base**, así sus datos nunca se cruzan con los
tuyos.

1. En Airtable, en tu base de Guaranístore → la flechita al lado del nombre
   → **Duplicar base** → **sin** los registros. Ponele el nombre del cliente.
2. Tiene que tener las tres tablas con estas columnas:
   - **Pedidos:** Producto, Nombre, Ciudad, Telefono, Direccion, Total,
     Fecha, Estado, Contacto
   - **Catalogo_Espejo:** producto_id, nombre, precio_gs, costo_gs,
     stock_estado, descripcion_corta
   - **Conversaciones:** contact_id, canal, mensaje_entrante
3. Cargá el catálogo del cliente en **Catalogo_Espejo**.
4. **Dale permiso a tu token de Airtable sobre la base nueva** (si te
   olvidás, el bot no la puede leer): airtable.com/create/tokens → tu token
   → **Add a base** → elegí la base nueva → **Save changes**.
5. Copiá el **id de la base**: está en la dirección de Airtable, es lo que
   empieza con `app…` (17 letras).

## Fase 5 — Conectar tu página Novva (≈ 30 min)

Tu página Novva se carga como un cliente más, y su vendedor vende el bot.

1. Prepará su base de Airtable (Fase 4). En **Catalogo_Espejo** cargá tus
   planes como productos: `nombre` = el plan (ej. «Novva»), `precio_gs` = el
   precio, `descripcion_corta` = qué incluye. Así el bot da tus precios reales.
2. **Sacá el token.** En Meta for Developers → **Herramientas** → **Explorador
   de la API Graph**: elegí tu app, tocá **Generar token de acceso** y dale
   permiso a tu página Novva con `pages_show_list`, `pages_messaging` y
   `pages_manage_metadata`. Copiá el token.
3. En `admin.html` → **+ Nuevo**:
   - Pegá el token en **Token de la persona** → **Buscar mis páginas** →
     tocá tu página Novva. El nombre se completa solo.
   - **Clave del panel:** tocá **Inventar**.
   - **Base de Airtable:** el `app…` de la base de Novva.
   - **Chat de Telegram:** el tuyo, así los interesados te llegan a vos.
   - **Forma de vender:** pegá todo el texto de `prompt-novva.txt`.
   - **Costo de envío al interior:** `0`. Si no, le suma envío a tus planes.
   - **Fotos:** podés poner capturas del panel subidas a internet.
   - **Guardar.**
4. En la tarjeta de Novva: **Conectar página** y después **Revisar**. Todo
   tiene que dar ✅.
5. **Probá:** escribile a tu página Novva desde otra cuenta. Tiene que
   contestar como vendedor de Novva, y con la clave de Novva el panel tiene
   que mostrar **solo** lo de Novva.

## Fase 6 — Conectar al primer cliente (cuando Meta te apruebe)

1. **El cliente te da acceso a su página** desde Facebook: en la
   configuración de su página → **Acceso a la página** → te agrega con un
   acceso que incluya **mensajes** y **actividad de la comunidad**
   (moderar). No necesitás su contraseña. Si después «Conectar página» da un
   error de permisos, que te dé control total.
2. Preparale su base de Airtable (Fase 4).
3. Igual que en la Fase 5: Explorador de la API Graph → token →
   `admin.html` → **+ Nuevo** → **Buscar mis páginas** → elegí la del cliente.
   La **forma de vender** la podés dejar vacía (usa la de Guaranístore con el
   nombre del negocio) o escribirle una propia.
4. **Guardar** → **Conectar página** → **Revisar**.
5. Escribile a su página desde otra cuenta para probar.
6. **Pasar acceso** → **Copiar mensaje** → mandáselo por WhatsApp: tiene el
   link del panel y su clave.

**Si un cliente no paga:** en su tarjeta, **Pausar**. El bot deja de
contestarle y su panel le dice que el servicio está pausado. **Reanudar** lo
vuelve a prender al instante.

---

## Para más adelante (opcional)

- **Aceptar solo mensajes firmados por Meta.** Cuando todo ande, agregá en
  Render `VERIFICAR_FIRMA` = `1`. Así nadie puede mandarle mensajes falsos al
  bot. Si después de eso el bot deja de contestar, revisá que
  `META_APP_SECRET` esté bien copiado (o sacá la variable).
- **Si «Revisar» dice que un token venció:** volvé a hacer **Buscar mis
  páginas** con un token nuevo y guardá. Con `META_APP_ID` y
  `META_APP_SECRET` cargados, los tokens que trae no vencen.
- **Probar el bot sin internet:** `cd bot && python3 test_bot.py` corre los
  54 chequeos con todo simulado.
