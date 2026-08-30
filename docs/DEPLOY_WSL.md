# Desplegar Reto4V en WSL2 con Docker Engine

Esta guía sirve para la primera versión de Reto4V en una máquina Windows que ejecuta
Ubuntu dentro de WSL2. El motor de contenedores es **Docker Engine dentro de
WSL**; Docker Desktop no es un requisito ni una dependencia del despliegue.

Reto4V y PostgreSQL se ejecutan en contenedores Linux. PostgreSQL no publica
ningún puerto en Windows: solo es accesible desde la red privada de Compose.
El único puerto de aula es el de `web` (por defecto TCP 8080).

## 1. Arquitectura y decisiones de red

```text
ordenador del alumno
        │ TCP 8080 (LAN)
        ▼
Windows Firewall / (portproxy si NAT)
        │
        ▼
WSL2 / Docker Engine
        │ puerto publicado
        ▼
 web directo o Caddy:8080 ── red edge ── web:8000
                                           │
                                  red backend (internal)
                                           │
                                       db:5432
                                  (volumen persistente)
```

Hay dos variantes:

| Variante | Cuándo usarla | Acceso desde la LAN |
|---|---|---|
| WSL2 NAT (predeterminada) | Windows Server o equipos donde mirrored no esté disponible | Regla de `netsh interface portproxy` hacia la IP cambiante de WSL y regla del Firewall de Windows. |
| WSL2 mirrored | Windows 11 22H2 o posterior, si la política del centro lo permite | WSL comparte las interfaces/IP de Windows; se mantiene una regla del Firewall de Windows y del firewall Hyper-V. |

Microsoft documenta mirrored para Windows 11 22H2 o posterior. No se debe
asumir que está disponible en Windows Server: en ese caso se utiliza NAT y
portproxy. La propia documentación de Microsoft indica también que WSL2 NAT
no expone automáticamente una aplicación a otros equipos de la LAN.

La base de datos, los archivos estáticos recopilados y `media` viven en
volúmenes Docker con nombre. Mantén el proyecto y los volúmenes en el sistema
de archivos Linux de WSL (por ejemplo `/opt/reto4v`), no en `/mnt/c`, para
evitar la penalización de I/O de WSL. Los backups sí pueden copiarse después a
una carpeta de Windows.

## 2. Prerrequisitos

- Windows con virtualización habilitada y WSL2 actualizado.
- Ubuntu 22.04/24.04 dentro de WSL2.
- Una cuenta con permisos de administrador en Windows y `sudo` en Ubuntu.
- Al menos 4 GB de RAM para la VM WSL y espacio para imágenes, PostgreSQL y
  backups. Para una clase de 25–35 alumnos, 2–4 vCPU y 8 GB ofrecen margen.
- Una IP o reserva DHCP del equipo Windows y un nombre DNS interno, si el
  centro lo tiene. Usa el nombre del centro o un dominio interno; evita
  `.local` si puede interferir con mDNS.

Comprueba la versión de WSL desde PowerShell:

```powershell
wsl --version
wsl --status
wsl --list --verbose
```

La distribución debe mostrar `VERSION 2`. Si WSL no está instalado, la forma
habitual en una consola de PowerShell elevada es:

```powershell
wsl --install --no-distribution
wsl --set-default-version 2
wsl --install --distribution Ubuntu-24.04
```

En ediciones de Windows Server donde esos comandos no estén disponibles,
instala WSL y la distribución siguiendo el procedimiento aprobado por el
centro y vuelve a comprobar `wsl --list --verbose`. No instales Docker Desktop
para resolver esta parte.

## 3. Activar systemd en WSL

Docker Engine se administrará con systemd. Dentro de Ubuntu, crea o edita
`/etc/wsl.conf`:

```ini
[boot]
systemd=true
```

> **Importante:** cierra y reinicia la instancia desde PowerShell para que la
> configuración sea efectiva.

```powershell
wsl --shutdown
wsl --distribution Ubuntu-24.04
```

Comprueba dentro de Ubuntu:

```bash
systemctl is-system-running
```

Si `systemctl` no existe, actualiza WSL y comprueba que están instalados
`systemd` y `systemd-sysv` antes de repetir el reinicio. Microsoft mantiene la
configuración de systemd y la diferencia entre `/etc/wsl.conf` y
`%UserProfile%\\.wslconfig` en su documentación de WSL.

