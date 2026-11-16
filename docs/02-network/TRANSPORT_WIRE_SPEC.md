# Especificación de Cable de `Utils.TcpClient` y `Utils.RC4` (Experimento 3 — Vía A)

**Fecha de ejecución:** 2026-11-14  
**Objeto de análisis:** `D:\secret\P5X\client\pc\GameAssembly.dll` + `D:\secret\P5X\client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat`  
**Método:** Análisis estático offline de solo lectura mediante correlación de tokens de `global-metadata.dat` (IL2CPP v31) con `Il2CppCodeGenModule` de `Assembly-CSharp.dll` y desensamblado `x86_64` instrucción por instrucción con `capstone` (Python).

---

## 1. Resumen Ejecutivo y Contraste con Hipótesis Previas (Experimento 2)

El desensamblado instrucción por instrucción de `Utils.TcpClient` (`TypeDef[1823]`) y `Utils.RC4` (`TypeDef[1830]`) resuelve el 100% de las incógnitas de transporte planteadas tras el Experimento 2 y corrige dos supuestos previos de `NETWORK_FRAMING_ANALYSIS.md`:

1. **Orden, Endianness y Semántica de la Cabecera (`HEAD_SIZE = 8`) — `CONFIRMADO`:**
   - **Bytes `0..3` (`totalLen`):** Entero de 32 bits con signo en orden de red **Big-Endian** (`int32 BE`). Representa la **longitud total de la trama en bytes incluyendo la propia cabecera** (`totalLen = 8 + N` para mensajes normales con `N` bytes de payload Protobuf; en recepción `ReceivePayload` calcula `lastMsgLength = rawLen - 4`, que equivale a `4 + N`).
   - **Bytes `4..7` (`msgId`):** Entero de 32 bits con signo en orden de red **Big-Endian** (`int32 BE`). Contiene el identificador numérico del mensaje (`MsgID` del catálogo de 2.195 mensajes).
   - **Bytes `8..8+N-1` (`payload`):** Bytes serializados de `ProtoBuf` (`N = totalLen - 8`).

2. **Handshake Inicial de Clave RC4 (`_readKey`) y Asimetría Direccional de Cifrado — `CONFIRMADO`:**
   - **Handshake inicial (`_readKey == false` al conectar):** Al establecerse la conexión TCP (`Connect`, `RVA 0xCEC710`), `_readKey` (`this+0x70`) y `_ready` (`this+0x18`) se inicializan en `0` (`false`). El cliente **no marca la conexión como lista (`BeReady == true`) ni permite enviar paquetes** hasta recibir la **primera trama del servidor** (`ReceivePayload`, rama `_readKey == false` en `VA 0x180CEDBDD..0x180CEDD12`).
   - **Estructura de la Trama 0 (Server $\rightarrow$ Client Key Frame):** Consta de `[0..3: int32 BE rawLen = 4 + keyLen]` seguido de `[4..4+keyLen-1: byte[keyLen] keyBytes]` (**sin campo `msgId`**). El cliente lee `keyBytes` (`lastMsgLength = rawLen - 4` bytes), instancia `this._rc4 = new Utils.RC4(keyBytes)` y activa `this._readKey = true` (`1`).
   - **Cifrado RC4 exclusivamente en dirección Cliente $\rightarrow$ Servidor y desde el byte 4 (`[4..totalLen)`) — `CONFIRMADO`:**
     - En **Cliente $\rightarrow$ Servidor** (`Send_begin` en `VA 0x180CEE0DA..0x180CEE10A` y `Send(msg_base)` en `VA 0x180CEE686..0x180CEE6A6`), si `this._rc4 != null`, el cliente invoca `this._rc4.Crypt(this._sendBuffer, 4, totalLen)`. Por tanto:
       - Los **bytes `0..3` (`totalLen`) viajan SIEMPRE EN TEXTO PLANO**.
       - Los **bytes `4..7` (`msgId`) y `8..totalLen-1` (`payload`) se cifran juntos de forma continua** con el flujo RC4 (`start = 4, end = totalLen`).
     - En **Servidor $\rightarrow$ Cliente** (`ReceivePayload` en `VA 0x180CEDBE6..0x180CEDCB9` y `DealMessage` en `VA 0x180CED260..0x180CED371`), **NO se invoca `Utils.RC4::Crypt` en ningún punto**. Todas las tramas Servidor $\rightarrow$ Cliente posteriores al handshake viajan en **texto plano** (`[totalLen BE][msgId BE][payload]`).

---

## 2. Diagramas de Trama Byte a Byte

### 2.1. Trama 0: Handshake Inicial de Clave RC4 (Servidor $\rightarrow$ Cliente, cuando `_readKey == false`)

Enviada por el servidor inmediatamente después de aceptar el socket TCP. Sin esta trama, `Utils.TcpClient.BeReady` (`this+0x18`) permanece en `false` (`VA 0x180CECA55..0x180CECA87`).

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                rawLen = 4 + K (int32 Big-Endian)              |  Bytes 0..3   [TEXTO PLANO]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                   keyBytes (K bytes, K >= 1)                  +  Bytes 4..3+K [TEXTO PLANO]
|             (Semilla para new Utils.RC4(keyBytes))            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

* **`rawLen` (`Bytes 0..3`):** `int32` Big-Endian. `ReceivePayload` calcula `this.lastMsgLength = rawLen - 4 = K` (`VA 0x180CEDB7D: lea eax, [r11 - 4]`).
* **`keyBytes` (`Bytes 4..3+K`):** Arreglo de `K` bytes leído con `binaryReader.ReadBytes(this.lastMsgLength)` (`VA 0x180CEDCC7..0x180CEDCD8`) y pasado a `Utils.RC4::.ctor(byte[] key)` (`VA 0x180CEDCF5: call 0x180d01b90`).
* **Restricción de longitud `K`:** `Utils.RC4::.ctor` admite cualquier `K >= 1` (ejecuta `i % key.Length` mediante `idiv esi` en `VA 0x180D01C35` para inicializar el vector `S[256]`). Si el servidor emulado envía por ejemplo una clave de 1 a 256 bytes, el cliente inicializa `this._rc4` y establece `this._readKey = 1` (`VA 0x180CEDD0F`).

---

