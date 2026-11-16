# Índice de documentación

Documentación técnica del estudio. Cada documento indica qué está **confirmado en runtime**,
qué es **probable** y qué sigue **desconocido**. Los informes históricos (`09-history/`)
reflejan el estado en su fecha y pueden contener afirmaciones luego corregidas.

## 01 — Estado del proyecto
| Documento | Contenido |
|---|---|
| [IMPLEMENTATION_PROGRESS](01-status/IMPLEMENTATION_PROGRESS.md) | matriz de componentes y estado técnico |
| [KNOWN_BLOCKERS](01-status/KNOWN_BLOCKERS.md) | bloqueos, causa raíz y estado de solución |
| [STATUS_AND_REMAINING_WORK](01-status/STATUS_AND_REMAINING_WORK.md) | traspaso: qué funciona y backlog ordenado |
| [FEASIBILITY_UPDATE](01-status/FEASIBILITY_UPDATE.md) | evaluación de viabilidad y límites |

## 02 — Red y protocolo
| Documento | Contenido |
|---|---|
| [PROTOCOL_MAP](02-network/PROTOCOL_MAP.md) | mensajes implementados y su rol |
| [TRANSPORT_WIRE_SPEC](02-network/TRANSPORT_WIRE_SPEC.md) | especificación de tramas, handshake y RC4 |
| [NETWORK_FRAMING_ANALYSIS](02-network/NETWORK_FRAMING_ANALYSIS.md) | análisis del framing observado |
| [NETWORK_DEPENDENCIES](02-network/NETWORK_DEPENDENCIES.md) | dependencias y orden de mensajes |
| [PROTOBUF_ANALYSIS](02-network/PROTOBUF_ANALYSIS.md) | esquema Proto2 y descriptores |
| [CODEC_VALIDATION](02-network/CODEC_VALIDATION.md) | validación de codecs contra el cliente |

## 03 — Cliente (ingeniería inversa)
| Documento | Contenido |
|---|---|
| [REVERSE_ENGINEERING](03-client/REVERSE_ENGINEERING.md) | hallazgos en IL2CPP, Lua y assets |
| [UI_LANGUAGE_DIAGNOSIS](03-client/UI_LANGUAGE_DIAGNOSIS.md) | diagnóstico forense del HUD y del idioma |
| [UI_FIX_REPORT](03-client/UI_FIX_REPORT.md) | intentos de corrección de UI y sus fallos |
| [LUA_FORMAT_ANALYSIS](03-client/LUA_FORMAT_ANALYSIS.md) | formato de chunks LuaJIT |
| [CLIENT_BATTLE_ANALYSIS](03-client/CLIENT_BATTLE_ANALYSIS.md) | por qué el combate es server-authoritative |
| [CONFDATA_CIPHER_ANALYSIS](03-client/CONFDATA_CIPHER_ANALYSIS.md) | cifrado de tablas maestras |

## 04 — Mundo y runtime
| Documento | Contenido |
|---|---|
| [SCENE_MESSAGE_MAP](04-world/SCENE_MESSAGE_MAP.md) | mensajes de escena |
| [SCENE_POC_REPORT](04-world/SCENE_POC_REPORT.md) | primera carga de Shibuya |
| [STARTUP_GATES_ANALYSIS](04-world/STARTUP_GATES_ANALYSIS.md) | gates de arranque |
| [STARTUP_RUNTIME_TEST](04-world/STARTUP_RUNTIME_TEST.md) | pruebas de arranque |
| [RUNTIME_TEST_REPORT_2026_11_15](04-world/RUNTIME_TEST_REPORT_2026_11_15.md) | prueba integral de runtime |

## 09 — Histórico
Informes de sesión, experimentos y planes fechados. Útiles para trazabilidad; no usar como
estado actual sin contrastar con `01-status/`.

## Material no distribuido

`msg.proto`, catálogos de mensajes, `assetMapName.txt`, `I18NAssetMap.xml`, bundles, bytecode
Lua y tablas ConfData **no se incluyen** en este repositorio por derechos de autor. Se
regeneran localmente desde una copia legal del cliente.
