# Seguridad de Reto4V

Reto4V es una aplicación docente local. Estar en una LAN no sustituye HTTPS,
la autenticación, la separación de permisos o las copias de seguridad.

## Fronteras de confianza

- El código entregado se trata como datos no confiables.
- HTML/CSS/JavaScript se comprueban mediante parsers. La preview web utiliza
  un iframe sin acceso al origen de la aplicación y sin conexiones de red.
- Los scripts Bash se analizan mediante Tree-sitter. No se ejecutan, no
  acceden a archivos y no disponen de una terminal del servidor.
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
