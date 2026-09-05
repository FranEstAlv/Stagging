# Interfaz de Mictlán — catálogo visual rediseñado

> **Objetivo de esta versión:** conservar la lógica y cobertura funcional del inventario original, pero cambiar la capa de UX writing y presentación para que Mictlán se sienta más humano, claro y reconocible dentro de Telegram.
>
> La voz del bot es breve, directa y ligeramente temática. Mictlán no habla como una consola técnica cuando no hace falta: primero explica **qué pasó** y **qué puede hacer la persona ahora**. Los datos técnicos siguen apareciendo donde ayudan a administrar o diagnosticar.

## 1. Lenguaje visual y patrones de toda la interfaz

### Identidad

La interfaz usa una estética textual consistente con Mictlán sin convertir cada mensaje en una referencia mitológica.

- 💀 identifica Mictlán, perfiles o elementos ligados a identidad.
- 🔥 se usa para entrada, actividad y momentos de bienvenida.
- 🪶, 🏛️ y 🕯️ funcionan como decoradores temáticos cuando aportan carácter.
- 🟢, 🟡 y 🔴 comunican estados.
- ✅, ⚠️, ❌, 🚫, ➕, ➖ y 🗑️ conservan un significado funcional estable.
- Los títulos son cortos y reconocibles.
- Se evita repetir etiquetas técnicas cuando una frase normal comunica mejor la misma información.

### Botón «Cerrar»

Casi todo mensaje de servicio conserva como última acción:

```text
[✖️ Cerrar]
```

Tocarlo borra el mensaje. Si nadie lo toca, el mensaje se elimina automáticamente a los **30 minutos**. Esta sigue siendo la señal visual de que se trata de una pantalla temporal del bot.

### Volver

Siempre que exista una pantalla anterior, se usa una etiqueta contextual cuando sea posible:

```text
[← Usuarios]    [✖️ Cerrar]
```

Si no conviene nombrar la sección:

```text
[← Volver]      [✖️ Cerrar]
```

### Paginación

Las listas largas mantienen **6 elementos por página**, en dos columnas y tres filas. La navegación se simplifica:

```text
[Ítem 1]              [Ítem 2]
[Ítem 3]              [Ítem 4]
[Ítem 5]              [Ítem 6]

[⬅️]      [📄 1/3]      [➡️]
```

El botón `📄 1/3` sigue siendo informativo/refresco; no abre una pantalla distinta.

### Acceso restringido

Los comandos restringidos conservan la lógica original: `/mando`, `/otorgar`, `/reactivar` y `/tecuhtli_simular` pueden permanecer en silencio cuando se usan sin el rol o chat requerido. No se añade un mensaje que revele funciones administrativas a quien no debe verlas.

---

## 2. Comandos para cualquier miembro

### `/start`

**Pantalla:**

```text
💀  MICTLÁN

Bienvenido.
Desde aquí puedes consultar tu perfil y usar
las funciones disponibles para tu cuenta.

[👤 Ver mi perfil]
[✖️ Cerrar]
```

Si se desea mantener `/start` sin botón adicional por compatibilidad, el texto mínimo recomendado es:

```text
💀 Bienvenido a Mictlán.

Ya estás dentro. Usa /perfil cuando quieras
consultar tu acceso y tus créditos.

[✖️ Cerrar]
```

### `/perfil`

**Membresía activa:**

```text
💀  TU PERFIL

👤 Miembro
🟢 Tu acceso está activo hasta el 5 de octubre.
🪙 Tienes 40 créditos.

ID · 123456789

[✖️ Cerrar]
```

**Membresía vencida:**

```text
💀  TU PERFIL

👤 Miembro
🔴 Tu acceso venció el 5 de septiembre.
🪙 Tienes 40 créditos.

ID · 123456789

[✖️ Cerrar]
```

**Sin membresía:**

```text
💀  TU PERFIL

👤 Miembro
⚪ No tienes una membresía activa.
🪙 Tienes 40 créditos.

ID · 123456789

[✖️ Cerrar]
```