## 4. Instalar Docker Engine y Compose v2

Los siguientes comandos siguen el repositorio oficial de Docker para Ubuntu.
Ejecuta esto dentro de Ubuntu, con salida a Internet únicamente durante la
instalación:

```bash
sudo apt-get update
sudo apt-get install --yes ca-certificates curl
sudo install --mode=0755 --directory /etc/apt/keyrings
sudo curl --fail --silent --show-error --location \
  https://download.docker.com/linux/ubuntu/gpg \
  --output /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt-get update
sudo apt-get install --yes docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
```

Si la distribución no es Ubuntu 24.04 (`noble`), sustituye `Suites: noble` por
el valor de `VERSION_CODENAME` que muestra `/etc/os-release`, o sigue la
variante oficial de Docker para esa versión. No mezcles `docker.io`, el
paquete antiguo `docker-compose` y Docker Engine del repositorio oficial en la
misma instalación.

Arranca el servicio y valida el plugin:

```bash
sudo systemctl enable --now docker
sudo systemctl status docker --no-pager
sudo usermod --append --groups docker "$USER"
newgrp docker
docker version
docker compose version
docker run --rm hello-world
```

El último comando solo descarga una imagen de verificación; puede omitirse si
el centro no quiere descargarla. Pertenecer al grupo `docker` equivale en la
práctica a tener privilegios elevados sobre el host: usa una cuenta de
operación limitada y no compartas el socket Docker.

## 5. Copiar el proyecto al sistema de archivos Linux

Mantén el código y los volúmenes dentro del sistema de archivos Linux de WSL.
La forma más sencilla es clonar el repositorio público en tu carpeta de
usuario; no hace falta dar permisos de root al checkout:

```bash
git clone https://github.com/jalinhabrava/Reto4V.git Reto4V
cd Reto4V
```

Si la política del centro exige `/opt/reto4v`, crea esa ruta una vez con
`sudo`, clona y devuelve la propiedad del checkout al usuario de operación.
Si recibes el código desde Windows, copia el árbol de trabajo a una ruta Linux
con `cp --archive`, pero no copies un `.env` que contenga credenciales desde
una carpeta compartida.

## 6. Instalación de Reto4V

El instalador es idempotente y no instala paquetes del sistema ni usa `sudo`.
Comprueba Docker Engine y Compose v2, crea `.env` con secretos aleatorios
independientes y permisos `600`, valida la configuración, construye la imagen,
ejecuta migraciones, inicia los servicios y comprueba `/health/`.

Para una prueba en el propio servidor:

```bash
cd "$HOME/Reto4V"
bash scripts/install.sh --host localhost --port 8080
```

Para publicar en una red de aula mediante la IP o DNS del servidor:

```bash
bash scripts/install.sh --host 192.168.20.10 --port 8080
```

El script ofrece crear la primera cuenta administradora de forma interactiva.
En una ejecución sin terminal puedes crearla después con:

```bash
docker compose --env-file .env exec web python manage.py createsuperuser
```

Para cargar los retos Bash de demostración de 2.º ASIR:

```bash
bash scripts/install.sh --no-build --skip-admin --seed-bash \
  --owner profesor --cohort 2ASIR
```

`web` ejecuta las migraciones y `collectstatic` antes de Gunicorn. Un reinicio
normal no elimina los volúmenes. No uses `docker compose down -v` en la
instalación real: elimina los datos de PostgreSQL y los archivos locales.

La base de datos solo está en la red Compose `backend`, marcada como `internal`;
`web` también se conecta a la red `edge` para que el puerto publicado y Caddy
puedan servir la aplicación. Reto4V no necesita CDN, fuentes, analytics ni APIs
para funcionar. La conectividad de salida del contenedor web no es una frontera
de seguridad: si el centro la necesita, bloquéala con la política del host o del
firewall. Conserva las imágenes ya construidas si vas a trabajar sin Internet.

## 7. Publicar el puerto en la LAN

### 7.1 Directo, sin Caddy

Es el modo por defecto. `web` escucha en el puerto 8000 del contenedor y
Compose lo publica en `${APP_BIND_IP}:${APP_PORT}` (por defecto
`0.0.0.0:8080`). Desde Ubuntu y desde el propio Windows debería responder:

> Este modo HTTP directo sirve para la prueba técnica de Fase 0. Antes de
> introducir credenciales o notas reales, usa TLS interno (Caddy u otro proxy
> del centro) y completa la revisión de seguridad y protección de datos.

```bash
curl --fail http://127.0.0.1:8080/health/
```

El comportamiento de LAN depende del modo de red WSL.

### 7.2 NAT: portproxy + Firewall de Windows

Este es el procedimiento recomendado para Windows Server y para Windows 10/11
cuando no se usa mirrored. La IP de WSL puede cambiar tras `wsl --shutdown` o
un reinicio.

En PowerShell **como Administrador**:

```powershell
$Distro = "Ubuntu-24.04"
$WslIp = (wsl.exe --distribution $Distro hostname -I).Trim().Split()[0]
$ListenPort = 8080

Set-Service -Name iphlpsvc -StartupType Automatic
Start-Service -Name iphlpsvc
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$ListenPort
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=$ListenPort connectaddress=$WslIp connectport=$ListenPort

# Sustituye estas redes por la subred exacta del aula si es posible.
New-NetFirewallRule -DisplayName "Reto4V LAN TCP $ListenPort" `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort $ListenPort `
  -Profile Domain,Private -RemoteAddress 10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
```

El repositorio incluye `scripts/update-wsl-portproxy.ps1`, que obtiene la IP,
actualiza la regla y mantiene `iphlpsvc` iniciado:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\scripts\update-wsl-portproxy.ps1 `
  -Distro Ubuntu-24.04 -ListenPort 8080 -ConnectPort 8080
```

Ejecuta el script después de cada reinicio de WSL o crea una tarea programada
de Windows que lo ejecute al iniciar sesión/arrancar el servidor, con la
cuenta de operación aprobada por el centro. Comprueba el resultado:

```powershell
netsh interface portproxy show v4tov4
Test-NetConnection <nombre-o-ip-del-servidor> -Port 8080
```

No expongas el puerto de PostgreSQL. `listenaddress=0.0.0.0` acepta tráfico de
cualquier interfaz; la regla de Firewall y una subred remota estrecha son la
barrera que limita el acceso.

### 7.3 Mirrored: acceso directo con Firewall Hyper-V

Mirrored está documentado por Microsoft para Windows 11 22H2 o posterior. No
lo uses como supuesto en Windows Server. En `%UserProfile%\.wslconfig` (archivo
de Windows, no `/etc/wsl.conf`) puedes configurar:

```ini
[wsl2]
networkingMode=mirrored
firewall=true
dnsTunneling=true
```

Reinicia WSL:

```powershell
wsl --shutdown
```

En mirrored, WSL comparte las interfaces/IP de Windows y no se necesita
portproxy. Aun así, crea reglas explícitas y limitadas. Microsoft muestra la
regla Hyper-V con este identificador de creador de WSL:

```powershell
New-NetFirewallHyperVRule -Name "Reto4V-8080" `
  -DisplayName "Reto4V WSL TCP 8080" -Direction Inbound `
  -VMCreatorId "{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}" `
  -Protocol TCP -LocalPorts 8080
New-NetFirewallRule -DisplayName "Reto4V LAN TCP 8080" `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080 `
  -Profile Domain,Private -RemoteAddress 10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
