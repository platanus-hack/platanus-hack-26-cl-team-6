El escenario: entrevistas de METR

Usamos las notas reales de las entrevistas sobre aceleración (Investigadores A a L). Un enjambre de 4 agentes (investigador, redactor, revisor, sintetizador) responde: ¿quién dijo que Claude le dio 2x o más de productividad?

Plantamos errores. El más importante: el Investigador B dijo 3x, pero un agente escribe 1.2x. También plantamos citas falsas, cifras cambiadas y cifras inventadas. Luego comparamos tres casos: sin registro, con el registro y con un juez LLM.

Qué hay en el proyecto
Experimento	Archivo	Qué muestra
1. Lavado de afirmaciones	swarm.py	Cuántos errores plantados llegan al informe final, con y sin registro, y contra un juez LLM
2. Degradación	degrade.py	Cómo se pierde información al pasar por 4, 8, 16 y 32 agentes
3. Alarma de aceleración	meme.py, monitor.py	200 agentes votan si la IA acelera la investigación en IA más de 2x. Un meme falso ("B dijo solo 1.2x") puede apagar la alarma. El monitor encuentra al paciente cero.


Resultados Reales (Claude Haiku 4.5, 2 preguntas × 5 corridas)

Errores plantados que llegaron a la respuesta: 17 de 35 sin registro y 0 de 35 con registro.
Citas falsas: el juez LLM se dejó engañar en 3 de 5. El registro atrapó las 5 de 5.
Falsas alarmas: 1 de 109 del registro y 10 de 109 del juez.

Origen: el registro encontró al agente que inventó la cifra en 17 de 17 casos.

La muestra es chica. Quedan 20 marcas sin etiquetar que hay que revisar a mano.

