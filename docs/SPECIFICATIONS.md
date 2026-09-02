# Especificación de producto · Programmy4V

## Objetivo

Programmy4V es una herramienta de gamificación para aprender programación en la LAN del centro.
Tres recorridos comparten cuentas, grupos, editor, entregas y revisión docente:
HTML/CSS/JavaScript para SMR, Bash para Seguridad de 2.º ASIR y Python
introductorio para Sistemas de gestión empresarial de 2.º DAM.

El repositorio público contiene el software y actividades formativas de
ejemplo. Cuentas, borradores, entregas, notas y copias se almacenan únicamente
en la instalación del centro. No se requiere OAuth, IA ni un servicio SaaS.

## Alcance implementado de la versión 0.3

- Cuentas locales con roles administrador, profesor y alumno; creación,
  edición, desactivación y restablecimiento de contraseña. No hay registro
  público. La desactivación conserva las evidencias.
- Grupos, matrículas y relaciones docentes gestionados en la administración
  local. Cada alumno puede tener un único ciclo e itinerario activo; al crear o
  editar la cuenta, el administrador selecciona el campo **Ciclo e itinerario**
  y la matrícula se crea o cambia de forma atómica. Cada alumno solo recibe el
  catálogo publicado de su grupo.
- Actividades versionadas, asignaciones, plazos y política de intentos.
  Los cambios de un reto ya asignado necesitan una nueva versión.
- Editor web con HTML, CSS, JavaScript y preview aislada en el navegador.
- Editor Bash de un solo `script.sh`, explicación, objetivos y pistas.
  Análisis sintáctico y estructural en el servidor, **sin ejecución**.
- Editor Python de un solo `main.py`, explicación, objetivos y pistas. El
  corrector analiza un AST en memoria, **sin ejecución**, sin importar módulos,
  sin abrir archivos y sin acceder al sistema del centro.
- Borradores con control de revisión, entregas inmutables y pruebas públicas
  de práctica separadas de la evaluación de una entrega.
- XP según el mejor resultado automático por asignación; niveles e insignias
  calculados en el servidor, sin multiplicar puntos por repetir entregas.
- Revisión docente, publicación de calificaciones y exportaciones CSV.
  Los XP no se usan como nota académica ni como ranking público.
- Docker Compose con PostgreSQL persistente; instalador para Linux/WSL2,
  HTTPS interno opcional, comprobación de salud y backup/restauración.
- Bootstrap idempotente de catálogo al iniciar `web` (`PRELOAD_CATALOGS=1`),
  sin crear alumnos ni contraseñas de demostración. La administración local
  ofrece la vista **Aulas e itinerarios** para comprobar los grupos y sus
  retos antes de crear las cuentas.

La edición avanzada de cursos, grupos y actividades usa por ahora la
administración de Django; usuarios, matrículas y enlaces grupo-reto quedan allí
en modo de consulta para no saltarse los servicios académicos. El panel local
de **Aulas e itinerarios** sirve para consultar el catálogo y la gestión
cotidiana de matrículas, mientras que los grupos adicionales se preparan con
los comandos `seed_*`. No se presenta como un constructor visual de contenidos.

## Contenido y currículo

El catálogo inicial incluye **doce retos web**, **doce retos de Bash** y
**doce retos de Python** (36 retos publicados en total). Se cargan en los
grupos base Web · SMR, Bash · ASIR y Python · DAM durante el bootstrap. No
representa la programación completa de ninguno de los módulos.