```

Si el puerto ya está ocupado por un proceso de Windows, elige otro puerto
LAN. `ignoredPorts` puede cambiar el comportamiento de binding en mirrored,
pero no debe utilizarse para ocultar un conflicto de puertos sin una prueba
de LAN y firewall:

```ini
[wsl2]
networkingMode=mirrored
firewall=true
ignoredPorts=8080
```

## 8. Proxy Caddy opcional

El perfil `proxy` ofrece una única entrada y es la opción recomendada para
añadir TLS interno. El `Caddyfile` normal es HTTP y sirve únicamente para
pruebas. `Caddyfile.internal-tls` usa `tls internal`, guarda la CA en el
volumen `caddy_data` y requiere confiar esa CA en los equipos del aula; como
alternativa, el centro puede montar su propio certificado y proxy.

En `.env`, reserva un puerto interno para `web` y el puerto LAN para Caddy. El
perfil Caddy escucha internamente en 8080, sin redirección automática a :80, y
por defecto se publica en 8081:

```dotenv
APP_BIND_IP=127.0.0.1
APP_PORT=8000
CADDY_BIND_IP=0.0.0.0
CADDY_HTTP_PORT=8080
CADDYFILE=./Caddyfile
CADDY_SITE_ADDRESS=:8080
DJANGO_ALLOWED_HOSTS=reto4v.instituto.lan,192.168.20.10
DJANGO_CSRF_TRUSTED_ORIGINS=http://reto4v.instituto.lan:8080,http://192.168.20.10:8080
```

Arranca solo el perfil proxy:

```bash
docker compose --env-file .env --profile proxy up -d
```

La imagen oficial de Caddy conserva una capacidad de archivo que requiere
`NET_BIND_SERVICE` para poder ejecutar su binario, aunque se use el puerto
8080. Compose conserva **solo esa capacidad en Caddy**, además de
`no-new-privileges`; la aplicación web sigue sin capacidades. Véase la
[incidencia documentada por Caddy](https://github.com/caddyserver/caddy-docker/issues/396).
La comprobación de salud del proxy escucha únicamente en el loopback interno
del contenedor, puerto 8082, y no se publica en el host.

No arranques simultáneamente direct mode y Caddy usando el mismo puerto host.
Con el bloque anterior, `web` solo queda en `127.0.0.1:8000` y Caddy es la
entrada LAN en `:8080`; si no cambias `CADDY_HTTP_PORT`, la entrada será
`:8081` según `.env.example`.

La instalación guiada configura estos valores automáticamente:

```bash
bash scripts/install.sh --host reto4v.instituto.lan --port 8443 --tls
```

Con `--tls`, el navegador debe abrir `https://reto4v.instituto.lan:8443` y
confiar la CA interna de Caddy. La comprobación automática del instalador usa
una conexión local con verificación TLS relajada solo para confirmar que el
servicio responde; no cambia la confianza de los clientes.

## 9. Arranque automático con systemd

El servicio `scripts/reto4v-compose.service` ejecuta `docker compose up -d
--no-build`, por lo que no intenta descargar ni reconstruir imágenes durante
el arranque. Ejecuta el instalador dentro de WSL después del primer build:

```bash
cd "$HOME/Reto4V"
sudo ENABLE_BACKUP=1 scripts/install-wsl-systemd.sh
sudo systemctl status reto4v-compose.service --no-pager
sudo systemctl list-timers reto4v-backup.timer
```

El temporizador opcional llama al backup cada noche a las 02:30, con hasta 15
minutos de retraso aleatorio. Asegura que `backups/` está en un
volumen con espacio y que el personal del centro copia/cifra esos archivos.

WSL no necesariamente arranca una distribución por sí solo después de cada
reinicio de Windows. Si el servidor debe servir la plataforma sin una sesión
interactiva, crea en el Programador de tareas una tarea **Al iniciar el
sistema**, con la cuenta de operación aprobada, que ejecute:

```text
C:\Windows\System32\wsl.exe -d Ubuntu-24.04 --exec /bin/true
```

El primer proceso inicia la distribución y systemd activa
`reto4v-compose.service`. Prueba esta ruta después de un reinicio real del
servidor y registra quién puede modificar la tarea.

## 10. Backups y restauración

El backup incluye:

- un dump PostgreSQL en formato custom comprimido;
- el volumen `media` local;
- un manifiesto y `SHA256SUMS`.

Los datos de `staticfiles` no son necesarios para recuperar la instalación: se
regeneran con `collectstatic`. Los secretos, certificados privados y la
configuración `.env` deben respaldarse cifrados mediante el procedimiento del
centro y por separado del dump.

Backup manual:

```bash
cd "$HOME/Reto4V"
bash scripts/backup.sh
sha256sum -c backups/<marca>/SHA256SUMS
```

Puedes elegir otra ubicación protegida sin tocar Compose:

```bash
BACKUP_DIR=/var/backups/reto4v bash scripts/backup.sh
```

Restaurar es una operación destructiva y exige confirmación explícita:

```bash
RESTORE_CONFIRM=YES bash scripts/restore.sh \
  backups/<marca>/postgres.dump.gz \
  backups/<marca>/media.tar.gz
```

