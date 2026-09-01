# Desplegar Mictlantecuhtli como servicio systemd

Instrucciones para levantar `mictlantecuhtli.py` (segundo bot de
respaldo/failover — máquina de estados en `mictlan/tecuhtli/`, detalle
completo en `CLAUDE.md`) como servicio systemd real, con reinicio
automático. Comandos exactos, para copiar y pegar tal cual.

**Estado actual en `mictlan-staging` (ambiente de pruebas)**: corre como
proceso manual (`nohup python mictlantecuhtli.py &`), no como servicio
systemd — la sesión de Claude Code que lo desplegó no tiene sudo para
crear unidades nuevas (su sudo está acotado solo a los servicios que ya
existen, ver "Permisos de sudo en el VPS (política)" en `CLAUDE.md`).
Este documento es para que vos lo conviertas en un servicio de verdad,
ahí o en producción.

## 0. Prerrequisitos

- Un token de Telegram **propio** para Mictlantecuhtli, distinto del
  bot principal — se saca hablándole a `@BotFather` (`/newbot`).
- Agregar ese bot como **administrador** (con permiso de "Restringir
  miembros" / *Restrict members* habilitado) en cada grupo/canal que
  Mictlantecuhtli deba poder proteger — sin ese permiso,
  `set_chat_permissions` falla silenciosamente para ese grupo (queda
  contado en "fallidos" en los avisos, no rompe nada, pero no protege
  ese chat).
- Un secreto de recuperación elegido por vos (se puede generar uno
  fuerte con `python3 -c "import secrets; print(secrets.token_urlsafe(24))"`).

## 1. Variables de entorno

Agregar al `.env` del bot principal correspondiente (production:
`/home/olimpo/mictlan/.env`; staging:
`/home/olimpo/mictlan-staging/.env`) — Mictlantecuhtli lee el mismo
`.env` que el bot principal, porque usan la misma `DATABASE_URL`:

```bash
cat >> /home/olimpo/mictlan/.env << 'EOF'

# Mictlantecuhtli (segundo bot de respaldo, mictlantecuhtli.py)
MICTLANTECUHTLI_BOT_TOKEN=<token de @BotFather>
TECUHTLI_SECRETO_RECUPERACION=<tu secreto>
EOF
```

El resto de las variables (`TECUHTLI_ALERTA_SEGUNDOS`,
`TECUHTLI_CRITICO_SEGUNDOS`, `TECUHTLI_RESPALDO_SEGUNDOS`,
`TECUHTLI_HEARTBEAT_INTERVAL_SEGUNDOS`,
`TECUHTLI_EVALUAR_INTERVALO_SEGUNDOS`,
`TECUHTLI_VENTANA_RECUPERACION_SEGUNDOS`) son opcionales, tienen default
razonable — ver `.env.example` y `mictlan/tecuhtli/estado.py` si hace
falta ajustarlas.

## 2. Archivo de unidad systemd

Crear `/etc/systemd/system/mictlantecuhtli.service` con exactamente este
contenido (mismo patrón que `mictlan.service`, solo cambia
`ExecStart`/`Description`):

```bash
sudo tee /etc/systemd/system/mictlantecuhtli.service > /dev/null << 'EOF'
[Unit]
Description=Mictlantecuhtli (segundo bot de respaldo de Mictlan)
After=network.target postgresql.service

[Service]
Type=simple
User=olimpo
WorkingDirectory=/home/olimpo/mictlan
EnvironmentFile=/home/olimpo/mictlan/.env
ExecStart=/home/olimpo/mictlan/venv/bin/python mictlantecuhtli.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

Para `mictlan-staging`, cambiar `WorkingDirectory`,
`EnvironmentFile` y `ExecStart` a
`/home/olimpo/mictlan-staging/...` (sin `postgresql.service` en
`After=`, staging usa SQLite) y el nombre del archivo a
`mictlan-staging-tecuhtli.service`.

## 3. Habilitar y arrancar

```bash
sudo systemctl daemon-reload
sudo systemctl enable mictlantecuhtli.service
sudo systemctl start mictlantecuhtli.service
```

## 4. Verificar que arrancó bien

```bash
sudo systemctl status mictlantecuhtli.service
sudo journalctl -u mictlantecuhtli.service -n 50 --no-pager
```

Confirmar en el journal que no hay ningún traceback (en particular
`telegram.error.InvalidToken`, si el token está mal). Verificación
funcional real, no solo "arrancó":

- Hablarle en DM al bot nuevo con `/tecuhtli_simular respaldo_activo` —
  debería avisar en el grupo de gestión (`ADMIN_GROUP_ID`) y restringir
  los grupos gestionados de verdad.
- Después, `/reactivar` (sin argumentos) y, dentro de los 30s
  siguientes, `/reactivar <TECUHTLI_SECRETO_RECUPERACION>` — debería
  liberar los grupos y volver a fase `normal`.
- `/tecuhtli_simular normal` para dejarlo limpio.

## 5. (Opcional) Sudo acotado para que Claude Code administre este servicio

Mismo patrón que ya existe para `mictlan.service`/`mictlan-staging.service`
(ver "Permisos de sudo en el VPS (política)" en `CLAUDE.md`) — agregar
con `visudo` (nunca a mano ni por fuera de ese comando):

```
olimpo ALL=(root) NOPASSWD: /usr/bin/systemctl start mictlantecuhtli.service
olimpo ALL=(root) NOPASSWD: /usr/bin/systemctl stop mictlantecuhtli.service
olimpo ALL=(root) NOPASSWD: /usr/bin/systemctl restart mictlantecuhtli.service
olimpo ALL=(root) NOPASSWD: /usr/bin/systemctl status mictlantecuhtli.service
olimpo ALL=(root) NOPASSWD: /usr/bin/journalctl -u mictlantecuhtli.service
```

Sin esto, cualquier sesión de Claude Code puede seguir *escribiendo*
código para Mictlantecuhtli, pero no puede reiniciar el servicio ni leer
su journal sin que vos tipees la contraseña a mano.
