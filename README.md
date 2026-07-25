# Guaranístore · Fer Bot Control

Este paquete contiene la primera versión visual del panel de control para Fer Bot.

Incluye:
- Resumen del negocio
- Pedidos
- Chat en vivo para observar conversaciones
- Auditor de Fer
- Catálogo
- Diseño responsive para celular y computadora

## Importante

Esta versión incluye datos de demostración para mostrar la interfaz.

El siguiente paso es conectarla a los datos reales del `main.py` y Airtable mediante una API segura. No conviene poner las claves de Airtable, Gemini o Telegram dentro del navegador.

La idea recomendada es:

1. Mantener tu `main.py` del bot sin tocar su funcionamiento.
2. Crear un pequeño servicio/API separado para el panel.
3. Ese servicio usa las mismas variables de entorno y lee Airtable de forma segura.
4. El panel consulta esa API y muestra datos reales.
5. Luego se puede desplegar gratis en Render y conectar un dominio.

