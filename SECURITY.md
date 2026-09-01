# Seguridad de Reto4V

Reto4V es una aplicación docente local. Estar en una LAN no sustituye HTTPS,
la autenticación, la separación de permisos o las copias de seguridad.

## Fronteras de confianza

- El código entregado se trata como datos no confiables.
- HTML/CSS/JavaScript se comprueban mediante parsers. La preview web utiliza
  un iframe sin acceso al origen de la aplicación y sin conexiones de red.
- Los scripts Bash se analizan mediante Tree-sitter. No se ejecutan, no
  acceden a archivos y no disponen de una terminal del servidor.
- Los ejercicios Python se analizan con `ast` en memoria. El servidor no
  evalúa ni ejecuta el árbol, no carga los imports escritos por el alumnado y
  no invoca `exec`, `eval`, `importlib`, `subprocess` ni `open` a partir del
  código entregado. Tampoco genera bytecode ni toca el disco.
  La lectura y escritura de archivos solo se reconoce de forma estructural.
- El proceso web no recibe el socket Docker, carpetas del host ni privilegios
  para administrar contenedores.
- Las notas se calculan en el servidor; no se aceptan puntuaciones del cliente.
- Las APIs filtran por usuario y grupos autorizados. Las soluciones y tests
  privados no forman parte del bootstrap del estudiante.

## Qué no garantiza el análisis estático

Reconocer sintaxis, comandos, argumentos o estructuras no demuestra que un
script funcione correctamente, restaure una copia o sea seguro al ejecutarlo.
Puede contener código inalcanzable u operaciones con efectos no deducibles por
un test estructural. Una insignia o 100% de tests no equivale a certificación
de seguridad ni a una calificación oficial del módulo.

En Python, un árbol AST válido solo demuestra que el texto puede analizarse con
la gramática Python del servidor y que contiene las construcciones que declara
el reto. No garantiza que el programa funcione, que los datos tengan el formato
esperado, que un archivo exista o que una integración con Odoo sea correcta.
El análisis aplica límites de tamaño, profundidad y nodos para reducir el
impacto de entradas patológicas, pero no sustituye a la ejecución aislada de
prácticas en una VM de laboratorio. Los ejercicios de archivos no leen ni
escriben el sistema del centro.

Las prácticas de ejecución real deben hacerse en una VM de laboratorio
separada, con datos ficticios y validación docente. No ejecutes entregas en el
servidor de Reto4V ni en el ordenador del profesor.

## Antes del piloto

1. Configurar TLS interno y nombres/orígenes permitidos explícitos.
2. Limitar el firewall a la subred aprobada por el centro.
3. Crear cuentas individuales y proteger la cuenta de administración.
4. Validar backup, restauración, reinicio y funcionamiento sin Internet.
5. Probar carga y consumo de recursos con la clase prevista.
6. Acordar retención, eliminación y acceso a las evidencias académicas.
7. Mantener actualizados dependencias, imágenes y sistema operativo.

Los administradores de base de datos y del host son actores de confianza y
pueden alterar directamente su almacenamiento. La inmutabilidad de la
aplicación no pretende ser una protección contra el administrador del sistema.

## Comunicación de incidencias

No incluyas contraseñas, bases de datos o datos del alumnado en incidencias
públicas. Comunica vulnerabilidades al responsable del despliegue y al
mantenedor por un canal privado acordado; utiliza una reproducción mínima con
datos ficticios. No hay promesa de tiempos de respuesta ni auditoría externa.