Para roles distintos, el nombre acompaña al emoji:

- 👤 Miembro
- 💼 Vendedor
- 🛠️ Administrador
- 👑 Root

### `/reporte <texto>`

**Si falta el mensaje:**

```text
🚩  ENVIAR UN REPORTE

Cuéntanos qué pasó después del comando.

Ejemplo:
/reporte alguien está enviando spam

[✖️ Cerrar]
```

**Reporte recibido:**

```text
✅  REPORTE ENVIADO

Gracias. Un administrador lo revisará.

[✖️ Cerrar]
```

**En el grupo de gestión:**

```text
🚩  REPORTE #14

👤 @usuario
ID · 123456789

“(texto del reporte)”

[✅ Marcar como atendido]
[✖️ Cerrar]
```

**Después de atenderlo:**

```text
🚩  REPORTE #14

👤 @usuario
ID · 123456789

“(texto del reporte)”

✅ @admin ya lo atendió.

[✖️ Cerrar]
```

### `/canales`

Solo funciona dentro del grupo principal y requiere membresía activa.

**Sin membresía:**

```text
🔒 Necesitas una membresía activa para entrar
a los canales de Mictlán.

[✖️ Cerrar]
```

**Selector:**

```text
🔗  CANALES DE MICTLÁN

¿A dónde quieres entrar?
Te daremos un enlace de un solo uso.

[📣 Nombre del canal 1]
[💬 Nombre del grupo 2]

[✖️ Cerrar]
```

**Sin destinos activos:**

```text
🔗  CANALES DE MICTLÁN

Por ahora no hay otros grupos o canales
disponibles.

[✖️ Cerrar]
```

**Después de elegir:**

```text
🔗  TU ENLACE ESTÁ LISTO

Úsalo una sola vez:
https://t.me/+xxxxxxxxxxxx

[📣 Nombre del canal 1]
[💬 Nombre del grupo 2]

[✖️ Cerrar]
```

---

## 3. Entrada de nuevos miembros

Cada grupo gestionado utiliza **un solo método de entrada** para miembros nuevos que no sean administrador/root.

### 3.1 Prueba de bienvenida

Al entrar, la persona permanece sin permiso para escribir hasta superar la prueba.

```text
🔥  CRUZA EL UMBRAL

Antes de entrar, una prueba rápida:

¿Cuánto es 7 + 12?

⏳ Tienes 3 minutos. Si se acaba el tiempo,
tendrás que intentar entrar de nuevo.

[9]        [19]
[23]       [15]
```

**Respuesta correcta:**

```text
🔥  EL UMBRAL ESTÁ ABIERTO

✅ Listo, ya puedes escribir en el grupo.
Bienvenido a Mictlán.
```

**Respuesta incorrecta — popup:**

```text
❌ Esa no es. Inténtalo otra vez.
```

La prueba continúa activa y la persona sigue sin poder escribir.

**Tiempo agotado:**

```text
⌛  SE CERRÓ EL UMBRAL

Se acabó el tiempo y saliste del grupo.
Puedes volver a entrar e intentarlo otra vez.
```

### 3.2 Entrada con aprobación

La persona queda temporalmente sin permiso para escribir y la decisión aparece en el grupo de gestión.

```text
🚪  ALGUIEN QUIERE ENTRAR

👤 @nuevo_usuario
ID · 123456789
🏛️ Nombre del Grupo

⏳ Hay 1 minuto para aceptar el ingreso.
Si nadie responde, el usuario saldrá del grupo.

[✅ Dejar entrar]
```

**Aceptado:**

```text
✅ @nuevo_usuario ya puede entrar.

Aprobado por @admin.
```

Si no existe username:

```text
✅ 123456789 ya puede entrar.

Aprobado por @admin.
```

**Tiempo agotado:**

```text
⌛ Nadie aprobó a 123456789 a tiempo.
El usuario salió del grupo.
```

Un usuario sin permisos suficientes sigue sin recibir respuesta visible al tocar el botón.