El script detiene `web` y Caddy, restaura el dump sin cambiar los propietarios
de PostgreSQL, restaura opcionalmente `media` y vuelve a arrancar `web` y el
proxy si el perfil Caddy estaba activo. Haz una restauración de prueba en una
instalación aislada antes de confiar en un backup para una incidencia real.
Objetivos iniciales orientativos: RPO máximo 24 horas y RTO máximo 4 horas; el
centro debe aprobarlos y probarlos.

Para una recuperación sin Internet guarda, además, una copia cifrada de las
imágenes y del código/configuración aprobados:

```bash
docker image ls
docker save reto4v:local postgres:16-bookworm | gzip > images-reto4v.tar.gz
```

Si usas Caddy, incluye también su imagen y los certificados públicos. Nunca
incluyas claves privadas sin cifrado y control de acceso.

## 11. Operación diaria y actualización

```bash
docker compose --env-file .env ps
docker compose --env-file .env logs --tail=100 web
docker compose --env-file .env logs --tail=100 db
bash scripts/healthcheck.sh
```

Antes de actualizar:

1. Ejecuta y verifica un backup.
2. Prueba el cambio con una copia de la base de datos si afecta al esquema.
3. Con Internet disponible, reconstruye (`docker compose build --pull`).
4. Arranca con `docker compose up -d`; verifica login, editor, entrega y CSV.
5. Comprueba desde un equipo de alumno y desde el profesor.

El Dockerfile instala el `requirements.lock` exportado desde `uv.lock` con
hashes verificados y usa `package-lock.json` para npm. Registra los digests de
las imágenes después de probarlas y conserva la versión aprobada para poder
repetir un despliegue sin Internet.

No ejecutes `down -v`, no borres volúmenes a mano y no sustituyas el Docker
Engine de WSL por Docker Desktop sin revisar la arquitectura y los backups.

## 12. Solución de problemas

### `docker compose` no existe

Instala `docker-compose-plugin` desde el repositorio oficial de Docker y
comprueba `docker compose version`. El binario antiguo `docker-compose` no es
el flujo documentado aquí.

### `web` aparece `unhealthy`

Consulta `docker compose logs web`. Comprueba que `DB_*` coincide con
`POSTGRES_*`, que las migraciones terminaron y que `HEALTHCHECK_PATH` apunta a
una ruta que responde (`/health/` por defecto).

### El navegador del servidor funciona, pero el aula no conecta

En NAT, actualiza `update-wsl-portproxy.ps1` y revisa la regla de Firewall. En
mirrored, comprueba la regla Hyper-V, que la política de WSL permite networking
custom y que el puerto no está ocupado en Windows. Desde otro equipo ejecuta
`Test-NetConnection <servidor> -Port 8080`.

### La IP de WSL cambió

Es normal en NAT. Ejecuta el script PowerShell de portproxy o automatízalo con
el Programador de tareas. No fijes manualmente una IP efímera de WSL.

### `DisallowedHost` o error CSRF

Añade el nombre/IP real a `DJANGO_ALLOWED_HOSTS` y la URL exacta con esquema y
puerto a `DJANGO_CSRF_TRUSTED_ORIGINS`; recrea el contenedor `web` para que lea
el `.env`.

### No hay espacio en WSL

Revisa `docker system df` y el tamaño del VHDX. Elimina solo imágenes/recursos
no utilizados después de verificar los backups; no uses comandos destructivos
sobre el volumen `postgres_data`.

## Fuentes oficiales consultadas

- [Docker Engine: instalar en Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Docker Compose: instalar el plugin Linux](https://docs.docker.com/compose/install/linux/)
- [Microsoft: acceder a aplicaciones de red desde WSL](https://learn.microsoft.com/en-us/windows/wsl/networking)
- [Microsoft: configuración avanzada de WSL (`wsl.conf` y `.wslconfig`)](https://learn.microsoft.com/en-us/windows/wsl/wsl-config)
- [Microsoft: systemd en WSL](https://learn.microsoft.com/en-us/windows/wsl/systemd)
- [Docker: preguntas frecuentes de Docker Desktop en Windows Server](https://docs.docker.com/desktop/troubleshoot-and-support/faqs/windowsfaqs/)
