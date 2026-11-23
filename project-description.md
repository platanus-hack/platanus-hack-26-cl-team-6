SwarmWatch: alucinaciones de un enjambre, detectadas en vivo y a cualquier escala

El problema

Cuando varios agentes de IA trabajan juntos, casi siempre uno solo lee la fuente y los demás confían en él. Si ese agente se equivoca en una cifra o en una cita, los demás la repiten y el error termina en el resultado final.

Cómo funciona

Dos modelos siguen la conversación mientras ocurre. Un modelo de lenguaje (Haiku) lleva un registro de quién dijo qué y de lo que dice realmente la fuente. Solo la fuente cuenta como verdad; lo que afirma un agente queda como "sin verificar". Un modelo de decisión usa ese registro para revisar cada mensaje apenas se publica, con dos preguntas: ¿este mensaje inventa algo? ¿trata como cierto algo que no se verificó? Si la puntuación llega a 0.85, marca el mensaje.

Prueba 1: errores plantados (entrevistas de METR)

Cinco agentes escriben un informe sobre la sección de citas de entrevistas de la evaluación de METR sobre Anthropic. Plantamos errores: cifras cambiadas, citas atribuidas a la persona equivocada, citas con finales inventados y agentes que repiten los errores de otros como si fueran hechos. Como sabemos dónde está cada error, podemos medir cuáles se detectan.

Resultados (umbral 0.85, elegido en la semilla 1 y medido en las semillas 2 y 3):
- Conjunto difícil: 30 de 36 errores detectados (83%), 8 falsas alarmas en 289 mensajes correctos (2.8%).
- Conjunto fácil: 32 de 36 errores detectados (89%), 0 falsas alarmas en 81 mensajes correctos.
- Todos los errores numéricos se detectan. La mayoría de los que se escapan son errores de texto dentro de párrafos con varias afirmaciones.
- Costo: unos $0.03 por cada 100 mensajes, 28 veces más barato que usar Sonnet como juez. El costo por mensaje no crece con el tamaño del enjambre.

Prueba 2: un enjambre real (AI Village)

Corrimos el mismo sistema, sin cambiar nada, sobre 133 agentes de AI Village que conversaron durante 24 horas. Marcó 113 de 3.843 mensajes (2.9%), provenientes de 53 agentes.

En la página

Puedes reproducir las 24 horas del enjambre de AI Village y ver cuándo y a qué agentes marca el modelo, con los puntajes de cada mensaje. Por los términos de uso de AI Village, la página muestra solo nuestros puntajes, no el texto de los mensajes.