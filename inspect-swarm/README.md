Claim Ledger


Cuando agentes de IA se pasan información, una mentira llega al informe final sin que nadie la vea. Nosotros la atrapamos y decimos qué agente la dijo.

El problema
4 agentes de IA (investigador → redactor → revisor → sintetizador) resumen entrevistas reales de METR sobre cuánto acelera Claude la investigación. Un agente cambia "el investigador B dijo 3x" por "1,2x". Nadie lo nota.

La solución
Un registro de afirmaciones: código, no otra IA. Busca cada cifra y cada cita en la fuente original. Si no está, la borra y señala al agente culpable.

Resultados (Claude Haiku, corridas reales)
Sin registro	Con registro
Falsedades que llegan al informe	61% (46/75)	0%
Falsas alarmas sobre datos verdaderos	—	2% (7/326)
Agente culpable identificado	—	100% (46/46)
Lo que no atrapa
Mentiras sin números (por ejemplo, cambiar "Sí" por "No") y cifras reales usadas fuera de contexto.

Probarlo