### 2.2. Trama Normal Cliente $\rightarrow$ Servidor (`Send_begin` / `Send(msg_base)`, cuando `_readKey == true`)

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|               totalLen = 8 + N (int32 Big-Endian)             |  Bytes 0..3     [TEXTO PLANO - NO CIFRADO]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+  --- Inicio de RC4.Crypt(buf, start=4, end=8+N) ---
|                    msgId (int32 Big-Endian)                   |  Bytes 4..7     [CIFRADO CON RC4]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+               Protobuf Payload (N bytes, N >= 0)              +  Bytes 8..7+N   [CIFRADO CON RC4]
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+  --- Fin de RC4.Crypt(buf, start=4, end=8+N) ---
```

* **`totalLen` (`Bytes 0..3`, texto plano):** `int32` Big-Endian igual a `8 + N` (calculado desde `_sendStream.Position` tras escribir el payload a partir del offset `8`; `VA 0x180CEDFD6..0x180CEE040`).
* **`msgId` (`Bytes 4..7`, cifrado con RC4):** `int32` Big-Endian escrito en `_sendHeaderBuffer[4..7]` (`VA 0x180CEE042..0x180CEE080`), copiado a `_sendBuffer[4..7]` y luego cifrado in-place por `_rc4.Crypt(_sendBuffer, 4, totalLen)` (`VA 0x180CEE0F1..0x180CEE10A`).
* **`payload` (`Bytes 8..7+N`, cifrado con RC4):** Bytes serializados del mensaje Protobuf, escritos en `_sendBuffer[8..8+N-1]` y cifrados en la misma llamada continua `_rc4.Crypt(_sendBuffer, 4, totalLen)`.
* **Estado del flujo RC4:** La instancia `this._rc4` mantiene únicamente el arreglo `S[256]` (`byte[]` en `this._rc4+0x10`), pero **ojo al detalle crítico de `Utils.RC4::Crypt`** (ver Sección 4.1): en `Utils.RC4::Crypt` (`VA 0x180D01A50`), los índices `i` (`r10d`) y `j` (`r11d`) se inicializan a `0` al comienzo de cada llamada (`xor r10d, r10d; xor r11d, r11d` en `VA 0x180D01A5A..0x180D01A60`), mientras que la permutación del arreglo `this.S[256]` (`[rcx + 0x10]`) **sí muta y persiste entre llamadas** (`mov byte ptr [rax + rdx + 0x20], r8b` en `VA 0x180D01AC6..0x180D01AD7`).

---

### 2.3. Trama Normal Servidor $\rightarrow$ Cliente (`ReceivePayload`, cuando `_readKey == true`)

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|               rawLen = 8 + N (int32 Big-Endian)               |  Bytes 0..3     [TEXTO PLANO]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    msgId (int32 Big-Endian)                   |  Bytes 4..7     [TEXTO PLANO]
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+               Protobuf Payload (N bytes, N >= 0)              +  Bytes 8..7+N   [TEXTO PLANO]
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

* **`rawLen` (`Bytes 0..3`, texto plano):** `int32` Big-Endian igual a `8 + N`. `ReceivePayload` lee estos 4 bytes y almacena `this.lastMsgLength = rawLen - 4 = 4 + N` (`VA 0x180CEDB7D..0x180CEDB81`).
* **`msgId` (`Bytes 4..7`, texto plano):** `int32` Big-Endian leído mediante `readInt32FromNetwork(this.binaryReader)` (`VA 0x180CEDBEF: call 0x180ceede0`).
* **`payload` (`Bytes 8..7+N`, texto plano):** Leído mediante `this.binaryReader.ReadBytes(this.lastMsgLength - 4)` (`VA 0x180CEDC09..0x180CEDC1D`, donde `lastMsgLength - 4 = N` bytes) y encolado directamente en `_receivePackage` (`SMsgData { msgID = esi, msgData = rdi }`) sin pasar por `Utils.RC4::Crypt`.

---

## 3. Mapa de Campos de Instancia (`Utils.TcpClient` y `Utils.RC4`)

Verificado a partir de `Utils.TcpClient::.ctor` (`VA 0x180CEE7C0`), `Connect` (`VA 0x180CEC710`), `Send_begin` (`VA 0x180CEDF60`), `ReceivePayload` (`VA 0x180CED970`) y `Utils.RC4::.ctor` (`VA 0x180D01B90`):

| Tipo | Offset | Nombre en Metadatos | Tipo de Campo | Evidencia en Ensamblador (`GameAssembly.dll`) |
|---|---|---|---|---|
| `Utils.RC4` (`TypeDef[1830]`) | `+0x10` | `S` | `System.Byte[]` (`256` bytes) | `VA 0x180D01BD3`: `ba00010000 mov edx, 0x100` $\rightarrow$ `mov [rdi+0x10], rax` (`VA 0x180D01BE4`) |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x10` | `mTcpState` | `Utils.TcpClient.TcpState` | `VA 0x180CEC9C6`: `mov [rdi+0x10], rbx` |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x18` | `_ready` | `System.Boolean` | `VA 0x180CEEB20` (`get_BeReady`): `movzx ebx, byte ptr [rcx+0x18]` |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x20` | `_sendBuffer` | `System.Byte[]` (`65536` bytes) | `VA 0x180CEE85C`: `mov edx, 0x10000` $\rightarrow$ `mov [rsi+0x20], rax` (`VA 0x180CEE86C`) |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x28` | `_sendStream` | `System.IO.MemoryStream` | `VA 0x180CEE986`: `mov [rsi+0x28], rdi` (envuelve `_sendBuffer`) |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x30` | `recvBuffer` | `System.IO.MemoryStream` | `VA 0x180CEE893`: `mov [rsi+0x30], rdi` |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x38` | `lastMsgLength` | `System.Int32` | `VA 0x180CEE89F`: `mov dword ptr [rsi+0x38], 0xffffffff` (`-1`) |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x3C` | `<ClientID>k__BackingField` | `System.Int32` | `VA 0x180CEE999`: `mov dword ptr [rsi+0x3c], ebp` |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x40` | `<SocketID>k__BackingField` | `System.Int32` | `VA 0x180517810` (`get_SocketID`): `mov eax, dword ptr [rcx+0x40]` |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x48` | `<cIp>k__BackingField` | `System.String` | `VA 0x180517830` (`get_cIp`): `mov rax, qword ptr [rcx+0x48]` |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x50` | `<nPort>k__BackingField` | `System.Int32` | `VA 0x18052D6D0` (`get_nPort`): `mov eax, dword ptr [rcx+0x50]` |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x54` | `netWorkState` | `Utils.ENetWorkState` | `VA 0x180CEC87D`: `mov dword ptr [rdi+0x54], esi` |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x60` | `_receivePackage` | `ThreadSafeQueue<SMsgData>` | `VA 0x180CEE8CF`: `mov [rsi+0x60], rdi` |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x68` | `_sendHeaderBuffer` | `System.Byte[]` (`8` bytes) | `VA 0x180CEE8DB`: `mov edx, 8` $\rightarrow$ `mov [rsi+0x68], rax` (`VA 0x180CEE8E9`) |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x70` | `_readKey` | `System.Boolean` | `VA 0x180CEDBCD`: `movzx edi, byte ptr [rbx+0x70]`; `VA 0x180CEDD0F`: `mov byte ptr [rbx+0x70], 1` |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x78` | `_rc4` | `Utils.RC4` | `VA 0x180CEDCFE`: `mov qword ptr [rbx+0x78], rsi` |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x80` | `binaryReader` | `System.IO.BinaryReader` | `VA 0x180CEDABF`: `mov qword ptr [rbx+0x80], rdi` |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x88` | `waitSendDatas` | `Queue<Utils.SendData>` | `VA 0x180CEE913`: `mov qword ptr [rsi+0x88], rdi` |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x90` | `memoryPool` | `ByteArrayMemoryPool` | `VA 0x180CEE944`: `mov qword ptr [rsi+0x90], rdi` |
| `Utils.TcpClient` (`TypeDef[1823]`) | `+0x98` | `lastSendTime` | `System.Single` (`float`) | `VA 0x180CEE137`: `movss dword ptr [rbx+0x98], xmm0` |

---

## 4. Desensamblado Instrucción por Instrucción de Métodos Clave

### 4.1. `Utils.RC4` (`TypeDef[1830]`)

#### A. `Utils.RC4::.ctor(byte[] key)`
* **Metadatos:** `Method[24926]`, Token `0x0600615F`, `RVA = 0xD01B90`, `VA = 0x180D01B90`, `FileOffset = 0xD00590`, Tamaño = `369` bytes.
* **Comportamiento verificado:**
  1. Reserva `this.S = new byte[256]` (`edx = 0x100` en `0x180D01BD3`, almacenado en `[rdi + 0x10]`).
  2. Inicializa `S[0..255] = 0..255` y un arreglo temporal `T[0..255] = key[i % key.Length]` (`idiv esi` en `0x180D01C35`, donde `esi = key.Length`).
  3. Ejecuta el Key-Scheduling Algorithm (KSA) estándar de RC4 (`j = (j + S[i] + T[i]) % 256`; intercambia `S[i]` y `S[j]` en `0x180D01C60..0x180D01CD7`).

```text
0x180D01B90 (+0x000): 48895c2408             mov      qword ptr [rsp + 8], rbx
0x180D01B95 (+0x005): 48896c2410             mov      qword ptr [rsp + 0x10], rbp
0x180D01B9A (+0x00A): 4889742418             mov      qword ptr [rsp + 0x18], rsi
0x180D01B9F (+0x00F): 57                     push     rdi
0x180D01BA0 (+0x010): 4883ec20               sub      rsp, 0x20
0x180D01BA4 (+0x014): 803d22a15c0300         cmp      byte ptr [rip + 0x35ca122], 0
0x180D01BAB (+0x01B): 488bda                 mov      rbx, rdx                 ; rbx = byte[] key
0x180D01BAE (+0x01E): 488bf9                 mov      rdi, rcx                 ; rdi = this (Utils.RC4)
...
0x180D01BC9 (+0x039): 488b0dd8573b03         mov      rcx, qword ptr [rip + 0x33b57d8] ; byte[] TypeInfo
0x180D01BD0 (+0x040): 488d6f10               lea      rbp, [rdi + 0x10]        ; &this.S
0x180D01BD4 (+0x044): ba00010000             mov      edx, 0x100               ; 256
0x180D01BD9 (+0x049): e8c2696dff             call     0x1803d85a0              ; il2cpp_array_new(byte[], 256)
0x180D01BDE (+0x04E): 488bd0                 mov      rdx, rax
0x180D01BE1 (+0x051): 488bcd                 mov      rcx, rbp
0x180D01BE4 (+0x054): 48894710               mov      qword ptr [rdi + 0x10], rax ; this.S = new byte[256]
0x180D01BE8 (+0x058): e8f3596dff             call     0x1803d75e0              ; WriteBarrier
0x180D01BED (+0x05D): 4885db                 test     rbx, rbx                 ; if (key == null) throw
0x180D01BF0 (+0x060): 0f84f1000000           je       0x180d01ce7
0x180D01BF6 (+0x066): 488b0dab573b03         mov      rcx, qword ptr [rip + 0x33b57ab]
0x180D01BFD (+0x06D): ba00010000             mov      edx, 0x100               ; 256
0x180D01C02 (+0x072): 8b7318                 mov      esi, dword ptr [rbx + 0x18] ; esi = key.Length
0x180D01C05 (+0x075): e896696dff             call     0x1803d85a0              ; rdi = T = new byte[256]
0x180D01C0A (+0x07A): 33c9                   xor      ecx, ecx                 ; i = 0
0x180D01C0C (+0x07C): 488bf8                 mov      rdi, rax
0x180D01C0F (+0x07F): 90                     nop
0x180D01C10 (+0x080): 488b4500               mov      rax, qword ptr [rbp]     ; rax = this.S
0x180D01C14 (+0x084): 4885c0                 test     rax, rax
0x180D01C17 (+0x087): 0f84ca000000           je       0x180d01ce7
0x180D01C1D (+0x08D): 3b4818                 cmp      ecx, dword ptr [rax + 0x18]
0x180D01C20 (+0x090): 0f83c7000000           jae      0x180d01ced
0x180D01C26 (+0x096): 4863c9                 movsxd   rcx, ecx
0x180D01C29 (+0x099): 884c0120               mov      byte ptr [rcx + rax + 0x20], cl ; this.S[i] = (byte)i
0x180D01C2D (+0x09D): 8bc1                   mov      eax, ecx
0x180D01C2F (+0x09F): 85f6                   test     esi, esi
0x180D01C31 (+0x0A1): 0f84bc000000           je       0x180d01cf3              ; DivideByZero check if key.Length == 0
0x180D01C37 (+0x0A3): 99                     cdq
0x180D01C38 (+0x0A4): f7fe                   idiv     esi                      ; edx = i % key.Length
0x180D01C3A (+0x0A6): 3b5318                 cmp      edx, dword ptr [rbx + 0x18]
0x180D01C3D (+0x0A9): 0f83aa000000           jae      0x180d01ced
0x180D01C43 (+0x0AF): 4885ff                 test     rdi, rdi
0x180D01C46 (+0x0B2): 0f849b000000           je       0x180d01ce7
0x180D01C4C (+0x0B8): 3b4f18                 cmp      ecx, dword ptr [rdi + 0x18]
0x180D01C4F (+0x0BB): 0f8398000000           jae      0x180d01ced
0x180D01C55 (+0x0C1): 4863c2                 movsxd   rax, edx
0x180D01C58 (+0x0C4): 0fb6441820             movzx    eax, byte ptr [rax + rbx + 0x20] ; key[i % key.Length]
0x180D01C5D (+0x0C9): 88443920               mov      byte ptr [rcx + rdi + 0x20], al  ; T[i] = key[i % key.Length]
0x180D01C61 (+0x0CD): ffc1                   inc      ecx
0x180D01C63 (+0x0CF): 81f900010000           cmp      ecx, 0x100               ; i < 256
0x180D01C69 (+0x0D5): 7ca5                   jl       0x180d01c10
0x180D01C6B (+0x0D7): 33c9                   xor      ecx, ecx                 ; i = 0
0x180D01C6D (+0x0D9): 33d2                   xor      edx, edx                 ; j = 0
...
0x180D01C82 (+0x0F2): 4863c9                 movsxd   rcx, ecx
0x180D01C85 (+0x0F5): 410fb65020             movzx    edx, byte ptr [r8 + 0x20] ; S[i]
0x180D01C8A (+0x0FA): 4403da                 add      r11d, edx                ; j + S[i]
0x180D01C92 (+0x102): 0fb6443920             movzx    eax, byte ptr [rcx + rdi + 0x20] ; T[i]
0x180D01C97 (+0x107): 4103c3                 add      eax, r11d                ; j + S[i] + T[i]
0x180D01C9A (+0x10A): 8bc8                   mov      ecx, eax
0x180D01C9C (+0x10C): c1f91f                 sar      ecx, 0x1f
0x180D01C9F (+0x10F): 81e1ff000000           and      ecx, 0xff
0x180D01CA5 (+0x115): 03c8                   add      ecx, eax
0x180D01CA7 (+0x117): 25ff000000             and      eax, 0xff
0x180D01CAC (+0x11C): 2bc1                   sub      eax, ecx
0x180D01CAE (+0x11E): 03c1                   add      eax, ecx                 ; eax = (j + S[i] + T[i]) % 256
0x180D01CB0 (+0x120): 8bd0                   mov      edx, eax                 ; j = eax
...
0x180D01CC1 (+0x131): 430fb6441120           movzx    eax, byte ptr [r9 + r10 + 0x20] ; S[j]
0x180D01CC7 (+0x137): 41884020               mov      byte ptr [r8 + 0x20], al        ; S[i] = S[j]
0x180D01CCB (+0x13B): 488b4500               mov      rax, qword ptr [rbp]
...
0x180D01CD7 (+0x147): 46885c0220             mov      byte ptr [rdx + r8 + 0x20], r11b ; S[j] = old S[i]
0x180D01CDC (+0x14C): ffc1                   inc      ecx
0x180D01CDE (+0x14E): 81f900010000           cmp      ecx, 0x100
0x180D01CE4 (+0x154): 7c8a                   jl       0x180d01c70
0x180D01CE6 (+0x156): c3                     ret
```

#### B. `Utils.RC4::Crypt(byte[] pt, int start, int end)`
* **Metadatos:** `Method[24927]`, Token `0x06006160`, `RVA = 0xD01A50`, `VA = 0x180D01A50`, `FileOffset = 0xD00450`, Tamaño = `312` bytes.
* **Parámetros (`x64` fastcall):** `rcx = this`, `rdx = byte[] pt`, `r8d = int start`, `r9d = int end`.
* **Comportamiento verificado:**
  1. Si `end < 0` (`test r9d, r9d; jns`), toma `end = pt.Length` (`mov r9d, dword ptr [rdx + 0x18]` en `0x180D01A6C`).
  2. Inicializa los índices locales del generador pseudoaleatorio (PRGA) a cero en cada invocación: `i = 0` (`xor r10d, r10d`) y `j = 0` (`xor r11d, r11d`).
  3. Para cada índice `k` (`r8d`) desde `start` hasta `end - 1` (`cmp r8d, r9d; jge 0x180d01b6a`):
     - `i = (i + 1) % 256` (`inc r10d`, módulo 256 en `0x180D01A86..0x180D01A9D`).
     - `j = (j + S[i]) % 256` (`0x180D01AA6..0x180D01AC1`).
     - Intercambia `S[i]` y `S[j]` en `this.S` (`0x180D01AC6..0x180D01AD7`). **Nota crítica:** La mutación de `this.S` ocurre in-place sobre `[rcx + 0x10]`, por lo que `this.S` evoluciona de paquete en paquete aunque `i` y `j` se reinicien a `0` al comenzar cada llamada a `Crypt`.
     - Calcula `t = (S[i] + S[j]) % 256` (`0x180D01AF8..0x180D01B1E`).
     - Hace `pt[k] ^= S[t]` (`xor byte ptr [r8 + rdx + 0x20], al` en `0x180D01B36`).

```text
0x180D01A50 (+0x000): 48895c2408             mov      qword ptr [rsp + 8], rbx
0x180D01A55 (+0x005): 4889742410             mov      qword ptr [rsp + 0x10], rsi
0x180D01A5A (+0x00A): 4533d2                 xor      r10d, r10d               ; i = 0
0x180D01A5D (+0x00D): 488bf2                 mov      rsi, rdx                 ; rsi = pt
0x180D01A60 (+0x010): 4533db                 xor      r11d, r11d               ; j = 0
0x180D01A63 (+0x013): 488bd9                 mov      rbx, rcx                 ; rbx = this
0x180D01A66 (+0x016): 4585c9                 test     r9d, r9d                 ; if (end >= 0) goto loop_check
0x180D01A69 (+0x019): 7908                   jns      0x180d01a73
0x180D01A6B (+0x01B): 4885d2                 test     rdx, rdx
0x180D01A6E (+0x01E): 7464                   je       0x180d01ad4
0x180D01A70 (+0x020): 448b4a18               mov      r9d, dword ptr [rdx + 0x18] ; end = pt.Length
0x180D01A74 (+0x024): 453bc1                 cmp      r8d, r9d                 ; start >= end ?
0x180D01A77 (+0x027): 0f8d8d000000           jge      0x180d01b0a
...
0x180D01A80 (+0x030): 488b4310               mov      rax, qword ptr [rbx + 0x10] ; rax = this.S
0x180D01A84 (+0x034): 41ffc2                 inc      r10d                     ; i = i + 1
...
0x180D01AC6 (+0x076): 420fb6441020           movzx    eax, byte ptr [rax + r10 + 0x20] ; S[j]
0x180D01ACC (+0x07C): 418801                 mov      byte ptr [r9], al        ; S[i] = S[j]
0x180D01ACF (+0x07F): 488b4310               mov      rax, qword ptr [rbx + 0x10]
0x180D01AD3 (+0x083): 4688540220             mov      byte ptr [rdx + rax + 0x20], r10b ; S[j] = old S[i]
...
0x180D01B31 (+0x0E1): 0fb6440120             movzx    eax, byte ptr [rcx + rax + 0x20] ; S[(S[i] + S[j]) % 256]
0x180D01B36 (+0x0E6): 4230443020             xor      byte ptr [r8 + rsi + 0x20], al   ; pt[k] ^= S[t]
0x180D01B3B (+0x0EB): 41ffc0                 inc      r8d                      ; k++
0x180D01B3E (+0x0EE): 453bc1                 cmp      r8d, r9d                 ; k < end
0x180D01B41 (+0x0F1): 0f8c39ffffff           jl       0x180d01a80
```

---

### 4.2. Helpers de Enteros de 32 Bits en Orden de Red (`Big-Endian`)

#### A. `Utils.TcpClient::setBufferInt(byte[] buf, int value, int offset)`
* **Metadatos:** `Method[24845]`, Token `0x0600610E`, `RVA = 0xCEEF10`, `VA = 0x180CEEF10`, `FileOffset = 0xCED910`, Tamaño = `77` bytes.
* **Comportamiento verificado:** Recorre `r11d = 24, 16, 8, 0` (`mov r11d, 0x18` ... `sub r11d, 8`), desplazando `value` (`r8d`) a la derecha (`sar edx, cl`) y escribiendo cada byte en `buf[offset + 0..3]` (`mov byte ptr [rbx + r10 + 0x20], dl`). Codificación **Big-Endian**.

```text
0x180CEEF10 (+0x000): 48895c2408             mov      qword ptr [rsp + 8], rbx
0x180CEEF15 (+0x005): 57                     push     rdi
0x180CEEF16 (+0x006): 4883ec20               sub      rsp, 0x20
0x180CEEF1A (+0x00A): 41bb18000000           mov      r11d, 0x18               ; shift = 24
0x180CEEF20 (+0x010): 488bda                 mov      rbx, rdx                 ; rbx = buf
0x180CEEF23 (+0x013): 418bc1                 mov      eax, r9d                 ; eax = offset
0x180CEEF26 (+0x016): 4c63d0                 movsxd   r10, eax
0x180CEEF29 (+0x019): 41ffc1                 inc      r9d                      ; offset++
0x180CEEF2C (+0x01C): 4885db                 test     rbx, rbx
0x180CEEF2F (+0x01F): 7420                   je       0x180ceef51
0x180CEEF31 (+0x021): 3b4318                 cmp      eax, dword ptr [rbx + 0x18]
0x180CEEF34 (+0x024): 7321                   jae      0x180ceef57
0x180CEEF36 (+0x026): 418bcb                 mov      ecx, r11d                ; cl = shift (24, 16, 8, 0)
0x180CEEF39 (+0x029): 418bd0                 mov      edx, r8d                 ; edx = value
0x180CEEF3C (+0x02C): d3fa                   sar      edx, cl                  ; edx = value >> shift
0x180CEEF3E (+0x02E): 4183eb08               sub      r11d, 8                  ; shift -= 8
0x180CEEF42 (+0x032): 4288541320             mov      byte ptr [rbx + r10 + 0x20], dl ; buf[offset] = (byte)(value >> shift)
0x180CEEF47 (+0x037): 4183fbf8               cmp      r11d, -8
0x180CEEF4B (+0x03B): 7fd6                   jg       0x180ceef23
```

#### B. `Utils.TcpClient::getBufferInt(byte[] buf)`
* **Metadatos:** `Method[24846]`, Token `0x0600610F`, `RVA = 0xCEEAC0`, `VA = 0x180CEEAC0`, `FileOffset = 0xCED4C0`, Tamaño = `84` bytes.
* **Comportamiento verificado:** Lee `buf[0..3]` desplazando a la izquierda por `24, 16, 8, 0` (`shl edx, cl; add eax, edx`). Decodificación **Big-Endian**.

```text
0x180CEEAC0 (+0x000): 4883ec28               sub      rsp, 0x28
0x180CEEAC4 (+0x004): 33c0                   xor      eax, eax                 ; result = 0
0x180CEEAC6 (+0x006): 4533c0                 xor      r8d, r8d                 ; idx = 0
0x180CEEAC9 (+0x009): 41b918000000           mov      r9d, 0x18                ; shift = 24
0x180CEEAD0 (+0x010): 4885d2                 test     rdx, rdx
0x180CEEAD3 (+0x013): 7431                   je       0x180ceeb06
0x180CEEAD5 (+0x015): 4c63d0                 movsxd   r10, eax
0x180CEEAD8 (+0x018): 3b4218                 cmp      eax, dword ptr [rdx + 0x18]
0x180CEEADB (+0x01B): 7331                   jae      0x180ceeb0e
0x180CEEADD (+0x01D): 418bc9                 mov      ecx, r9d                 ; cl = shift (24, 16, 8, 0)
0x180CEEAE0 (+0x020): 4183e908               sub      r9d, 8                   ; shift -= 8
0x180CEEAE4 (+0x024): 420fb6541220           movzx    edx, byte ptr [rdx + r10 + 0x20] ; buf[idx]
0x180CEEAEC (+0x02C): d3e2                   shl      edx, cl                  ; buf[idx] << shift
0x180CEEAEE (+0x02E): 4103d0                 add      edx, r8d                 ; sum += (buf[idx] << shift)
```

#### C. `Utils.TcpClient::readInt32FromNetwork(BinaryReader br)`
* **Metadatos:** `Method[24836]`, Token `0x06006105`, `RVA = 0xCEEDE0`, `VA = 0x180CEEDE0`, `FileOffset = 0xCED7E0`, Tamaño = `120` bytes.
* **Comportamiento verificado:** Invoca `br.ReadBytes(4)` (`mov edx, 4; call qword ptr [r8 + 0x2d8]` en `0x180CEEDF2..0x180CEEEDF`) y reconstruye un `int32` **Big-Endian** desplazando por `24, 16, 8, 0` (`shl r8d, cl; add r10d, r8d` en `0x180CEEE10..0x180CEEE3A`).

```text
0x180CEEDF2 (+0x012): ba04000000             mov      edx, 4                   ; count = 4
0x180CEEDF7 (+0x017): 498b80d8020000         mov      rax, qword ptr [r8 + 0x2d8] ; BinaryReader.ReadBytes(4)
0x180CEEDFE (+0x01E): 4d8b80e0020000         mov      r8, qword ptr [r8 + 0x2e0]
0x180CEEE05 (+0x025): ffd0                   call     rax
0x180CEEE07 (+0x027): 33d2                   xor      edx, edx                 ; idx = 0
0x180CEEE09 (+0x029): 4533d2                 xor      r10d, r10d               ; result = 0
0x180CEEE0C (+0x02C): 488bd8                 mov      rbx, rax                 ; rbx = byte[4]
0x180CEEE0F (+0x02F): 41b918000000           mov      r9d, 0x18                ; shift = 24
...
0x180CEEE22 (+0x042): 418bc9                 mov      ecx, r9d
0x180CEEE25 (+0x045): 4183e908               sub      r9d, 8
0x180CEEE29 (+0x049): 460fb6441b20           movzx    r8d, byte ptr [rbx + r11 + 0x20]
0x180CEEE2F (+0x04F): 41d3e0                 shl      r8d, cl
0x180CEEE32 (+0x052): ffc2                   inc      edx
0x180CEEE34 (+0x054): 4503d0                 add      r10d, r8d
0x180CEEE37 (+0x057): 4183f9f8               cmp      r9d, -8
0x180CEEE3B (+0x05B): 7fd3                   jg       0x180ceee10
0x180CEEE3D (+0x05D): 418bc2                 mov      eax, r10d                ; return result
```

---

### 4.3. Construcción y Cifrado de Tramas Salientes (`Send_begin`, `Send`, `rawSend`)

#### A. `Utils.TcpClient::Send_begin(int msgId, byte[] data, int dataSize)`
* **Metadatos:** `Method[24842]`, Token `0x0600610B`, `RVA = 0xCEDF60`, `VA = 0x180CEDF60`, `FileOffset = 0xCEC960`, Tamaño = `502` bytes.
* **Secuencia exacta de instrucciones:**
  1. `0x180CEDF85..0x180CEDFA5`: `this._sendStream.Seek(8, SeekOrigin.Begin)` (`edx = 8, r8d = 0, call [r9 + 0x318]`).
  2. `0x180CEDFA7..0x180CEDFD3`: `this._sendStream.Write(data, 0, dataSize)` (`rdx = rsi, r8d = 0, r9d = edi, call [rax + 0x368]`).
  3. `0x180CEDFD6..0x180CEDFF4`: `esi = (int)this._sendStream.Position` (`call [rdx + 0x1f8]`; `esi = 8 + dataSize`).
  4. `0x180CEDFF6..0x180CEE040`: Inlined `setBufferInt(this._sendHeaderBuffer, esi, 0)` — escribe `totalLen = 8 + dataSize` en `_sendHeaderBuffer[0..3]` en **Big-Endian**.
  5. `0x180CEE042..0x180CEE080`: Inlined `setBufferInt(this._sendHeaderBuffer, ebp, 4)` — escribe `msgId` en `_sendHeaderBuffer[4..7]` en **Big-Endian** (`mov r8d, 4`).
  6. `0x180CEE082..0x180CEE0D7`: `this._sendStream.Seek(0, SeekOrigin.Begin)` y `this._sendStream.Write(this._sendHeaderBuffer, 0, 8)` (`mov r9d, 8`).
  7. `0x180CEE0DA..0x180CEE10A`: Si `this._rc4 != null` (`cmp qword ptr [rbx + 0x78], 0`), llama a `this._rc4.Crypt(this._sendBuffer, 4, totalLen)` (`rdx = _sendBuffer, r8d = 4, r9d = esi, call 0x180d01a50`).
  8. `0x180CEE10F..0x180CEE12D`: Llama a `this.mTcpState.Send(this._sendBuffer, totalLen)` (`call 0x180cef460`) y actualiza `this.lastSendTime = Time.realtimeSinceStartup` (`movss [rbx + 0x98], xmm0`).

```text
0x180CEDF85 (+0x025): 488b4b28               mov      rcx, qword ptr [rbx + 0x28] ; this._sendStream
0x180CEDF91 (+0x031): 4533c0                 xor      r8d, r8d                    ; SeekOrigin.Begin (0)
0x180CEDF94 (+0x034): ba08000000             mov      edx, 8                      ; offset = 8
0x180CEDFA3 (+0x043): ffd0                   call     rax                         ; _sendStream.Seek(8, Begin)
...
0x180CEDFB6 (+0x056): 448bcf                 mov      r9d, edi                    ; count = dataSize
0x180CEDFB9 (+0x059): 4533c0                 xor      r8d, r8d                    ; offset = 0
0x180CEDFBC (+0x05C): 488bd6                 mov      rdx, rsi                    ; buffer = data
0x180CEDFD0 (+0x070): 41ffd2                 call     r10                         ; _sendStream.Write(data, 0, dataSize)
...
0x180CEDFF0 (+0x090): ffd0                   call     rax                         ; rax = _sendStream.Position (8 + dataSize)
0x180CEDFF2 (+0x092): 4c8b4b68               mov      r9, qword ptr [rbx + 0x68]  ; r9 = _sendHeaderBuffer
0x180CEDFF6 (+0x096): 41ba18000000           mov      r10d, 0x18                  ; shift = 24
0x180CEDFFC (+0x09C): 488bf0                 mov      rsi, rax                    ; esi = totalLen (8 + dataSize)
0x180CEDFFF (+0x09F): 4533c0                 xor      r8d, r8d                    ; offset = 0
...
0x180CEE031 (+0x0D1): 8bd6                   mov      edx, esi                    ; edx = totalLen
0x180CEE033 (+0x0D3): d3fa                   sar      edx, cl
0x180CEE039 (+0x0D9): 4288540f20             mov      byte ptr [rdi + r9 + 0x20], dl ; _sendHeaderBuffer[0..3] = totalLen (BE)
...
0x180CEE042 (+0x0E2): 4c8b4b68               mov      r9, qword ptr [rbx + 0x68]  ; r9 = _sendHeaderBuffer
0x180CEE046 (+0x0E6): 41b804000000           mov      r8d, 4                      ; offset = 4
0x180CEE04C (+0x0EC): 41bb18000000           mov      r11d, 0x18                  ; shift = 24
...
0x180CEE06D (+0x10D): 8bd5                   mov      edx, ebp                    ; edx = msgId
0x180CEE06F (+0x10F): d3fa                   sar      edx, cl
0x180CEE075 (+0x115): 4388540a20             mov      byte ptr [r10 + r9 + 0x20], dl ; _sendHeaderBuffer[4..7] = msgId (BE)
...
0x180CEE0DA (+0x17A): 488b7b20               mov      rdi, qword ptr [rbx + 0x20] ; rdi = _sendBuffer
0x180CEE0EA (+0x18A): 48837b7800             cmp      qword ptr [rbx + 0x78], 0   ; if (this._rc4 != null)
0x180CEE0EF (+0x18F): 741e                   je       0x180cee10f
0x180CEE0F1 (+0x191): 488b4b78               mov      rcx, qword ptr [rbx + 0x78] ; rcx = this._rc4
0x180CEE0F5 (+0x195): 448bce                 mov      r9d, esi                    ; r9d = end = totalLen
0x180CEE0F8 (+0x198): 41b804000000           mov      r8d, 4                      ; r8d = start = 4
0x180CEE107 (+0x1A7): 488bd7                 mov      rdx, rdi                    ; rdx = this._sendBuffer
0x180CEE10A (+0x1AA): e841390100             call     0x180d01a50                 ; -> Utils.RC4::Crypt(_sendBuffer, 4, totalLen)
0x180CEE10F (+0x1AF): 488b4b10               mov      rcx, qword ptr [rbx + 0x10] ; rcx = this.mTcpState
0x180CEE11A (+0x1BA): 448bc6                 mov      r8d, esi                    ; r8d = totalLen
0x180CEE11D (+0x1BD): 488bd7                 mov      rdx, rdi                    ; rdx = this._sendBuffer
0x180CEE120 (+0x1C0): e83b130000             call     0x180cef460                 ; -> TcpState::Send(_sendBuffer, totalLen)
```

#### B. `Utils.TcpClient::Send(int msgId, byte[] data, int dataSize)` y `Utils.TcpClient::Send(msg_base msg)`
* **`Send(int, byte[], int)` (`Method[24840]`, Token `0x06006109`, `VA = 0x180CEE160`):**
  - Verifica `if (!this._ready) return;` (`movzx ebx, byte ptr [rdi + 0x18]` en `0x180CEE1F0`; `test bl, bl; je 0x180cee3e4`).
  - Omite el log de depuración cuando `msgId == 0x45C` (`1116 = CSPing`, `cmp esi, 0x45c` en `0x180CEE23D`).
  - Si hay cola activa (`waitSendDatas.Count > 0` o `mTcpState.isSending`), encola un `SendData` en `this.waitSendDatas` (`0x180CEE3C4`), que luego `DealMessage()` procesa llamando a `Send_begin` (`0x180CED225: call 0x180cedf60`). En caso contrario, invoca directamente `Send_begin` (`0x180CEE3DF: call 0x180cedf60`).
* **`Send(msg_base)` (`Method[24841]`, Token `0x0600610A`, `VA = 0x180CEE410`):**
  - Verifica `if (!this._ready) return;` (`0x180CEE472..0x180CEE47D`).
  - Ejecuta la misma secuencia inlined que `Send_begin`: `Seek(8, Begin)` $\rightarrow$ `Serializer.Serialize(_sendStream, msg)` (`0x180CEE55B`) $\rightarrow$ escribe `totalLen` en `_sendHeaderBuffer[0..3]` y `msg.msgId` en `_sendHeaderBuffer[4..7]` $\rightarrow$ escribe cabecera en `_sendBuffer[0..7]` $\rightarrow$ `this._rc4.Crypt(_sendBuffer, 4, totalLen)` (`0x180CEE68D..0x180CEE6A6`) $\rightarrow$ `mTcpState.Send(_sendBuffer, totalLen)` (`0x180CEE6BD`).

#### C. `Utils.TcpClient::rawSend(byte[] data, int length)`
* **Metadatos:** `Method[24844]`, Token `0x0600610D`, `RVA = 0xCEF0A0`, `VA = 0x180CEF0A0`, `FileOffset = 0xCEDAA0`, Tamaño = `30` bytes.
* **Comportamiento verificado:** Envoltura directa que delega en `this.mTcpState.Send(data, length)` (`0x180CEF0B4: jmp 0x180cef460`).

```text
0x180CEF0A0 (+0x000): 488b4910               mov      rcx, qword ptr [rcx + 0x10] ; rcx = this.mTcpState
0x180CEF0A4 (+0x004): 4885c9                 test     rcx, rcx
0x180CEF0A7 (+0x007): 740e                   je       0x180cef0b7
0x180CEF0A9 (+0x009): 458bc0                 mov      r8d, r8d
0x180CEF0AC (+0x00C): 4533c9                 xor      r9d, r9d
0x180CEF0AF (+0x00F): e9ac030000             jmp      0x180cef460                 ; -> TcpState::Send(data, length)
```

---

### 4.4. Recepción, Handshake de Clave RC4 y Despacho (`ReceivePayload`, `DealMessage`, `Connect`)

#### A. `Utils.TcpClient::ReceivePayload(byte[] data, int length)`
* **Metadatos:** `Method[24837]`, Token `0x06006106`, `RVA = 0xCED970`, `VA = 0x180CED970`, `FileOffset = 0xCEC370`, Tamaño = `1515` bytes.
* **Secuencia exacta de instrucciones:**
  1. **Acumulación (`0x180CED9C1..0x180CEDA3F`):** Busca el final de `this.recvBuffer` (`[rbx + 0x30]`) y escribe `data[0..length]`.
  2. **Comprobación de longitud mínima (`0x180CEDA42..0x180CEDA6C`):** Si `this.lastMsgLength < 0` (`cmp dword ptr [rbx + 0x38], 0; jns`) y `this.recvBuffer.Length < 4` (`cmp rax, 4; jl 0x180cede8f`), retorna esperando más datos.
  3. **Lectura del prefijo de longitud (`0x180CEDAD5..0x180CEDB81`):**
     - Posiciona `recvBuffer` en `0` (`0x180CEDA7B`).
     - Si `this.lastMsgLength < 0`: lee 4 bytes en Big-Endian (`r11d = rawLen`) y guarda **`this.lastMsgLength = rawLen - 4`** (`0x180CEDB7D: 418d43fc lea eax, [r11 - 4]`, `0x180CEDB81: 894338 mov dword ptr [rbx + 0x38], eax`).
     - Si `this.lastMsgLength >= 0`: salta los primeros 4 bytes (`recvBuffer.set_Position(4)` en `0x180CEDAF7..0x180CEDB05`).
  4. **Comprobación de trama completa (`0x180CEDB84..0x180CEDBBB`):**
     - Calcula `availableBody = recvBuffer.Length - 4` (`0x180CEDBB3: 8d78fc lea edi, [rax - 4]`).
     - Si `availableBody < this.lastMsgLength` (`cmp edi, dword ptr [rbx + 0x38]; jl 0x180cedeb2`), sale del bucle hasta recibir el resto del paquete.
  5. **Bifurcación por `this._readKey` (`0x180CEDBCD..0x180CEDD12`):**
     - **Rama `_readKey == false` (`0x180CEDCBB..0x180CEDD12` — Handshake Inicial RC4):**
       - Lee `keyBytes = this.binaryReader.ReadBytes(this.lastMsgLength)` (`0x180CEDCC7..0x180CEDCD8`).
       - Crea `this._rc4 = new Utils.RC4(keyBytes)` (`0x180CEDCE4..0x180CEDCFE`).
       - Activa `this._readKey = 1` (`0x180CEDD0F: c6437001 mov byte ptr [rbx + 0x70], 1`).
     - **Rama `_readKey == true` (`0x180CEDBE6..0x180CEDCB9` — Trama Normal Servidor $\rightarrow$ Cliente):**
       - Lee `msgID = this.readInt32FromNetwork(this.binaryReader)` (`0x180CEDBEF: call 0x180ceede0`).
       - Calcula `payloadLen = this.lastMsgLength - 4` (`0x180CEDC09: mov edx, dword ptr [rbx + 0x38]`, `0x180CEDC0C: sub edx, 4`).
       - Lee `msgData = this.binaryReader.ReadBytes(payloadLen)` (`0x180CEDC0F..0x180CEDC1D`).
       - Encola `SMsgData(msgID, msgData)` en `this._receivePackage` (`0x180CEDCB4: call 0x1816c2e40`).
  6. **Compactación de `recvBuffer` (`0x180CEDD14..0x180CEDE8A`):**
     - Calcula los bytes restantes `remaining = (int)(recvBuffer.Length - recvBuffer.Position)` (`0x180CEDD4C: sub rdi, rax`).
     - Lee los `remaining` bytes, reinicia `recvBuffer.Position = 0` y `recvBuffer.SetLength(0)`, reescribe los `remaining` bytes al inicio de `recvBuffer`, y si `remaining > 4` lee el siguiente `rawLen` (`lastMsgLength = rawLen - 4` en `0x180CEDE6C..0x180CEDE70`) o pone `this.lastMsgLength = -1` (`0x180CEDE83: c74338ffffffff mov dword ptr [rbx + 0x38], 0xffffffff`).

```text
0x180CEDB7D (+0x20D): 418d43fc               lea      eax, [r11 - 4]              ; eax = rawLen - 4
0x180CEDB81 (+0x211): 894338                 mov      dword ptr [rbx + 0x38], eax ; this.lastMsgLength = rawLen - 4
...
0x180CEDBB3 (+0x243): 8d78fc                 lea      edi, [rax - 4]              ; edi = recvBuffer.Length - 4
0x180CEDBB6 (+0x246): 3b7b38                 cmp      edi, dword ptr [rbx + 0x38] ; if (recvBuffer.Length - 4 < lastMsgLength)
0x180CEDBB9 (+0x249): 0f8cf3020000           jl       0x180cedeb2                 ; wait for more bytes
...
0x180CEDBCD (+0x25D): 0fb67b70               movzx    edi, byte ptr [rbx + 0x70]  ; edi = this._readKey
0x180CEDBD1 (+0x261): e83aa96eff             call     0x1803d8510
0x180CEDBD6 (+0x266): 488b8b80000000         mov      rcx, qword ptr [rbx + 0x80] ; rcx = this.binaryReader
0x180CEDBDD (+0x26D): 4084ff                 test     dil, dil                    ; if (!this._readKey)
0x180CEDBE0 (+0x270): 0f84d5000000           je       0x180cedcbb                 ; -> goto Handshake Key Branch
; --- Rama _readKey == true (Mensajes normales Server -> Client) ---
0x180CEDBE6 (+0x276): 488bd1                 mov      rdx, rcx                    ; rdx = this.binaryReader
0x180CEDBE9 (+0x279): 4533c0                 xor      r8d, r8d
0x180CEDBEC (+0x27C): 488bcb                 mov      rcx, rbx                    ; rcx = this
0x180CEDBEF (+0x27F): e8ec110000             call     0x180ceede0                 ; esi = readInt32FromNetwork(binaryReader) [msgID]
0x180CEDBF4 (+0x284): 488b8b80000000         mov      rcx, qword ptr [rbx + 0x80]
0x180CEDBFB (+0x28B): 8bf0                   mov      esi, eax
0x180CEDC09 (+0x299): 8b5338                 mov      edx, dword ptr [rbx + 0x38] ; edx = this.lastMsgLength (rawLen - 4)
0x180CEDC0C (+0x29C): 83ea04                 sub      edx, 4                      ; edx = lastMsgLength - 4 (rawLen - 8)
0x180CEDC0F (+0x29F): 4d8b88d8020000         mov      r9, qword ptr [r8 + 0x2d8]  ; BinaryReader.ReadBytes(edx)
0x180CEDC1D (+0x2AD): 41ffd1                 call     r9                          ; rdi = msgData
...
0x180CEDCB4 (+0x344): e887519d00             call     0x1816c2e40                 ; _receivePackage.Enqueue(SMsgData)
0x180CEDCB9 (+0x349): eb59                   jmp      0x180cedd14
; --- Rama _readKey == false (Trama 0: Handshake de clave RC4) ---
0x180CEDCBB (+0x34B): 4885c9                 test     rcx, rcx
0x180CEDCBE (+0x34E): 0f848b020000           je       0x180cedf4f
0x180CEDCC4 (+0x354): 4c8b01                 mov      r8, qword ptr [rcx]
0x180CEDCC7 (+0x357): 8b5338                 mov      edx, dword ptr [rbx + 0x38] ; edx = this.lastMsgLength (rawLen - 4)
0x180CEDCCA (+0x35A): 498b80d8020000         mov      rax, qword ptr [r8 + 0x2d8] ; BinaryReader.ReadBytes(lastMsgLength)
0x180CEDCD8 (+0x368): ffd0                   call     rax                         ; rdi = keyBytes
0x180CEDCDA (+0x36A): 488b0dc7a33a03         mov      rcx, qword ptr [rip + 0x33aa3c7] ; Utils.RC4 TypeInfo
0x180CEDCE1 (+0x371): 488bf8                 mov      rdi, rax
0x180CEDCE4 (+0x374): e897a86eff             call     0x1803d8580                 ; il2cpp_object_new(Utils.RC4)
0x180CEDCEC (+0x37C): 488bd7                 mov      rdx, rdi                    ; rdx = keyBytes
0x180CEDCEF (+0x37F): 488bc8                 mov      rcx, rax
0x180CEDCF5 (+0x385): e8963e0100             call     0x180d01b90                 ; -> Utils.RC4::.ctor(keyBytes)
0x180CEDCFE (+0x38E): 48897378               mov      qword ptr [rbx + 0x78], rsi ; this._rc4 = new RC4(keyBytes)
0x180CEDD0F (+0x39F): c6437001               mov      byte ptr [rbx + 0x70], 1    ; this._readKey = true
```

#### B. `Utils.TcpClient::DealMessage()` y `Connect`
* **`DealMessage()` (`Method[24829]`, Token `0x060060FE`, `VA = 0x180CED0C0`):**
  - Drena `waitSendDatas` llamando a `Send_begin` (`0x180CED225: call 0x180cedf60`).
  - Desencola hasta 16 estructuras `SMsgData` por tick desde `_receivePackage` (`0x180CED29D: call 0x1816c2c50`, `cmp eax, 0xf; jle 0x180ced260`) y las entrega directamente a `NetMod` (`0x180CED2F5: call 0x180d89cc0` y `0x180CED35E: call 0x180d82320`) **sin aplicar ningún descifrado**.
* **`Connect` (`Method[24825]`, Token `0x060060FA`, `VA = 0x180CEC710`):**
  - Al iniciar conexión reinicia `this._ready = 0` (`0x180CEC7DF`), `this._readKey = 0` (`0x180CEC7EC`), `this.lastMsgLength = -1` (`0x180CEC7F0`) y vacía `recvBuffer` y `waitSendDatas`.
  - En `0x180CECA55..0x180CECA87`, calcula `this._ready = (mTcpState.state == 2 && this._readKey != 0)`.

---

## 5. Pseudocódigo de Referencia (Handshake + Bucle de Envío/Recepción)

```python
import struct