---

## 4. `/mando` — administración de Mictlán

Solo responde por DM con el bot o en el grupo de gestión, y únicamente al rol `root`.

### 4.1 Inicio

```text
💀  MICTLÁN

¿Qué quieres administrar?

[👥 Personas]
[🧩 Módulos]
[🏛️ Grupos]
[🕯️ Mantenimiento]

[✖️ Cerrar]
```

### 4.2 👥 Personas

#### Lista

```text
👥  PERSONAS

👤 Miembro · 💼 Vendedor
🛠️ Admin · 👑 Root · 🚫 Bloqueado

[👤 usuario1]              [💼 usuario2]
[🛠️ usuario3 🚫]           [👑 usuario4]
[👤 usuario5]              [👤 123456789]

[⬅️]      [📄 1/2]      [➡️]

[← Mictlán]    [✖️ Cerrar]
```

Cada botón conserva emoji de rol + username o ID + `🚫` si está bloqueado.

#### Detalle de una persona

```text
👤  @usuario1
ID · 123456789

👤 Miembro
🟢 Acceso hasta el 5 de octubre
🛡️ Sin restricciones

[➕ 7 días]      [➕ 30 días]
[➖ 7 días]      [➖ 30 días]

[🎭 Cambiar rol]
[🚫 Bloquear usuario]

[← Personas]    [✖️ Cerrar]
```

**Si está bloqueado:**

```text
👤  @usuario1
ID · 123456789

👤 Miembro
🟢 Acceso hasta el 5 de octubre
🚫 Usuario bloqueado

[➕ 7 días]      [➕ 30 días]
[➖ 7 días]      [➖ 30 días]

[🎭 Cambiar rol]
[✅ Desbloquear]
[📋 Ver motivo y evidencia]

[← Personas]    [✖️ Cerrar]
```

#### Cambiar rol

```text
🎭  CAMBIAR ROL

@usuario1
Ahora es: 👤 Miembro

¿A qué rol lo quieres cambiar?

[✅ 👤 Miembro]
[💼 Vendedor]
[🛠️ Administrador]
[👑 Root]

[← Cancelar]    [✖️ Cerrar]
```

El rol actual lleva `✅`.

#### Bloquear usuario — paso 1

```text
🚫  BLOQUEAR USUARIO

@usuario1
ID · 123456789

¿Por qué lo vas a bloquear?
Escribe el motivo en un mensaje.

[← Cancelar]
```

#### Paso 2: evidencia

```text
📸  FALTA LA EVIDENCIA

Ahora envía una foto que respalde el bloqueo.

Puedes escribir “cancelar” para salir.
```

**Si envía algo que no sea una foto:**

```text
📸 Necesito una foto como evidencia.

Envíala aquí o escribe “cancelar”.
```

#### Bloqueo terminado

```text
🚫  USUARIO BLOQUEADO

123456789 quedó en la lista de bloqueados.
🚪 Se retiró de los 4 grupos.

Motivo:
(el motivo escrito)

✅ Listo.
```

**Cancelar en cualquier punto:**

```text
↩️ Bloqueo cancelado. No se hizo ningún cambio.
```

#### Ver motivo y evidencia

Se envía la foto acompañada por:

```text
📋  BLOQUEO DE @usuario1

ID · 123456789

📝 Motivo
(el motivo)

🛠️ Aplicado por · 987654321
📅 5 de septiembre de 2026

[✖️ Cerrar]
```

---

### 4.3 🧩 Módulos

#### Lista

```text
🧩  MÓDULOS

🟢 Funcionando · ⚪ Apagado
🧪 Externo · 🏠 Interno
⚠️ Archivos no encontrados

[🟢 🧪 Eco]               [🟢 🧪 Trivia]
[⚪ 🧪 Publicador Prod]    [🟢 🧪 Buscador]

[⬅️]      [📄 1/3]      [➡️]

[🔎 Buscar módulos nuevos]
[← Mictlán]    [✖️ Cerrar]
```

