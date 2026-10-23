# Guaranístore · Novva

Panel web y bot de ventas para páginas de Facebook. Un solo bot atiende a
varios negocios a la vez; Guaranístore sigue con sus variables de siempre.

| Archivo | Qué es |
|---|---|
| `index.html` | El panel Novva. Con tu clave ves Guaranístore; con la de un cliente, solo lo suyo. |
| `admin.html` | Tu página para cargar, editar, pausar y revisar cada negocio. |
| `oferta.html` | La página para mostrarle Novva a los negocios. |
| `privacidad.html`, `borrar-datos.html` | Las páginas que pide Meta. |
| `prompt-novva.txt` | El vendedor de tu página Novva. |
| `bot/main.py` | El bot (va en Render, repo `guaranistorebot`). |
| `bot/test_bot.py` | Pruebas con todos los servicios simulados: `cd bot && python3 test_bot.py`. |

**Cómo ponerlo en marcha:** seguí [`GUIA-MULTICLIENTE.md`](GUIA-MULTICLIENTE.md),
fase por fase.