class P5XRC4:
    """Implementación exacta de Utils.RC4 (TypeDef[1830], VA 0x180D01A50 / 0x180D01B90)."""
    def __init__(self, key: bytes):
        assert len(key) >= 1
        self.S = list(range(256))
        T = [key[i % len(key)] for i in range(256)]
        j = 0
        for i in range(256):
            j = (j + self.S[i] + T[i]) & 0xFF
            self.S[i], self.S[j] = self.S[j], self.S[i]

    def crypt(self, buf: bytearray, start: int = 4, end: int = -1) -> None:
        if end < 0:
            end = len(buf)
        # En Utils.RC4::Crypt (VA 0x180D01A5A..0x180D01A60), i y j se inicializan a 0
        # en cada llamada, pero self.S muta y persiste entre llamadas.
        i = 0
        j = 0
        S = self.S
        for k in range(start, end):
            i = (i + 1) & 0xFF
            j = (j + S[i]) & 0xFF
            S[i], S[j] = S[j], S[i]
            t = (S[i] + S[j]) & 0xFF
            buf[k] ^= S[t]


def server_build_handshake_frame(rc4_key: bytes) -> bytes:
    """Trama 0 (Server -> Client): [int32 BE rawLen = 4 + len(rc4_key)][rc4_key] en texto plano."""
    raw_len = 4 + len(rc4_key)
    return struct.pack(">i", raw_len) + rc4_key