#### Detalle de módulo activo

```text
🧩  TRIVIA
trivia · v1.0.0

🟢 Está funcionando
🧪 Módulo externo
📦 Archivos encontrados
⚙️ Cargado y listo

🔐 Puede usar:
• enviar mensajes
• registrar usuarios

[⏸️ Apagar]
[🏠 Convertir en interno]
[🗑️ Quitar módulo]

[← Módulos]    [✖️ Cerrar]
```

Los permisos pueden conservar sus identificadores técnicos en una línea secundaria si el administrador los necesita para diagnóstico:

```text
Detalles: mensajes.enviar · usuarios.registrar
```

#### Módulo inactivo

```text
🧩  TRIVIA
trivia · v1.0.0

⚪ Está apagado
🧪 Módulo externo
📦 Archivos encontrados

[▶️ Encender]
[🏠 Convertir en interno]
[🗑️ Quitar módulo]

[← Módulos]    [✖️ Cerrar]
```

#### Error al activar

```text
⚠️  TRIVIA NO PUDO INICIAR

Encontré un permiso que Mictlán no reconoce.

Permiso: (permiso desconocido)

Revisa el módulo antes de volver a encenderlo.

[← Módulo]    [✖️ Cerrar]
```

#### Confirmar eliminación

```text
🗑️  ¿QUITAMOS TRIVIA?

El módulo dejará de funcionar y desaparecerá
de Mictlán.

Su archivo no se borrará, así que podrás
encontrarlo e instalarlo otra vez después.

[🗑️ Sí, quitarlo]
[← Mejor no]
[✖️ Cerrar]
```

---

### 4.4 🏛️ Grupos

#### Lista

```text
🏛️  GRUPOS

🟢 Activo · ⚪ Inactivo

[🟢 👥 Grupo Principal]
[⚪ 📣 Canal Secundario]
[🟢 👥 Comunidad]

[⬅️]      [📄 1/2]      [➡️]

[← Mictlán]    [✖️ Cerrar]
```

#### Detalle del grupo principal

```text
🏛️  GRUPO PRINCIPAL

Grupo Principal
ID · -1001234567890

🟢 Está activo
⭐ Es el grupo principal
🚪 Entrada: prueba rápida
📅 Añadido el 15 de agosto de 2026

Tipo · supergroup

[⏸️ Desactivar]

Cambiar forma de entrada:
[🛂 Aprobación]    [🚪 Entrada libre]

🔗 Último enlace
https://t.me/+xxxxxxxxxxxx

[🔗 Crear otro enlace]

[← Grupos]    [✖️ Cerrar]
```

La opción actualmente activa no se muestra entre los botones de cambio. En este ejemplo no aparece `🔥 Prueba rápida` porque ya está seleccionada.

#### Grupo secundario

```text
🏛️  CANAL SECUNDARIO

Canal Secundario
ID · -1009876543210

🟢 Está activo
🚪 Entrada: aprobación
📅 Añadido el 20 de agosto de 2026

Tipo · supergroup

[⏸️ Desactivar]
[⭐ Hacerlo principal]

Cambiar forma de entrada:
[🔥 Prueba rápida]    [🚪 Entrada libre]

[← Grupos]    [✖️ Cerrar]
```

El botón para crear un enlace aparece únicamente cuando la lógica original lo permite: grupo principal o grupo con aprobación administrativa activa.

---

### 4.5 🕯️ Mantenimiento

#### Estado normal

```text
🕯️  MANTENIMIENTO

🟢 Todo funciona normalmente.

¿Necesitas pausar Mictlán por un rato?

[🟡 30 minutos]    [🟠 2 horas]
[🔵 Hasta que yo vuelva]

[← Mictlán]    [✖️ Cerrar]
```

#### Mantenimiento activo

```text
🕯️  MICTLÁN ESTÁ EN PAUSA

🟡 Mantenimiento activo
🕑 Empezó a las 14:00
⏳ Quedan 1 h 45 min

Puedes cambiar la duración o terminarlo ahora.

[🟡 30 minutos]    [🟠 2 horas]
[🔵 Sin límite]
[✅ Volver a abrir Mictlán]

[← Mictlán]    [✖️ Cerrar]
```

