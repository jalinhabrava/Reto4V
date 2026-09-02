# Decisiones de Programmy4V 0.2

## Identidad y distribución

El nombre público es **Programmy4V**, por su enfoque práctico en programación
y su vinculación con 4Vientos. Se presenta como una herramienta de
gamificación para aprender programación. El repositorio contiene código y
contenido de ejemplo; nunca datos de una instalación docente.

La URL y la carpeta de clonación pueden seguir mostrando `Reto4V` porque son
identificadores históricos del repositorio. También se mantienen los nombres
internos de Django, Compose, volúmenes, imágenes, rutas y scripts para no
romper instalaciones ya desplegadas; el producto que se muestra al alumnado
y al profesorado se llama Programmy4V.

La publicación del repositorio no publica el servidor del centro: las cuentas,
entregas, notas y copias permanecen en los volúmenes de la instalación LAN.
La licencia de redistribución del código propio queda pendiente de elección
por su titular; no se presume una licencia por el hecho de ser visible.

## Tres itinerarios, una plataforma

- **Web / SMR:** conserva el editor HTML, CSS y JavaScript, la preview y los
  mecanismos de entrega existentes.
- **Bash / ASIR:** incorpora scripts, retos de automatización y seguridad,
  pistas y evaluación estática. El contenido es apoyo transversal a la
  asignatura, no una acreditación automática de sus resultados de aprendizaje.
- **Python / DAM:** introduce Python hasta lectura y escritura de archivos para
  preparar Sistemas de gestión empresarial y el trabajo posterior con Odoo.
  No ejecuta código ni integra el ERP.

Los catálogos base se precargan de forma idempotente al arrancar `web` con
`PRELOAD_CATALOGS=1`. Un alumno recibe el catálogo publicado al elegir su
único ciclo e itinerario en `/admin-ui/users/`; cambiar de ciclo desactiva la
matrícula anterior y conserva su historial.

El lenguaje y los datos de gamificación forman parte de la versión de actividad.
Una versión asignada no cambia de lenguaje, pruebas o recompensa a posteriori.

## Bash no es una terminal remota

El servidor analiza sintaxis y estructura con Tree-sitter sin ejecutar código.
Esto permite trabajar con variables, argumentos, decisiones, bucles, permisos,
copias y verificación sin exponer el host a scripts de alumnos.

Los tests no prueban resultados reales de comandos. Un runner de ejecución
sería otro hito: requeriría una frontera de aislamiento separada, cuotas,
timeouts, red y archivos restringidos, limpieza y una revisión específica.
No se añadirá acceso al socket Docker al contenedor web para conseguirlo.

## Gamificación y calificación

Los XP reflejan el mejor resultado automático de cada reto. Repetir una
entrega idéntica no multiplica la recompensa. Los niveles e insignias se
calculan en el servidor, sin confiar en cifras enviadas por el navegador.

La nota académica, su publicación y su exportación siguen bajo control del
profesor. La interfaz no equipara XP con nota ni muestra clasificaciones
públicas de alumnado.

## Despliegue

La vía prevista es Docker Engine y Compose sobre Linux o WSL2. El instalador
prepara configuración y comprueba requisitos, pero no instala software del
sistema con privilegios sin intervención del operador ni reemplaza una
configuración existente silenciosamente.

El primer build requiere descargar dependencias. Una vez construidas las
imágenes, la aplicación funciona sin servicios externos. HTTP queda limitado
a pruebas; las credenciales y evidencias reales requieren TLS interno y el
procedimiento de protección de datos del centro.

## Diseño

Interfaz sobria, con tipografía local, jerarquía visual, contraste y estados
claros. La gamificación debe motivar sin infantilizar. Se verifica el flujo
real en escritorio y móvil; no se rellenan paneles con estadísticas ficticias.