En SMR se mantiene la referencia navarra de `0228 · Aplicaciones web`, con
trazabilidad curricular por versión. El banco completo debe desarrollarse
conforme a la programación didáctica y al
[Decreto Foral 49/2010 consolidado, currículo navarro de SMR](https://www.lexnavarra.navarra.es/detalle.asp?r=9129),
con sus modificaciones vigentes.

Bash apoya de forma transversal `0378 · Seguridad y alta disponibilidad`:
variables, condiciones, bucles, funciones, argumentos, códigos de salida,
filtros, permisos y planificación de copias. No se asignan RA/CE artificiales.
Las referencias navarras y el alcance están en [BASH_TRACK.md](BASH_TRACK.md).
Saber escribir una estructura no demuestra haber restaurado una copia real:
esa evidencia debe recogerse en la VM de prácticas y con revisión docente.

Python ofrece una introducción progresiva hasta lectura y escritura de
archivos: sintaxis, variables, control de flujo, colecciones, funciones,
errores y excepciones, módulos, rutas y operaciones estructurales con archivos.
Los ejercicios usan contextos de datos empresariales para preparar el trabajo
posterior con Odoo, pero no incluyen el framework, el ORM ni una conexión a un
servidor Odoo. El [Decreto Foral 110/2024](https://www.educacion.navarra.es/documents/27590/558252/DF%2B110_2024%2Bmodificacion%2BGS.pdf/a649cf9e-7adf-3c5d-c5ac-eaa602a553a5?version=1.0)
sitúa `0491 · Sistemas de gestión empresarial` en 160 horas, 5 horas
semanales y 2.º curso, y describe en su RA5 el desarrollo de componentes para
un ERP-CRM mediante el lenguaje incorporado, incluidos elementos de
manipulación y extracción de información. Este itinerario es un alineamiento y
una preparación parcial: no cubre ni acredita el RA5, sus criterios de
evaluación ni la instalación, configuración, verificación o desarrollo real en
Odoo. La referencia de que los objetos de negocio de Odoo se modelan con
clases Python está en su [tutorial oficial del framework de servidor](https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101.html).
El detalle del catálogo y sus límites está en [PYTHON_TRACK.md](PYTHON_TRACK.md).

## Requisitos de experiencia

Interfaz en español, con jerarquía tipográfica, contraste, navegación por
teclado y distribución adaptable a escritorio y móvil. La gamificación es
sobria: progreso personal, recompensas legibles y feedback útil. No se
rellenan paneles de producción con estadísticas ficticias ni se simula una
terminal que no existe.

El estudiante debe poder recargar un reto y recuperar el borrador guardado,
volver al resumen y ver el progreso actualizado. Un conflicto de edición
debe ofrecer una decisión explícita, nunca sobrescribir silenciosamente.
Al crear la cuenta, el administrador elige un único ciclo e itinerario; en el
primer acceso el alumno debe encontrar su primer reto publicado ya disponible.
Una cuenta sin matrícula muestra una orientación clara para solicitar la
asignación, no un catálogo inventado.

## Requisitos del despliegue

El operador prepara Ubuntu en WSL2 con Docker Engine y Compose v2. Después,
clona el repositorio en el sistema de archivos Linux y ejecuta el instalador.
La primera construcción necesita Internet; la aplicación construida no debe
solicitar recursos externos durante la clase.

La instalación debe conservar configuración, secretos, usuarios y volúmenes
al repetirse. La restauración es una operación distinta y requiere
confirmación. Antes de usar datos reales se exige TLS, firewall del aula,
backup comprobado y política de retención del centro. El arranque automático
del catálogo se puede desactivar con `PRELOAD_CATALOGS=0`; al actualizar con
`git pull`, reconstruir y levantar la imagen vuelve a ejecutarse de forma
idempotente cuando permanece en `1`.

## Criterios de aceptación del piloto en el centro

1. Acceso desde un equipo del aula con cuentas ficticias de cada rol.
2. Guardado, recarga y entrega de un reto web, otro de Bash y otro de Python.
3. Repetir una entrega no aumenta artificialmente los XP.
4. Un alumno no accede a evidencias ajenas ni a tests privados.
5. Un profesor revisa y exporta solo los grupos autorizados.
6. Reiniciar Windows/WSL recupera la aplicación y los datos.
7. Un backup restaura correctamente en una instalación de prueba separada.
8. La aplicación funciona con Internet desconectado tras preparar imágenes.
9. Se comprueba carga con el número real de equipos del aula.
10. Los certificados son confiables en los equipos, sin omitir advertencias.

Las pruebas de desarrollo y CI no sustituyen estas comprobaciones en el
servidor y la red concretos del instituto.

## Siguientes incrementos, fuera de esta versión

- Ampliar el catálogo web y validar una matriz RA/CE con el profesor.
- Pilotar un reto Python con datos ficticios de una entidad empresarial y
  recoger una rúbrica docente separada de la puntuación AST; después ampliar
  progresivamente hacia lectura/escritura de formatos delimitados y JSON sin
  convertir el corrector en un ejecutor.
- Diseñar, en colaboración con el profesorado de 0491, una secuencia posterior
  de instalación, configuración, importación, integración, extracción e
  informes de un ERP-CRM. La integración con Odoo se probará en un entorno
  separado y no se infiere desde los retos Python de esta plataforma.
- Constructor visual de actividades y rúbricas sobre el modelo versionado.
- Importación masiva de usuarios/grupos con validación y vista previa.
- Pruebas funcionales de Bash en un entorno aislado independiente, solo
  después de diseñar cuotas, red, archivos, limpieza y límites de ejecución.
  Nunca conectar el socket Docker al proceso web para conseguirlo.

## Contratos para continuar con Codex

Consultar [AGENTS.md](../AGENTS.md), [BACKEND_API.md](BACKEND_API.md),
[el contrato del frontend](../frontend/API_CONTRACT.md),
[las decisiones](DECISIONS.md) y [SECURITY.md](../SECURITY.md).
Toda ampliación debe mantener la separación de permisos, el carácter
inmutable de las entregas y la distinción entre gamificación y calificación.