El identificador interno `mantenimiento_120_minutos` deja de mostrarse como “Motivo” en la interfaz normal. Si se necesita para diagnóstico, puede mostrarse en una vista técnica separada, no como texto principal para el usuario.

---

## 5. `/otorgar` — créditos

Sigue siendo un comando root-only disponible por DM o en el grupo de gestión.

### Falta información

```text
🪙  DAR CRÉDITOS

Escribe:
/otorgar <usuario> <cantidad> [motivo]

Ejemplo:
/otorgar 555555555 50 premio

[✖️ Cerrar]
```

### Usuario no registrado

```text
❌ No encuentro a 555555555 en Mictlán.

Primero debe usar /start o /perfil para
registrar su cuenta.

[✖️ Cerrar]
```

### Éxito

```text
🪙  CRÉDITOS ENTREGADOS

✅ 50 créditos para 555555555.
💰 Nuevo saldo: 90

📝 Motivo
otorgado manualmente desde /otorgar

Referencia · tx_a1b2c3d4

[✖️ Cerrar]
```

La referencia de transacción se conserva porque puede ser útil para administración, pero queda visualmente separada del mensaje principal.

---

## 6. Mictlantecuhtli — bot de respaldo

Este segundo bot continúa usando solo texto y sin botones inline. Los comandos son root-only y solo funcionan por DM o en el grupo de gestión. Fuera de esos casos se conserva el silencio total.

### `/reactivar`

**Si todo está bien:**

```text
🟢 Todo está en orden.
Mictlán no necesita recuperación.
```

**Si Mictlán está caído:**

```text
🔑  RECUPERACIÓN ABIERTA

Envía /reactivar <secreto> en los próximos
30 segundos.
```

**Si la ventana venció:**

```text
⌛ Ese intento de recuperación ya venció.

Usa /reactivar para iniciar uno nuevo.
```

**Clave incorrecta:**

```text
❌ Esa clave no es correcta.
```

**Recuperación terminada:**

```text
🔥 Mictlán volvió.

✅ Los 4 grupos quedaron liberados.
```

### `/tecuhtli_simular <fase>`

Este comando sí es deliberadamente técnico porque su usuario es root y su propósito es diagnóstico.

**Sin fase:**

```text
🧪  SIMULAR ESTADO

Usa:
/tecuhtli_simular <fase>

Fases:
normal · alerta · critico
respaldo_activo · recuperacion_pendiente
```

**Al forzar una fase:**

```text
🧪 Simulación activa: respaldo_activo
```

Para una futura revisión técnica se puede traducir el nombre de la fase en pantalla sin cambiar el identificador que usa el comando.

---

## 7. Módulos externos

Los módulos externos (`eco`, `trivia`, etc.) conservan libertad para construir sus propias pantallas, pero deben sentirse parte del mismo bot.

Reglas recomendadas:

- título breve;
- una acción principal clara;
- emojis con significado;
- `✖️ Cerrar` en mensajes de servicio;
- `← Volver` o `🚫 Salir` cuando exista un flujo;
- evitar nombres de variables, roles internos o identificadores técnicos en mensajes para miembros;
- editar el mismo mensaje cuando la interacción sea parte de una sola pantalla.

### `/eco <texto>`

En vez de exponer `rol=miembro`:

```text
🔊  ECO

lo que hayas escrito

[✖️ Cerrar]
```

Si el rol es relevante para la función, se puede mostrar de forma humana:

```text
🔊  ECO · 👤 Miembro

lo que hayas escrito

[✖️ Cerrar]
```

### `/trivia`

```text
🧠  TRIVIA

¿Cuál es la capital de Francia?

[🅰️ Madrid]
[🅱️ París]
[🅲️ Roma]

[🚪 Salir]
```

**Respuesta correcta:**

