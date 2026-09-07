# Aprender desde cero · HTML/CSS y JavaScript separados

## Qué tomamos de las referencias

Se revisaron el inicio y las primeras lecciones de las cuatro webs el 7 de
septiembre de 2026. Adoptamos su organización didáctica, no sus textos ni una
traducción de sus ejercicios.

- [Learn HTML: primera página](https://www.learn-html.org/en/Hello,_World!)
  empieza explicando qué es HTML y mostrando un documento con `html`,
  `head`, `title` y `body`, antes de pedir completar una página.
  [Elementos básicos](https://www.learn-html.org/en/Basic_Elements) y
  [enlaces](https://www.learn-html.org/en/Links) presentan ejemplos antes de
  su ejercicio. Seguimos la secuencia documento → elementos básicos → enlaces
  → listas → imágenes → estilos → clases y selectores. La plantilla del primer
  reto ya contiene el documento completo; solo se cambia un texto.
  No trasladamos las referencias iniciales a IDE ni Bootstrap. JavaScript
  tiene su propio recorrido.
- [Learn Python: primer programa](https://www.learnpython.org/en/Hello,_World!)
  usa una instrucción de salida como primer ejercicio.
  [Variables y tipos](https://www.learnpython.org/en/Variables_and_Types)
  ilustra cada construcción con código. Separamos los conceptos que allí
  aparecen juntos y evitamos introducir condiciones, interpolación o bucles
  como requisitos antes de explicarlos.
- [Learn Shell: primer script](https://www.learnshell.org/en/Hello,_World!)
  presenta el shell, el script y una salida sencilla.
  [Variables](https://www.learnshell.org/en/Variables) muestra asignación y
  uso. Nuestro primer ejercicio solo modifica un mensaje; formato, variables
  y decisiones llegan de forma gradual, sin exigir una copia de seguridad.
- [Learn JavaScript](https://www.learn-js.org/) separa el inicio del lenguaje
  (mensajes, variables, listas, operaciones, decisiones y funciones) de temas
  avanzados. La adaptación introduce cada construcción con un ejemplo y una
  práctica breve; no presupone que saber HTML equivalga a saber programar.

Las referencias tampoco eliminan todos los saltos de dificultad. Se toma el
patrón explicación → ejemplo → ejercicio, adaptando el tamaño de cada paso
al alumnado de esta plataforma.

## Contrato de cada lección

1. Explicar para qué sirve la idea y qué significan los símbolos nuevos.
2. Mostrar un ejemplo completo y explicar cómo se lee. No esconder esta
   explicación en una pista opcional.
3. Proponer un ejercicio distinto pero análogo, con casi todo preparado.
4. Pedir únicamente lo explicado aquí o en pasos anteriores.
5. Comprobar la modificación pedida: la plantilla sin modificar no debe
   completar el reto. Las soluciones de referencia deben pasar sus tests.
6. Usar el último paso para repasar, no para introducir una API nueva.

## HTML y CSS: aprender juntos, no a la vez desde el primer minuto

El inicio explica página, navegador y documento HTML; después se practican
párrafos, títulos, enlaces, listas e imágenes. A continuación se explica qué
aporta CSS y cómo se lee una regla antes de mostrar `styles.css`. La agrupación
semántica, la caja y la disposición llegan cuando sus elementos básicos ya se
han practicado. El Editor incorpora solo los lenguajes ya introducidos.

JavaScript no se mezcla en ese catálogo: tiene su curso dentro de Web · SMR,
con la misma matrícula. Por defecto se abre cuando todos los retos HTML/CSS
asignados están completados (8/10 automáticos válidos en cada uno). El admin
puede anticipar el acceso individual en «Editar cuenta». Consultar los
catálogos [HTML/CSS](HTML_CSS_TRACK.md) y [JavaScript](JAVASCRIPT_TRACK.md).
Archivos/Odoo en Python y copias complejas en Bash siguen siendo ampliaciones.

## Presentación y límites

Los ejemplos conservan sus líneas y sangría, y HTML se muestra como texto,
no se interpreta dentro de las instrucciones. En Web se distingue Editor de
Resultado. Python y Bash solo tienen comprobación estructural: no se muestra
una salida como si el código se hubiera ejecutado.
Sus paneles muestran los objetivos del paso actual; no recomiendan funciones,
archivos, copias ni opciones de error que el reto todavía no ha presentado.

Las revisiones nuevas crean versiones independientes. El bootstrap archiva asignaciones
anteriores y conserva borradores, entregas y notas originales; no traslada
XP. Los títulos incorporados de revisiones anteriores se actualizan a los nuevos temas, pero
los títulos personalizados del docente se conservan. Una revisión posterior
del centro no se degrada. `Activity.position` fija el orden didáctico dentro
del módulo independientemente del título; el dashboard y el workspace lo
exponen como `position`. Las explicaciones y ejemplos siguen viajando en
`version.instructions`.
