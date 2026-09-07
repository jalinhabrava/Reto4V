# Aprender desde cero · HTML/CSS y JavaScript separados

## Qué tomamos de las referencias

Se revisaron el inicio y las primeras lecciones de las tres webs el 7 de
septiembre de 2026. Adoptamos su organización didáctica, no sus textos ni una
traducción de sus ejercicios.

- [Learn HTML: primera página](https://www.learn-html.org/en/Hello,_World!)
  explica las etiquetas y enseña código antes de pedir completar una página.
  [Elementos básicos](https://www.learn-html.org/en/Basic_Elements) y
  [enlaces](https://www.learn-html.org/en/Links) presentan ejemplos antes de
  su ejercicio. Nuestra adaptación divide aún más el inicio: primero cambiar
  el contenido de un párrafo, después escribir etiquetas. No trasladamos las
  referencias iniciales a IDE ni Bootstrap. CSS se introduce después de los
  primeros conceptos HTML y se intercala con ellos; JavaScript tiene su propio recorrido.
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

El inicio sigue siendo página y navegador, párrafos y títulos. Después se
explica qué aporta CSS y cómo se lee una regla antes de mostrar `styles.css`.
Se alternan nuevos elementos HTML con selectores, clases, colores, espacios y
disposición. El archivo inicial incorpora solo los lenguajes ya introducidos.

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

Las revisiones nuevas crean versiones independientes. El bootstrap archiva asignaciones
anteriores y conserva borradores, entregas y notas originales; no traslada
XP. Los títulos incorporados de v2 se actualizan a los nuevos temas, pero
los títulos personalizados del docente se conservan. Una revisión posterior
del centro no se degrada. No hace falta modificar el esquema de la API:
las explicaciones y ejemplos viajan en `version.instructions`.
