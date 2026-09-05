# Interfaz de Mictlan — catálogo visual

Este documento es un inventario **solo estético** de todo lo que un
usuario ve al usar Mictlan: cada mensaje, panel, menú y botón inline,
tal como aparece en Telegram. No incluye código, nombres de función ni
`callback_data` — si necesitás la implementación real, ver
`GUIA_SDK_MODULOS_EXTERNOS.md` (para módulos externos) o el código en
`mictlan/`.

Convención de los mockups: cada pantalla va en un bloque de texto. Cada
línea entre corchetes `[ ]` es un botón; varios botones separados por
`|` están en la misma fila (el usuario los ve uno al lado del otro).

---

## 1. Patrones que se repiten en toda la interfaz

**Botón "Cerrar" universal.** Casi todo mensaje que manda el bot (menús,
confirmaciones, avisos) trae, como última fila, un botón:

```
[✖️ Cerrar]
```

Tocarlo borra el mensaje al instante. Si nadie lo toca, el propio mensaje
se autoborra solo a los **30 minutos**. Es la firma visual de "esto es
un mensaje del bot, no una conversación libre".

**Paginación (listas largas: usuarios, módulos, grupos).** Los ítems se
muestran de a **6 por página**, en una grilla de 2 columnas × 3 filas.
Si hay más de una página, aparece una fila de navegación:

```
[Ítem 1]              [Ítem 2]
[Ítem 3]              [Ítem 4]
[Ítem 5]              [Ítem 6]
[⬅️        📄 1/3        ➡️]
```

El botón del medio (número de página) no hace nada nuevo si se toca —
solo refresca la misma página.

**Silencio total.** Varios comandos (`/mando`, `/otorgar`, `/reactivar`,
`/tecuhtli_simular`) no responden absolutamente nada si quien escribe no
tiene el rol o no está en el chat correcto — ni un mensaje de error, ni
un botón. Para quien no tiene acceso, es indistinguible de un comando
que no existe.

---

## 2. Comandos para cualquier miembro

### `/start`

```
Bienvenido a Mictlan.

[✖️ Cerrar]
```
Cualquier persona, cualquier chat privado con el bot.

### `/perfil`

```
🆔 ID: 123456789
👤 Rol: 👤
📅 Membresía: activa hasta 2026-10-05
💰 Saldo: 40 créditos

[✖️ Cerrar]
```
Cualquier miembro, sobre sí mismo. "Membresía" cambia a "vencida
(fecha)" o "sin membresía activa" según corresponda. El rol nunca se
muestra como palabra — solo el emoji (👤 miembro, 💼 vendedor,
🛠 administrador, 👑 root).

### `/reporte <texto>`

Sin texto:
```
Uso: /reporte tu mensaje aquí

[✖️ Cerrar]
```

Con texto, quien reporta ve:
```
✅ Reporte recibido, los administradores lo revisarán.

[✖️ Cerrar]
```

Y en el grupo de gestión aparece, para cualquier administrador/root:
```
🚩 Reporte #14
De: 123456789 @usuario

(el texto del reporte)

[✅ Atendido]
[✖️ Cerrar]
```
Al tocar "Atendido", el mismo mensaje se edita en el momento:
```
🚩 Reporte #14
De: 123456789

(el texto del reporte)

✅ Atendido por @admin

[✖️ Cerrar]
```

### `/canales`