def server_read_client_frame(sock_read_exact, server_rc4: P5XRC4) -> tuple[int, bytes]:
    """Lee y descifra una trama Client -> Server enviada por Utils.TcpClient::Send_begin."""
    # Bytes 0..3: totalLen (int32 Big-Endian, SIEMPRE EN TEXTO PLANO)
    raw_len_bytes = sock_read_exact(4)
    (total_len,) = struct.unpack(">i", raw_len_bytes)
    assert total_len >= 8

    # Bytes 4..totalLen-1: [msgId BE (4B)][payload (totalLen - 8 B)] CIFRADOS CON RC4
    encrypted_body = bytearray(sock_read_exact(total_len - 4))
    frame_buf = bytearray(raw_len_bytes) + encrypted_body

    # Descifrar in-place desde offset 4 hasta total_len
    server_rc4.crypt(frame_buf, start=4, end=total_len)

    (msg_id,) = struct.unpack(">i", frame_buf[4:8])
    payload = bytes(frame_buf[8:total_len])
    return msg_id, payload


def server_build_message_frame(msg_id: int, protobuf_payload: bytes) -> bytes:
    """Construye una trama Server -> Client normal (cuando _readKey == true): SIEMPRE EN TEXTO PLANO."""
    total_len = 8 + len(protobuf_payload)
    return struct.pack(">ii", total_len, msg_id) + protobuf_payload
