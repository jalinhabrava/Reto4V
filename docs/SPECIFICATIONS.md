# Especificación de producto · Reto4V

## Objetivo

Herramienta de gamificación para aprender programación en la LAN del centro.
Dos recorridos comparten cuentas, grupos, editor, entregas y revisión docente:
HTML/CSS/JavaScript para SMR y Bash para Seguridad de 2.º ASIR.

El repositorio público contiene el software y actividades formativas de
ejemplo. Cuentas, borradores, entregas, notas y copias se almacenan únicamente
en la instalación del centro. No se requiere OAuth, IA ni un servicio SaaS.

## Alcance implementado de la versión 0.2

- Cuentas locales con roles administrador, profesor y alumno; creación,
  edición, desactivación y restablecimiento de contraseña. No hay registro
  público. La desactivación conserva las evidencias.
- Grupos, matrículas y relaciones docentes gestionados en la administración
  local. Cada alumno y profesor accede a los grupos que tiene autorizados.
- Actividades versionadas, asignaciones, plazos y política de intentos.
  Los cambios de un reto ya asignado necesitan una nueva versión.
- Editor web con HTML, CSS, JavaScript y preview aislada en el navegador.
- Editor Bash de un solo `script.sh`, explicación, objetivos y pistas.
  Análisis sintáctico y estructural en el servidor, **sin ejecución**.
- Borradores con control de revisión, entregas inmutables y pruebas públicas
  de práctica separadas de la evaluación de una entrega.
- XP según el mejor resultado automático por asignación; niveles e insignias
  calculados en el servidor, sin multiplicar puntos por repetir entregas.
- Revisión docente, publicación de calificaciones y exportaciones CSV.
  Los XP no se usan como nota académica ni como ranking público.
- Docker Compose con PostgreSQL persistente; instalador para Linux/WSL2,
  HTTPS interno opcional, comprobación de salud y backup/restauración.

La edición de cursos, grupos y actividades usa por ahora la administración
de Django; no se presenta como un constructor visual de contenidos.

## Contenido y currículo

El catálogo inicial incluye **una actividad introductoria web** y **doce
retos de Bash**. No representa la programación completa de ninguno de los
dos módulos.

En SMR se mantiene la referencia navarra de `0228 · Aplicaciones web`, con
trazabilidad curricular por versión. El banco completo debe desarrollarse
conforme a la programación didáctica y al
[Decreto Foral 109/2024, modificación de grado medio](https://www.educacion.navarra.es/documents/27590/558252/DF%2B109_2024%2Bmodificacion%2BGM.pdf/6641c899-fd0f-89e3-83f4-aa30c8224707).

Bash apoya de forma transversal `0378 · Seguridad y alta disponibilidad`:
variables, condiciones, bucles, funciones, argumentos, códigos de salida,
filtros, permisos y planificación de copias. No se asignan RA/CE artificiales.
Las referencias navarras y el alcance están en [BASH_TRACK.md](BASH_TRACK.md).
Saber escribir una estructura no demuestra haber restaurado una copia real:
esa evidencia debe recogerse en la VM de prácticas y con revisión docente.

## Requisitos de experiencia

Interfaz en español, con jerarquía tipográfica, contraste, navegación por
teclado y distribución adaptable a escritorio y móvil. La gamificación es
sobria: progreso personal, recompensas legibles y feedback útil. No se
rellenan paneles de producción con estadísticas ficticias ni se simula una
terminal que no existe.

El estudiante debe poder recargar un reto y recuperar el borrador guardado,
volver al resumen y ver el progreso actualizado. Un conflicto de edición
debe ofrecer una decisión explícita, nunca sobrescribir silenciosamente.

## Requisitos del despliegue

El operador prepara Ubuntu en WSL2 con Docker Engine y Compose v2. Después,
clona el repositorio en el sistema de archivos Linux y ejecuta el instalador.
La primera construcción necesita Internet; la aplicación construida no debe
solicitar recursos externos durante la clase.

La instalación debe conservar configuración, secretos, usuarios y volúmenes
al repetirse. La restauración es una operación distinta y requiere
confirmación. Antes de usar datos reales se exige TLS, firewall del aula,
backup comprobado y política de retención del centro.

## Criterios de aceptación del piloto en el centro

1. Acceso desde un equipo del aula con cuentas ficticias de cada rol.
2. Guardado, recarga y entrega de un reto web y otro de Bash.
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
