# Análisis Técnico de Descriptores Protobuf (`PROTOBUF_ANALYSIS.md`)

## 1. Verificación del Contenedor `allMsgPb.bytes`

- **Ruta analizada (solo lectura):** `D:\secret\P5X\client\OuterPackage\Lua\Windows\allMsgPb.bytes`
- **Tamaño exacto:** `223.978 bytes`
- **Hash SHA-256 original:** `2D4AEE2C04A861414317F7403D933793D4CB932F393F53D2229B8DA6119F3700`
- **Resultado de validación estructural:**
  - `allMsgPb.bytes` es un **`google.protobuf.FileDescriptorSet` 100% válido y no cifrado**, sin cabeceras propietarias añadidas ni bytes sobrantes al final del archivo.
  - Contiene exactamente **1 `FileDescriptorProto`** (`tag 0x0A`, longitud varint `223.974` bytes + 4 bytes de cabecera = `223.978` bytes).

---

## 2. Propiedades Técnicas del `FileDescriptorProto`

| Campo `FileDescriptorProto` | Número de Tag | Valor Decodificado | Significado Técnico |
|---|---|---|---|
| `name` | `1` (`string`) | `"msg.proto"` | Nombre original del archivo fuente compilado por el desarrollador. |
| `package` | `2` (`string`) | *(Ausente / vacío)* | Todos los mensajes y enumeraciones residen en el espacio de nombres raíz (`.CSLogin`, `.DHuman`, etc.). |
| `dependency` | `3` (`string`) | `["options.proto"]` | Importa un único archivo externo que define la extensión `MessageOptions` para los identificadores de paquete (`msgid`). |
| `message_type` | `4` (`DescriptorProto`) | **2.663 mensajes** | Incluye la totalidad de paquetes cliente-servidor y estructuras de datos auxiliares. |
| `enum_type` | `5` (`EnumDescriptorProto`) | **37 enumeraciones** | Constantes simbólicas compartidas entre cliente y servidor. |
| `options` | `8` (`FileOptions`) | `optimize_for = CODE_SIZE` (`field 9 = 2`) | Opción de compilación estándar de Protobuf (`OptimizeMode.CODE_SIZE`). |
| `syntax` | `12` (`string`) | *(Implícito: `"proto2"`)* | Usa semántica **Proto2** con etiquetas explícitas `optional` (`1`), `required` (`2`) y `repeated` (`3`). |

---

## 3. Hallazgo Crítico: El Mapeo `MsgID` está Embebido en `MessageOptions`

Uno de los mayores riesgos identificados antes de este experimento era desconocer la correspondencia entre los nombres de mensajes (`CSLogin`, `CSSceneEnter`, `CSRoundSkillList`) y los números de operación (`Opcode` / `MsgID`) enviados por la red.

El análisis de los descriptores demostró que **el 100% del mapeo `MsgID` está almacenado dentro del propio `allMsgPb.bytes`** mediante una extensión personalizada de `google.protobuf.MessageOptions` (definida en `options.proto` con el número de campo **`54321`**):

```protobuf
syntax = "proto2";
import "google/protobuf/descriptor.proto";

extend google.protobuf.MessageOptions {
  optional int32 msgid = 54321;
}
```

### Clasificación exacta de los 2.663 mensajes

1. **Mensajes de red con `option (msgid)` (2.195 mensajes — 82,43%):**
   - **`CS*` (Client $\rightarrow$ Server):** **1.070 mensajes.** Todos tienen asignado un `msgid` único en la extensión `54321`.
   - **`SC*` (Server $\rightarrow$ Client):** **1.125 mensajes.** Todos tienen asignado un `msgid` único en la extensión `54321`.
   - **Colisiones o duplicados:** **0.** Ningún `msgid` se repite en todo el esquema.
   - **Mensajes `CS*`/`SC*` huérfanos (sin `msgid`):** **0.**
2. **Estructuras de datos sin `option (msgid)` (468 mensajes — 17,57%):**
   - **432 estructuras con prefijo `D*`** (`DHuman`, `DCharacter`, `DSceneObject`, `DUnitProp`, `DBattleUnitObjectData`, `DVector3`, etc.) y **36 estructuras de subsistemas específicos** (`Monopoly*`, `Activity*`, `Calc*`, etc.) que nunca se envían solas por el socket, sino anidadas como campos (`type = 11 / TYPE_MESSAGE`) dentro de mensajes `CS*` y `SC*`.

---

## 4. Verificación de Equivalencia e Información No Recuperable

### 4.1 Prueba matemática de equivalencia (*Round-Trip Bit-Exact*)
Para cumplir la condición de verificar que los archivos [msg.proto](file:///D:/secret/docs/msg.proto) y [options.proto](file:///D:/secret/docs/options.proto) reconstruidos son 100% equivalentes a `allMsgPb.bytes`:
1. Se parseó el binario original hacia un árbol sintáctico abstracto (AST) en memoria con las 37 enumeraciones y los 2.663 mensajes.
2. Se verificó qué campos de `DescriptorProto`, `FieldDescriptorProto` y `EnumDescriptorProto` están presentes en el archivo original:
   - `DescriptorProto`: exclusivamente `1` (`name`), `2` (`field`) y `7` (`options`). No existen tipos anidados (`nested_type`), `oneof_decl`, rangos de extensión ni campos reservados.
   - `FieldDescriptorProto`: exclusivamente `1` (`name`), `3` (`number`), `4` (`label`), `5` (`type`) y `6` (`type_name`). No existen valores por defecto explícitos (`default_value`, tag 7) ni `FieldOptions` (tag 8).
3. Al volver a serializar el AST en memoria al formato binario `FileDescriptorSet`, se obtuvo un flujo de **223.978 bytes con hash SHA-256 `2D4AEE2C04A861414317F7403D933793D4CB932F393F53D2229B8DA6119F3700`**, idéntico bit a bit al archivo original.

### 4.2 Información no recuperable desde `allMsgPb.bytes` (Limitaciones)
Aunque el esquema de datos y los `MsgID` están 100% completos, un `FileDescriptorSet` compilado sin `SourceCodeInfo` (campo 9 de `FileDescriptorProto`, que el compilador `protoc` omite por defecto) **no conserva**:
1. **Comentarios del código fuente original (`//` o `/* */`):** Los nombres de campos en `DUnitProp` usan abreviaturas en pinyin (ej. `LL` = Fuerza, `ML` = Magia, `NL` = Aguante, `SD` = Agilidad, `YQ` = Suerte, `GJ` = Ataque, `FY` = Defensa, `BJ` = Probabilidad Crítica, `BS` = Daño Crítico) cuyos comentarios explicativos originales no se incluyen en el binario compilado.
2. **Archivo `options.proto` por separado:** En `allMsgPb.bytes` aparece declarado como dependencia (`dependency: "options.proto"`) y su uso se observa en `MessageOptions` (campo `54321`, tipo `varint`). El nombre simbólico de la extensión (`msgid`) es una reconstrucción semántica equivalente, ya que en el binario solo viaja el número de etiqueta `54321`.
3. **Encapsulado de red (Framing TCP):** `allMsgPb.bytes` define cómo se serializa el *cuerpo* (`payload`) de cada mensaje y cuál es su número `msgid`, pero **no define cómo se empaquetan la longitud y el `msgid` en la cabecera del socket TCP** (puertos `10403` y `10404`), ni si el socket aplica cifrado o compresión sobre el paquete.