```

---

## 6. Tabla de Evidencia (`Afirmación | Nivel | Cita`)

| # | Afirmación | Nivel | Cita Verificable (`TypeDef`, Método, Offset/RVA/VA, Bytes) |
|---|---|---|---|
| 1 | La cabecera de mensaje tiene 8 bytes (`_sendHeaderBuffer = new byte[8]`, payload escrito en `_sendStream` desde offset `8`). | `CONFIRMADO` | `TypeDef[1823]`, `.ctor` (`RVA 0xCEE8DB`, `VA 0x180CEE8DB`, `ba08000000 mov edx, 8`); `Send_begin` (`RVA 0xCEDF94`, `VA 0x180CEDF94`, `ba08000000 mov edx, 8` en `MemoryStream.Seek`). |
| 2 | Los bytes `0..3` de la cabecera contienen `totalLen = 8 + dataSize` codificado en **Big-Endian** (`int32`). | `CONFIRMADO` | `TypeDef[1823]`, `Send_begin` (`RVA 0xCEDFF0..0xCEE040`, `VA 0x180CEDFF0..0x180CEE040`, `41ba18000000 mov r10d, 0x18` ... `d3fa sar edx, cl; 4288540f20 mov byte ptr [rdi+r9+0x20], dl`). |
| 3 | Los bytes `4..7` de la cabecera contienen `msgId` codificado en **Big-Endian** (`int32`). | `CONFIRMADO` | `TypeDef[1823]`, `Send_begin` (`RVA 0xCEE042..0xCEE080`, `VA 0x180CEE042..0x180CEE080`, `41b804000000 mov r8d, 4; 41bb18000000 mov r11d, 0x18` ... `d3fa sar edx, cl; 4388540a20 mov byte ptr [r10+r9+0x20], dl`). |
| 4 | En recepción (`ReceivePayload`), los bytes `0..3` (`rawLen`) también incluyen los 4 bytes del propio campo de longitud (`lastMsgLength = rawLen - 4`). | `CONFIRMADO` | `TypeDef[1823]`, `ReceivePayload` (`RVA 0xCEDB7D..0xCEDB81`, `VA 0x180CEDB7D..0x180CEDB81`, `418d43fc lea eax, [r11 - 4]; 894338 mov dword ptr [rbx + 0x38], eax`). |
| 5 | Al conectar (`Connect`), `_readKey` (`this+0x70`) y `_ready` (`this+0x18`) se ponen a `0` (`false`), y `BeReady` solo pasa a `true` cuando `mTcpState.state == 2` **y** `_readKey != 0`. | `CONFIRMADO` | `TypeDef[1823]`, `Connect` (`RVA 0xCEC7DF..0xCEC7EC`, `c6471800 mov byte ptr [rdi+0x18], 0; c6477000 mov byte ptr [rdi+0x70], 0` y `RVA 0xCECA55..0xCECA87`, `4183ff02 cmp r15d, 2; 7509 jne; 0fb67770 movzx esi, byte ptr [rdi+0x70] ... 40887718 mov byte ptr [rdi+0x18], sil`). |
| 6 | Cuando `_readKey == false`, la primera trama recibida del servidor se interpreta íntegramente como `byte[] keyBytes` (`rawLen - 4` bytes, sin `msgId`), instancia `this._rc4 = new Utils.RC4(keyBytes)` y activa `this._readKey = 1`. | `CONFIRMADO` | `TypeDef[1823]`, `ReceivePayload` (`RVA 0xCEDBDD..0xCEDD12`, `VA 0x180CEDBDD..0x180CEDD12`, `4084ff test dil, dil; 0f84d5000000 je 0x180cedcbb` $\rightarrow$ `e8963e0100 call 0x180d01b90; 48897378 mov [rbx+0x78], rsi; c6437001 mov byte ptr [rbx+0x70], 1`). |
| 7 | En paquetes salientes (Cliente $\rightarrow$ Servidor), `this._rc4.Crypt(_sendBuffer, 4, totalLen)` cifra desde el byte `4` hasta `totalLen` (`msgId` + payload), dejando `totalLen` (`0..3`) en texto plano. | `CONFIRMADO` | `TypeDef[1823]`, `Send_begin` (`RVA 0xCEE0F1..0xCEE10A`, `VA 0x180CEE0F1..0x180CEE10A`, `448bce mov r9d, esi; 41b804000000 mov r8d, 4; 488bd7 mov rdx, rdi; e841390100 call 0x180d01a50`) y `Send(msg_base)` (`RVA 0xCEE68D..0xCEE6A6`). |
| 8 | En paquetes entrantes (Servidor $\rightarrow$ Cliente, `_readKey == true`), el cliente NO aplica `Utils.RC4::Crypt` en `ReceivePayload` ni en `DealMessage`; viajan en texto plano. | `CONFIRMADO` | `TypeDef[1823]`, `ReceivePayload` (`RVA 0xCEDBE6..0xCEDCB9`) y `DealMessage` (`RVA 0xCED260..0xCED371`): lectura directa de `msgID` (`call 0x180ceede0`), `ReadBytes(lastMsgLength - 4)` y despacho a `NetMod` (`call 0x180d89cc0`, `call 0x180d82320`) sin llamadas a `0x180D01A50`. |
| 9 | `Utils.RC4::Crypt` reinicia los índices locales `i = 0, j = 0` en cada llamada, pero conserva la permutación mutada de `this.S[256]` entre llamadas sucesivas. | `CONFIRMADO` | `TypeDef[1830]`, `Crypt` (`RVA 0xD01A5A..0xD01AD7`, `VA 0x180D01A5A..0x180D01AD7`, `4533d2 xor r10d, r10d; 4533db xor r11d, r11d` al entrar, mutando `[rbx + 0x10]` en `0x180D01ACC..0x180D01AD7`). |
| 10 | Valor concreto de los bytes de `keyBytes` enviados por el servidor oficial en la Trama 0 (irrelevante para un servidor local propio, ya que el cliente acepta cualquier `keyBytes` de longitud $\ge 1$ que el servidor decida enviarle). | `DESCONOCIDO` | `Utils.RC4::.ctor` (`VA 0x180D01C31..0x180D01C38`) acepta cualquier `byte[]` con `Length >= 1` enviado por el servidor en la Trama 0. Para conocer el valor exacto que enviaba el servidor oficial se requeriría una captura de red autorizada de una sesión oficial, pero **no es necesario para la interoperabilidad con un servidor local**, pues el servidor define y envía la semilla en la Trama 0. |

---

## 7. Herramientas Utilizadas y Verificación de Integridad (`INTEGRITY_PRE` / `INTEGRITY_POST`)

### Herramientas y Scripts Ejecutados
* Python `3.x` con biblioteca estándar (`struct`, `hashlib`) y módulo `capstone` preinstalado (`CS_ARCH_X86`, `CS_MODE_64`). No se instaló ninguna herramienta ni paquete nuevo.
* Scripts de análisis estático (solo lectura, alojados en `scratch/`):
  - `scratch/exp3_pre_check.py`: cálculo de `INTEGRITY_PRE` y verificación de disponibilidad de `capstone`.
  - `scratch/locate_codegen_modules.py`: localización de `Il2CppCodeGenModule` para `Assembly-CSharp.dll` (`VA 0x183651140`, tabla `methodPointers` de 33.183 punteros en `VA 0x183FD0960`).
  - `scratch/disasm_tcpclient_rc4.py` y `scratch/disasm_remaining_ranges.py`: desensamblado completo de `Utils.RC4` (`TypeDef[1830]`), `Utils.TcpClient` (`TypeDef[1823]`) y cálculo de `INTEGRITY_POST`.

### Tabla de Integridad (`SHA-256`)

| Archivo | Tamaño (Bytes) | `INTEGRITY_PRE` (SHA-256) | `INTEGRITY_POST` (SHA-256) | Estado |
|---|---|---|---|---|
| `D:\secret\P5X\client\pc\GameAssembly.dll` | `73,860,704` | `A052B4539D71603BF7ADAB1EA4A0DEFB06E7B979AEEE84EB60C8151B78BDC148` | `A052B4539D71603BF7ADAB1EA4A0DEFB06E7B979AEEE84EB60C8151B78BDC148` | **IDÉNTICO (`OK`)** |
| `D:\secret\P5X\client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat` | `17,648,664` | `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B` | `9A7BE76368FA7ABE78476AB8F7E63D82216D34F49832D4A1A350784ADECE153B` | **IDÉNTICO (`OK`)** |