```text
🎉  ¡CORRECTO!

París 🇫🇷

🔥 Llevas 3 aciertos.

[🔁 Otra pregunta]
[🚪 Terminar]
```

**Respuesta incorrecta:**

```text
😵  CASI

La respuesta era París 🇫🇷

🔥 Llevas 2 aciertos.

[🔁 Otra pregunta]
[🚪 Terminar]
```

**Al terminar:**

```text
🏁  FIN DE LA TRIVIA

Conseguiste 3 aciertos.
¡Nos vemos en la siguiente! 💀
```

---

## 8. Catálogo de microcopy y estados

Esta sección normaliza frases para que módulos actuales y futuros hablen con la misma voz.

### Estados

| Situación | Texto recomendado |
|---|---|
| Activo | 🟢 Está funcionando |
| Inactivo | ⚪ Está apagado |
| Mantenimiento | 🟡 Mictlán está en pausa |
| Correcto | ✅ Listo |
| Error recuperable | ⚠️ Algo no salió bien |
| Error definitivo | ❌ No se pudo completar |
| Bloqueado | 🚫 Usuario bloqueado |
| Sin restricciones | 🛡️ Sin restricciones |
| Esperando | ⏳ Esperando respuesta |
| Tiempo agotado | ⌛ Se acabó el tiempo |
| Archivos presentes | 📦 Archivos encontrados |
| Sin archivos | ⚠️ No encuentro sus archivos |

### Acciones

| Antes | Nuevo texto |
|---|---|
| Banear | Bloquear usuario |
| Desbanear | Desbloquear |
| Detectar módulos | Buscar módulos nuevos |
| Desactivar | Apagar / Desactivar, según contexto |
| Activar | Encender / Activar, según contexto |
| Eliminar módulo | Quitar módulo |
| Aprobación admin | Aprobación |
| Ninguno | Entrada libre |
| Finalizar mantenimiento | Volver a abrir Mictlán |
| Generar nuevo link | Crear otro enlace |
| Ver reporte | Ver motivo y evidencia |

### Fechas y cantidades

Para mensajes humanos se prefieren fechas legibles:

```text
5 de octubre de 2026
```

En vistas técnicas puede conservarse:

```text
2026-10-05
```

Los tiempos deben priorizar expresiones naturales:

```text
⏳ Quedan 1 h 45 min
```

en lugar de exponer identificadores como:

```text
mantenimiento_120_minutos
```

---

## 9. Principios para nuevas pantallas

Todo panel nuevo de Mictlán debería poder revisarse con estas preguntas:

1. **¿Se entiende en pocos segundos qué pasó?**
2. **¿Está claro qué puede hacer la persona ahora?**
3. **¿Hay datos técnicos que podamos mover a segundo plano?**
4. **¿Los botones usan verbos y nombres que una persona diría?**
5. **¿El emoji ayuda a leer o solo decora?**
6. **¿El mismo estado usa el mismo símbolo en todo Mictlán?**
7. **¿Podemos editar el mensaje actual en vez de llenar el chat de mensajes?**
8. **¿La referencia a Mictlán aporta identidad sin estorbar?**

La meta no es que el bot “hable náhuatl” ni que cada línea sea temática. La meta es que se sienta como **Mictlán**: oscuro, reconocible, directo y con personalidad, sin sacrificar claridad.

---

## 10. Resumen del sistema visual

La interfaz queda organizada en cuatro niveles:

**💀 Identidad**  
Mictlán, perfil, encabezados principales y cierres de flujo.

**🔥 Actividad y acceso**  
Bienvenida, ingreso, recuperación y acciones que “abren” o “cierran” el acceso.

**🟢 🟡 🔴 Estado**  
Funcionando, atención necesaria y problemas/bloqueos.

**🪶 🏛️ 🕯️ Ambientación**  
Decoradores usados con moderación para dar carácter sin volver ruidosa la interfaz.

Con este sistema, un módulo nuevo puede verse distinto por función, pero seguir sintiéndose parte del mismo bot.