Solo funciona escrito dentro del grupo principal, y solo para un
miembro con membresía activa (si no la tiene: "⚠️ Necesitás una
membresía activa para esto."). Muestra:

```
🔗 Canales

Elegí a dónde querés tu link de invitación (un solo uso):

[Nombre del canal secundario 1]
[Nombre del canal secundario 2]

[✖️ Cerrar]
```
(Si todavía no hay ningún grupo/canal secundario activo: "(sin
grupos/canales secundarios activos todavía)".)

Al tocar un canal, el mismo mensaje se actualiza mostrando el link:
```
🔗 Canales

🔗 Tu link (un solo uso): https://t.me/+xxxxxxxxxxxx

[Nombre del canal secundario 1]
[Nombre del canal secundario 2]

[✖️ Cerrar]
```

---

## 3. Los dos "portones" de entrada de un nuevo miembro

Cada grupo gestionado usa **uno solo** de estos dos mecanismos (nunca
los dos a la vez) para un miembro nuevo que no sea ya
administrador/root.

### 3.1 Captcha de bienvenida

Al entrar, el usuario queda silenciado (no puede escribir) y recibe, en
el propio grupo:

```
👋 Bienvenido.

Para poder escribir en el grupo, resolvé:

¿Cuánto es 7 + 12?

⚠️ Si no respondés en 3 minutos, vas a ser expulsado automáticamente.

[9]        [19]
[23]       [15]
```
(4 opciones, una sola es la correcta — el layout exacto de filas puede
variar según cuántas opciones haya.)

- Toca la opción correcta → el mismo mensaje se edita:
  ```
  ✅ Verificación correcta. Ya podés escribir.
  ```
- Toca una opción incorrecta → aparece una alerta emergente ("popup",
  no un mensaje nuevo): *"Respuesta incorrecta ❌ Seguís silenciado."*
  El reto sigue activo, puede reintentar.
- Si nadie responde a tiempo, el mensaje se edita solo:
  ```
  ⛔ Tiempo agotado. Fuiste expulsado por no resolver el captcha.
  ```

### 3.2 Ingreso por aprobación de un administrador

Al entrar, el usuario también queda silenciado, pero acá no ve ningún
reto — el aviso va al **grupo de gestión**, visible solo para
administradores/vendedores/root:

```
📥 Nuevo ingreso pendiente de aprobación

Usuario: @nuevo_usuario (123456789)
Grupo: Nombre del Grupo

⏳ Si ningún admin/vendedor lo acepta en 1 minuto, será expulsado
automáticamente.

[✅ Aceptar]
```

- Un administrador/vendedor toca "Aceptar" → el mensaje se edita:
  ```
  ✅ 123456789 aceptado por @admin.
  ```
- Si nadie lo acepta a tiempo → se edita solo:
  ```
  ⛔ 123456789 expulsado — nadie lo aceptó en 1 minuto.
  ```
- Si un miembro sin rol suficiente toca "Aceptar", no pasa nada visible
  (silencio total).

---

## 4. Consola `/mando`

Solo responde en DM con el bot o en el grupo de gestión, y solo a rol
`root` — cualquier otro caso, silencio total.

### 4.1 Menú principal

```
🛠 Consola Mictlan

[👥 Usuarios]
[🧩 Módulos]
[🏘 Grupos]
[🛠 Mantenimiento]

[✖️ Cerrar]
```

### 4.2 👥 Usuarios

**Lista** (paginada, 6 por página):
```
🛠 Usuarios

👤 / 💼 / 🛠 / 👑 — ⛔ baneado — página 1/2

[👤 usuario1]              [💼 usuario2]
[🛠 usuario3 ⛔]            [👑 usuario4]

[⬅️        📄 1/2        ➡️]
[⬅️ Volver]
[✖️ Cerrar]
```
Cada botón muestra el emoji del rol + username (o ID si no tiene) + un
⛔ extra si está baneado.

**Detalle de un usuario:**
```
🛠 usuario1
123456789

Rol: 👤
Membresía: activa hasta 2026-10-05
Estado: ✅ sin baneo

[📅 +7]        [📅 +30]
[📅 -7]        [📅 -30]
[🎭 Cambiar rol]
[🚫 Banear]
[⬅️ Volver]
[✖️ Cerrar]
```
Si el usuario ya está baneado, en vez de "🚫 Banear" aparecen:
```
[✅ Desbanear]
[📋 Ver reporte]
```

**Cambiar rol** (submenú):
```
🎭 Cambiar rol
123456789

Rol actual: 👤

[👤]
[✅ 💼]
[🛠]
[👑]
[⬅️ Cancelar]
[✖️ Cerrar]
```
(El rol actual lleva un ✅ delante. Ningún botón dice el nombre del
rol como palabra — solo el emoji.)

**Flujo de baneo** (conversación paso a paso, se activa desde "🚫
Banear"):
```
🚫 Banear
123456789

Enviá el motivo del baneo (texto).

[⬅️ Cancelar]
```
→ el admin escribe el motivo como mensaje de texto normal →
```
🖼 Ahora enviá la foto de evidencia:
```
→ si manda otra cosa que no sea una foto:
```
❌ Enviá una foto (no texto). O escribí 'cancelar' para abortar.
```
→ al mandar la foto, confirmación final:
```
✅ 123456789 baneado y agregado a la lista negra.
Expulsado de 4/4 grupos.
Motivo: (el motivo escrito)
```
Cancelar en cualquier punto → `❎ Baneo cancelado.`

**Ver reporte** (desde el detalle de un usuario ya baneado) — manda una
foto nueva con esta descripción:
```
[FOTO de evidencia]
📋 Reporte de baneo
123456789

Motivo: (el motivo)
Admin: 987654321
Fecha: 2026-09-05

[✖️ Cerrar]
```

### 4.3 🧩 Módulos

**Lista:**
```
🧩 Módulos

✅ activo / ⛔ inactivo — 🧪 externo / 🏠 interno — ⚠️ sin carpeta en disco — página 1/3

[✅ 🧪 Eco]                [✅ 🧪 Trivia]
[⛔ 🧪 Publicador Prod]     [✅ 🧪 Buscador]

[⬅️        📄 1/3        ➡️]
[🔍 Detectar módulos]
[⬅️ Volver]
[✖️ Cerrar]
```

**Detalle de un módulo:**
```
🧩 Trivia
trivia

Estado: ✅ activo
Origen: 🧪 externo
Cargado en memoria: sí
Carpeta en disco: sí
Versión: 1.0.0
Permisos: mensajes.enviar, usuarios.registrar

[⛔ Desactivar]
[🔁 Marcar interno]
[🗑 Eliminar]
[⬅️ Volver]
[✖️ Cerrar]
```
Si el módulo está inactivo, el primer botón dice "✅ Activar" en vez de
"⛔ Desactivar". Si algo salió mal al activarlo, el motivo del error
aparece como una línea de aviso arriba del todo (ej. "⚠️ El módulo pide
un permiso desconocido").

**Confirmar eliminación:**
```
🗑 ¿Eliminar Trivia?
trivia

Se desregistra del SDK (se desactiva y se borra su fila de registro).
El archivo sigue en disco — "Detectar módulos" lo vuelve a encontrar
como nuevo (inactivo) más adelante.

[✅ Sí, eliminar]
[⬅️ Cancelar]
[✖️ Cerrar]
```

### 4.4 🏘 Grupos

**Lista:**
```
🏘 Grupos

✅ activo / ⛔ inactivo — página 1/2

[✅ 👥 Grupo Principal]
[⛔ 👥 Canal Secundario]

[⬅️        📄 1/2        ➡️]
[⬅️ Volver]
[✖️ Cerrar]
```

**Detalle de un grupo:**
```
🏘 Grupo Principal
-1001234567890

Tipo: supergroup
Estado: ✅ activo
Agregado: 2026-08-15 10:30:00
Principal: ⭐ sí
Ingreso de nuevo miembro: 🧮 Captcha

[⛔ Desactivar]
[🛂 Aprobación admin]        [🚫 Ninguno]
🔗 Último link: https://t.me/+xxxxxxxxxxxx
[🔗 Generar nuevo link]
[⬅️ Volver]
[✖️ Cerrar]
```
Los botones de modo de ingreso solo muestran las **dos** opciones que
NO son la actual (acá falta "🧮 Captcha" porque ya está activa). Si el
grupo no es el principal, aparece además un botón "⭐ Marcar como
principal". El botón de generar link solo aparece si el grupo es el
principal, o si tiene el modo "🛂 Aprobación admin" activo.

### 4.5 🛠 Mantenimiento

```
🛠 Mantenimiento

Estado: ✅ inactivo

[🟡 30 min]        [🟠 2 h]
[🔵 Indefinido]
[⬅️ Volver]
[✖️ Cerrar]
```

Con una ventana activa:
```
🛠 Mantenimiento

Estado: 🟡 activo
Desde: 2026-09-05 14:00
Restante: 1 h 45 min
Motivo: mantenimiento_120_minutos

[🟡 30 min]        [🟠 2 h]
[🔵 Indefinido]
[✅ Finalizar mantenimiento]
[⬅️ Volver]
[✖️ Cerrar]
```

---

## 5. `/otorgar` (créditos, solo texto)

Comando de una sola línea, sin botones propios (más allá del "Cerrar"
automático de cualquier mensaje de servicio). Root-only, DM o grupo de
gestión.

```
Uso: /otorgar <user_id> <cantidad> [motivo]

[✖️ Cerrar]
```

Si el destinatario nunca usó `/start`/`/perfil`:
```
❌ 555555555 no está registrado todavía (tiene que usar /start o /perfil primero).

[✖️ Cerrar]
```

Éxito:
```
✅ Otorgados 50 créditos a 555555555.
Nuevo saldo: 90
Motivo: otorgado manualmente desde /otorgar
tx_a1b2c3d4

[✖️ Cerrar]
```

---

## 6. Mictlantecuhtli (segundo bot, solo texto — sin botones)

Comandos root-only, DM o grupo de gestión, silencio total para
cualquier otro caso. Todo son respuestas de texto plano, sin ningún
botón inline.

`/reactivar` (sin todavía haber pedido nada):
```
✅ Todo en orden, no hace falta reactivar nada.
```
o, si el bot principal está caído:
```
🔑 Enviá /reactivar <secreto> dentro de los próximos 30s.
```
Si la ventana venció:
```
⏱ No hay una ventana de recuperación abierta (o venció). Corré /reactivar de nuevo.
```
Secreto incorrecto:
```
❌ Secreto incorrecto.
```
Éxito:
```
✅ Reactivado. Grupos liberados (4/4).
```

`/tecuhtli_simular <fase>`:
```
Uso: /tecuhtli_simular <normal|alerta|critico|respaldo_activo|recuperacion_pendiente>
```
o, al forzar una fase:
```
🧪 Fase simulada: respaldo_activo
```

---

## 7. Cómo se ve un módulo externo típico

Un módulo externo (`eco`, `trivia`, etc.) no tiene ningún panel propio
del sistema — arma su propia pantalla con las mismas piezas visuales
que el resto del bot (mensaje con botón "Cerrar" automático, o mensajes
que se editan a sí mismos con botones propios). Dos ejemplos reales ya
instalados:

**`/eco <texto>`** — responde en una sola línea:
```
🔊 eco (rol=miembro): lo que hayas escrito

[✖️ Cerrar]
```

**`/trivia`** — arma su propio mini-juego con botones de opción
múltiple, muy similar en estilo al captcha de bienvenida (§3.1):
```
❓ ¿Cuál es la capital de Francia?

[🅰️ Madrid]
[🅱️ París]
[🅲️ Roma]
[🚫 Salir]
```
Al responder, el mismo mensaje se edita mostrando si acertó o no, con
un botón para pedir "🔁 Otra pregunta" o "🚫 Salir" (que muestra el
puntaje acumulado y cierra el juego).
