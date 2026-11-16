"""
Proto2 Wire Codec + Utils.TcpClient / Utils.RC4 Framing for P5X Local PoC Server.
Strictly implements the wire specification from docs/TRANSPORT_WIRE_SPEC.md
and the exact Proto2 schema from docs/msg.proto (allMsgPb.bytes).
"""
import struct
from typing import Any, Dict, List, Optional, Tuple



class RC4:
    """Bit-exact implementation of Utils.RC4 (TypeDef[1830], VA 0x180D01A50 / 0x180D01B90)."""

    def __init__(self, key: bytes):
        self.S = list(range(256))
        j = 0
        klen = len(key)
        for i in range(256):
            j = (j + self.S[i] + key[i % klen]) & 0xFF
            self.S[i], self.S[j] = self.S[j], self.S[i]
        self.x = 0
        self.y = 0

    def crypt_in_place(self, buf: bytearray, start: int, end: int) -> None:
        """
        Matches Utils.RC4::Crypt(byte[] buffer, int start, int end) at VA 0x180D01A50:
        Encrypts/decrypts buffer[start : end] (end is exclusive, i.e., while start < end).
        """
        S = self.S
        x = self.x
        y = self.y
        for idx in range(start, end):
            x = (x + 1) & 0xFF
            sx = S[x]
            y = (y + sx) & 0xFF
            sy = S[y]
            S[x] = sy
            S[y] = sx
            buf[idx] ^= S[(sx + sy) & 0xFF]
        self.x = x
        self.y = y


# --- Proto2 Wire Primitives ---

def encode_varint(val: int) -> bytes:
    """Encode signed/unsigned integer as 64-bit two's complement Protobuf varint."""
    if val < 0:
        val += (1 << 64)
    out = bytearray()
    while True:
        b = val & 0x7F
        val >>= 7
        if val:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def decode_varint(buf: bytes, pos: int) -> Tuple[int, int]:
    val = 0
    shift = 0
    while True:
        if pos >= len(buf):
            raise ValueError("Truncated varint")
        b = buf[pos]
        pos += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return val, pos


def to_signed32(val: int) -> int:
    val &= 0xFFFFFFFF
    return val - 0x100000000 if (val & 0x80000000) else val


def to_signed64(val: int) -> int:
    val &= 0xFFFFFFFFFFFFFFFF
    return val - 0x10000000000000000 if (val & 0x8000000000000000) else val


def encode_tag(field_num: int, wire_type: int) -> bytes:
    return encode_varint((field_num << 3) | wire_type)


def encode_varint_field(field_num: int, val: int) -> bytes:
    return encode_tag(field_num, 0) + encode_varint(val)


def encode_bool_field(field_num: int, val: bool) -> bytes:
    return encode_tag(field_num, 0) + (b"\x01" if val else b"\x00")


def encode_bytes_field(field_num: int, data: bytes) -> bytes:
    return encode_tag(field_num, 2) + encode_varint(len(data)) + data


def encode_string_field(field_num: int, text: str) -> bytes:
    raw = text.encode("utf-8")
    return encode_bytes_field(field_num, raw)


def decode_wire_fields(buf: bytes) -> List[Tuple[int, int, Any]]:
    """Generic Proto2 wire parser returning list of (field_number, wire_type, raw_value)."""
    pos = 0
    fields = []
    n = len(buf)
    while pos < n:
        tag, pos = decode_varint(buf, pos)
        field_num = tag >> 3
        wire_type = tag & 0x07
        if field_num == 0:
            raise ValueError("Invalid field_number 0")
        if wire_type == 0:  # varint
            val, pos = decode_varint(buf, pos)
            fields.append((field_num, wire_type, val))
        elif wire_type == 1:  # 64-bit
            if pos + 8 > n:
                raise ValueError("Truncated fixed64")
            val = struct.unpack_from("<Q", buf, pos)[0]
            pos += 8
            fields.append((field_num, wire_type, val))
        elif wire_type == 2:  # length-delimited
            length, pos = decode_varint(buf, pos)
            if pos + length > n:
                raise ValueError("Truncated length-delimited field")
            val = buf[pos : pos + length]
            pos += length
            fields.append((field_num, wire_type, val))
        elif wire_type == 5:  # 32-bit
            if pos + 4 > n:
                raise ValueError("Truncated fixed32")
            val = struct.unpack_from("<I", buf, pos)[0]
            pos += 4
            fields.append((field_num, wire_type, val))
        else:
            raise ValueError(f"Unsupported wire_type {wire_type}")
    return fields


# --- Message Decoders (Client -> Server, matching allMsgPb.bytes) ---

def decode_DPhone(buf: bytes) -> Dict[str, Any]:
    """
    message DPhone:
      1:deviceId(string), 2:deviceModel(string), 3:deviceSys(string),
      4:deviceRam(string), 5:mac(string), 6:idfa(string), 7:os(int32), 8:language(string)
    """
    str_fields = {
        1: "deviceId",
        2: "deviceModel",
        3: "deviceSys",
        4: "deviceRam",
        5: "mac",
        6: "idfa",
        8: "language",
    }
    out: Dict[str, Any] = {}
    for fnum, wtype, val in decode_wire_fields(buf):
        if fnum in str_fields and wtype == 2:
            out[str_fields[fnum]] = val.decode("utf-8", errors="replace")
        elif fnum == 7 and wtype == 0:
            out["os"] = to_signed32(val)
    return out


def decode_CSLogin(buf: bytes) -> Dict[str, Any]:
    """
    message CSLogin (MsgID 101):
      1:account(string), 2:password(string), 3:token(string), 4:channelId(string),
      5:mediaId(string), 6:version(string), 7:resVersion(int32), 8:phoneInfo(.DPhone),
      9:sdkType(int32), 10:serverUUID(int32), 11:channelPlatform(string)
    """
    str_fields = {
        1: "account",
        2: "password",
        3: "token",
        4: "channelId",
        5: "mediaId",
        6: "version",
        11: "channelPlatform",
    }
    int_fields = {
        7: "resVersion",
        9: "sdkType",
        10: "serverUUID",
    }
    out: Dict[str, Any] = {}
    for fnum, wtype, val in decode_wire_fields(buf):
        if fnum in str_fields and wtype == 2:
            out[str_fields[fnum]] = val.decode("utf-8", errors="replace")
        elif fnum in int_fields and wtype == 0:
            out[int_fields[fnum]] = to_signed32(val)
        elif fnum == 8 and wtype == 2:
            out["phoneInfo"] = decode_DPhone(val)
    return out


def decode_CSLoginGate(buf: bytes) -> Dict[str, Any]:
    """
    message CSLoginGate (MsgID 103):
      1:account(string), 2:sessionId(int64), 3:token(string), 4:phoneInfo(.DPhone),
      5:sdkType(int32), 6:serverUUID(int32), 7:channelPlatform(string),
      8:password(string), 9:steamId(string), 10:distinctId(string)
    """
    str_fields = {
        1: "account",
        3: "token",
        7: "channelPlatform",
        8: "password",
        9: "steamId",
        10: "distinctId",
    }
    out: Dict[str, Any] = {}
    for fnum, wtype, val in decode_wire_fields(buf):
        if fnum in str_fields and wtype == 2:
            out[str_fields[fnum]] = val.decode("utf-8", errors="replace")
        elif fnum == 2 and wtype == 0:
            out["sessionId"] = to_signed64(val)
        elif fnum == 4 and wtype == 2:
            out["phoneInfo"] = decode_DPhone(val)
        elif fnum == 5 and wtype == 0:
            out["sdkType"] = to_signed32(val)
        elif fnum == 6 and wtype == 0:
            out["serverUUID"] = to_signed32(val)
    return out


def decode_CSQueryCharacters(buf: bytes) -> Dict[str, Any]:
    """message CSQueryCharacters (MsgID 1001) - empty message."""
    decode_wire_fields(buf)
    return {}


def decode_CSCharacterLogin(buf: bytes) -> Dict[str, Any]:
    """
    message CSCharacterLogin (MsgID 1007):
      required int64 humanId = 1;
      optional int32 age = 2;
      optional bool adult = 3;
    """
    out: Dict[str, Any] = {}
    for fnum, wtype, val in decode_wire_fields(buf):
        if fnum == 1 and wtype == 0:
            out["humanId"] = to_signed64(val)
        elif fnum == 2 and wtype == 0:
            out["age"] = to_signed32(val)
        elif fnum == 3 and wtype == 0:
            out["adult"] = bool(val)
    if "humanId" not in out:
        raise ValueError("CSCharacterLogin missing required field humanId = 1")
    return out


# --- Message Encoders (Server -> Client, strict Proto2 required semantics) ---

def encode_SCLoginResult(
    resultCode: int = 1,
    account: str = "preserve_local",
    zoneTime: Optional[int] = None,
    serverId: int = 1,
    gameAddress: str = "127.0.0.1:18100",
    sessionId: int = 100001,
    timeout: int = 30,
    prepareReconnection: bool = False,
    isNeedUpdate: bool = False,
    revision: str = "13965237",
) -> bytes:
    """
    message SCLoginResult (MsgID 102):
      required int32 resultCode = 1;
      optional string account = 2;
      optional int32 zoneTime = 3;
      optional int32 serverId = 4;
      optional string gameAddress = 5;
      optional int64 sessionId = 6;
      optional int32 timeout = 7;
      required bool prepareReconnection = 8;
      required bool isNeedUpdate = 9;
      optional string failText = 10;
      optional string revision = 11;
    """
    parts = [
        encode_varint_field(1, resultCode),           # required int32 resultCode = 1
        encode_string_field(2, account),              # optional string account = 2
    ]
    if zoneTime is not None:
        parts.append(encode_varint_field(3, zoneTime))  # optional int32 zoneTime = 3
    parts.extend([
        encode_varint_field(4, serverId),             # optional int32 serverId = 4
        encode_string_field(5, gameAddress),          # optional string gameAddress = 5
        encode_varint_field(6, sessionId),            # optional int64 sessionId = 6
        encode_varint_field(7, timeout),              # optional int32 timeout = 7
        encode_bool_field(8, prepareReconnection),    # required bool prepareReconnection = 8
        encode_bool_field(9, isNeedUpdate),           # required bool isNeedUpdate = 9
        encode_string_field(11, revision),            # optional string revision = 11
    ])
    return b"".join(parts)


def encode_SCServerTime(serverTime: int = 1700000000000) -> bytes:
    """
    message SCServerTime (MsgID 1136):
      required int64 serverTime = 1; # in milliseconds
    """
    return encode_varint_field(1, serverTime)



def encode_SCLoginGateResult(errorCode: int = 0) -> bytes:
    """
    message SCLoginGateResult (MsgID 104):
      required int32 errorCode = 1;
    """
    return encode_varint_field(1, errorCode)


def encode_SCServerConfig(
    isClientBattle: bool = False,
    openGM: bool = False,
    timeNow: int = 1700000000,
    baseTime: int = 1700000000,
    timeZone: int = 28800,
) -> bytes:
    """
    message SCServerConfig (MsgID 1112):
      required bool isClientBattle = 1;
      required bool openGM = 2;
      required int64 timeNow = 3;
      required int64 baseTime = 4;
      optional int32 timeZone = 5;
    """
    return b"".join([
        encode_bool_field(1, isClientBattle),
        encode_bool_field(2, openGM),
        encode_varint_field(3, timeNow),
        encode_varint_field(4, baseTime),
        encode_varint_field(5, timeZone),
    ])


def encode_DCharacter(
    char_id: int = 10001,
    name: str = "Wonder",
    profession: int = 1,
    level: int = 1,
    sex: int = 1,
    model: str = "wonder_uniform",
    sn: int = 1001,
) -> bytes:
    """
    message DCharacter:
      required int64 id = 1;
      optional string name = 2;
      optional int32 profession = 3;
      optional int32 level = 4;
      optional int32 sex = 5;
      optional string model = 6;
      optional int32 sn = 11;
    """
    fields = [
        encode_varint_field(1, char_id),
        encode_string_field(2, name),
        encode_varint_field(3, profession),
        encode_varint_field(4, level),
        encode_varint_field(5, sex),
    ]
    if model:
        fields.append(encode_string_field(6, model))
    if sn:
        fields.append(encode_varint_field(11, sn))
    return b"".join(fields)


def encode_SCQueryCharactersResult(characters: List[bytes]) -> bytes:
    """
    message SCQueryCharactersResult (MsgID 1002):
      repeated DCharacter characters = 1;
    """
    return b"".join(encode_bytes_field(1, ch) for ch in characters)


def encode_SCCharacterLoginResult(resultCode: int = 0, loginType: int = 1) -> bytes:
    """
    message SCCharacterLoginResult (MsgID 1008):
      required int32 resultCode = 1;
      optional ELoginType loginType = 2;
    """
    return b"".join([
        encode_varint_field(1, resultCode),
        encode_varint_field(2, loginType),
    ])


# --- Scene & Heartbeat Codecs (Fase 2.3) ---

def encode_DVector3(x: float = 0.0, y: float = 0.0, z: float = 0.0) -> bytes:
    """message DVector3: 1:x(float), 2:y(float), 3:z(float)."""
    return b"".join([
        encode_tag(1, 5) + struct.pack("<f", x),
        encode_tag(2, 5) + struct.pack("<f", y),
        encode_tag(3, 5) + struct.pack("<f", z),
    ])


def encode_DVector2(x: float = 0.0, y: float = 1.0) -> bytes:
    """message DVector2: 1:x(float), 2:y(float)."""
    return b"".join([
        encode_tag(1, 5) + struct.pack("<f", x),
        encode_tag(2, 5) + struct.pack("<f", y),
    ])


def encode_DInitScene(
    pos_now: Any = None,
    dir_now: Any = None,
    scene_id: int = 2102,
    sn: int = 2102,
    instance_sn: int = 0,
    line_num: int = 1,
) -> bytes:
    """
    message DInitScene:
      1:posNow(DVector3), 2:id(int64), 3:sn(int32), 4:instanceSn(int32),
      5:lineNum(int32), 10:dirNow(DVector2).
    """
    if pos_now is None:
        pos_now = encode_DVector3(339.0956, 203.1076, 99.5553)
    if dir_now is None:
        dir_now = encode_DVector2(0.0, 1.0)
    return b"".join([
        encode_bytes_field(1, pos_now),
        encode_varint_field(2, scene_id),
        encode_varint_field(3, sn),
        encode_varint_field(4, instance_sn),
        encode_varint_field(5, line_num),
        encode_bytes_field(10, dir_now),
    ])


def encode_DHuman(
    human_id: int = 10001,
    name: str = "Wonder",
    level: int = 1,
    sex: int = 1,
    hp: int = 100,
    sp: int = 100,
    model_sn: str = "wonder_uniform",
    sn: int = 1001,
    user_id: int = 100001,
    create_time: int = 1700000000000,
) -> bytes:
    """
    message DHuman:
      1:id(int64), 3:name(string), 4:level(int32), 5:sex(int32),
      6:hpCur(int32), 7:spCur(int32), 9:modelSn(string), 11:sn(int32),
      12:userId(int64), 18:createTime(int64).
    """
    fields = [
        encode_varint_field(1, human_id),
        encode_string_field(3, name),
        encode_varint_field(4, level),
        encode_varint_field(5, sex),
        encode_varint_field(6, hp),
        encode_varint_field(7, sp),
    ]
    if model_sn:
        fields.append(encode_string_field(9, model_sn))
    if sn:
        fields.append(encode_varint_field(11, sn))
    fields.append(encode_varint_field(12, user_id))
    if create_time:
        fields.append(encode_varint_field(18, create_time))
    return b"".join(fields)


def encode_DBasic(b_auto: bool = False, b_enter_safe_room: bool = False) -> bytes:
    """message DBasic: 1:bAuto(bool), 5:bEnterSafeRoom(bool)."""
    return b"".join([
        encode_bool_field(1, b_auto),
        encode_bool_field(5, b_enter_safe_room),
    ])


def encode_DOpenWorld(
    period_sn: int = 1, day_sn: int = 1, day_count: int = 1, phase_type: int = 1
) -> bytes:
    """message DOpenWorld: 1:periodSn(int32), 2:daySn(int32), 3:dayCount(int32), 4:phaseType(int32)."""
    return b"".join([
        encode_varint_field(1, period_sn),
        encode_varint_field(2, day_sn),
        encode_varint_field(3, day_count),
        encode_varint_field(4, phase_type),
    ])


def encode_SCInitData(
    human: Any = None,
    scene: Any = None,
    basic: Any = None,
    open_world: Any = None,
) -> bytes:
    """
    message SCInitData (MsgID 1102):
      1:human(DHuman), 2:scene(DInitScene), 8:openWorld(DOpenWorld), 9:basic(DBasic).
    """
    parts = []
    if human is not None:
        parts.append(encode_bytes_field(1, human))
    if scene is not None:
        parts.append(encode_bytes_field(2, scene))
    if open_world is not None:
        parts.append(encode_bytes_field(8, open_world))
    if basic is not None:
        parts.append(encode_bytes_field(9, basic))
    return b"".join(parts)


def decode_CSSceneEnter(buf: bytes) -> Dict[str, Any]:
    """message CSSceneEnter (MsgID 1201) - empty signaling message."""
    decode_wire_fields(buf)
    return {}


def encode_SCSceneEnterResult(
    obj_list: Any = None,
    tar_human_id: int = 10001,
    union_station_id: Any = None,
) -> bytes:
    """
    message SCSceneEnterResult (MsgID 1202):
      1:obj(repeated DSceneObject), 2:tarHumanId(int64), 3:unionStationUnionId(int64).
    """
    parts = []
    if obj_list:
        for obj in obj_list:
            parts.append(encode_bytes_field(1, obj))
    parts.append(encode_varint_field(2, tar_human_id))
    if union_station_id is not None:
        parts.append(encode_varint_field(3, union_station_id))
    return b"".join(parts)


def encode_SCSceneEnterEnd(
    seek_list: Any = None,
    produces_list: Any = None,
) -> bytes:
    """
    message SCSceneEnterEnd (MsgID 1203):
      1:seek(repeated int32), 2:produces(repeated DProduce).
    """
    parts = []
    if seek_list:
        for s in seek_list:
            parts.append(encode_varint_field(1, s))
    if produces_list:
        for p in produces_list:
            parts.append(encode_bytes_field(2, p))
    return b"".join(parts)


def decode_CSPing(buf: bytes) -> Dict[str, Any]:
    """
    message CSPing (MsgID 1116):
      1:clientTimeStamp(float).
    """
    out: Dict[str, Any] = {}
    for fnum, wtype, val in decode_wire_fields(buf):
        if fnum == 1 and wtype == 5:
            out["clientTimeStamp"] = struct.unpack("<f", struct.pack("<I", val))[0]
    return out


def encode_SCPing(clientTimeStamp: float = 0.0) -> bytes:
    """
    message SCPing (MsgID 1117):
      1:clientTimeStamp(float).
    """
    return encode_tag(1, 5) + struct.pack("<f", clientTimeStamp)


def decode_CSNetDelayDetect(buf: bytes) -> Dict[str, Any]:
    """
    message CSNetDelayDetect (MsgID 1118):
      1:clientTimeStamp(float).
    """
    out: Dict[str, Any] = {}
    for fnum, wtype, val in decode_wire_fields(buf):
        if fnum == 1 and wtype == 5:
            out["clientTimeStamp"] = struct.unpack("<f", struct.pack("<I", val))[0]
    return out


def encode_SCNetDelayDetect(clientTimeStamp: float = 0.0, serverTimeStamp: int = 0) -> bytes:
    """
    message SCNetDelayDetect (MsgID 1119):
      1:clientTimeStamp(float), 2:serverTimeStamp(int64).
    """
    return b"".join([
        encode_tag(1, 5) + struct.pack("<f", clientTimeStamp),
        encode_varint_field(2, serverTimeStamp),
    ])


# --- Wire Framing Helpers (Utils.TcpClient) ---

def make_trama0(key_bytes: bytes) -> bytes:
    """
    Trama 0 (Server -> Client):
      [0..3] totalLen = 4 + len(key_bytes) (Big-Endian int32)
      [4..totalLen-1] key_bytes (plaintext)
    """
    total_len = 4 + len(key_bytes)
    return struct.pack(">i", total_len) + key_bytes


def make_sc_frame(msg_id: int, payload: bytes) -> bytes:
    """
    Server -> Client Standard Frame (Plaintext):
      [0..3] totalLen = 8 + len(payload) (Big-Endian int32)
      [4..7] msgId (Big-Endian int32)
      [8..totalLen-1] payload (Plaintext Protobuf)
    """
    total_len = 8 + len(payload)
    return struct.pack(">ii", total_len, msg_id) + payload


def make_cs_frame(msg_id: int, payload: bytes, rc4: RC4) -> Tuple[bytes, bytes]:
    """
    Client -> Server Standard Frame (RC4 encrypted from byte 4 to totalLen):
      Returns (encrypted_wire_bytes, plaintext_wire_bytes).
    """
    total_len = 8 + len(payload)
    plain = bytearray(struct.pack(">ii", total_len, msg_id) + payload)
    enc = bytearray(plain)
    rc4.crypt_in_place(enc, 4, total_len)
    return bytes(enc), bytes(plain)


SENSITIVE_KEYS = {
    "account", "password", "token", "steamId", "deviceId", "mac", "idfa", "distinctId"
}


def obfuscate_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out[k] = obfuscate_dict(v)
        elif k in SENSITIVE_KEYS and isinstance(v, str) and v:
            out[k] = f"<REDACTED:{len(v)}B>"
        else:
            out[k] = v
    return out


# --- Phase 2: Movement, Interaction, Quest, Combat Codecs ---

def decode_DVector3_val(payload: bytes) -> Dict[str, float]:
    fields = decode_wire_fields(payload)
    x, y, z = 0.0, 0.0, 0.0
    for fn, wt, val in fields:
        if wt == 5:
            fval = struct.unpack("<f", struct.pack("<I", val))[0]
            if fn == 1:
                x = fval
            elif fn == 2:
                y = fval
            elif fn == 3:
                z = fval
    return {"x": round(x, 4), "y": round(y, 4), "z": round(z, 4)}


def decode_CSSceneMoveStop(payload: bytes) -> Dict[str, Any]:
    fields = decode_wire_fields(payload)
    res: Dict[str, Any] = {"sendId": None, "posEnd": None, "marker": None}
    for fn, wt, val in fields:
        if fn == 1 and wt == 0:
            res["sendId"] = to_signed64(val)
        elif fn == 2 and wt == 2:
            res["posEnd"] = decode_DVector3_val(val)
        elif fn == 3 and wt == 0:
            res["marker"] = to_signed32(val)
    return res


def decode_CSSceneMove(payload: bytes) -> Dict[str, Any]:
    fields = decode_wire_fields(payload)
    res: Dict[str, Any] = {
        "objId": None,
        "posBegin": None,
        "posEnd": [],
        "dir": None,
        "speedGear": None,
        "moveSpeed": None,
    }
    for fn, wt, val in fields:
        if fn == 1 and wt == 0:
            res["objId"] = to_signed64(val)
        elif fn == 2 and wt == 2:
            res["posBegin"] = decode_DVector3_val(val)
        elif fn == 3 and wt == 2:
            res["posEnd"].append(decode_DVector3_val(val))
        elif fn == 4 and wt == 2:
            f2 = decode_wire_fields(val)
            vx, vy = 0.0, 0.0
            for f2n, f2wt, f2v in f2:
                if f2wt == 5:
                    fv = struct.unpack("<f", struct.pack("<I", f2v))[0]
                    if f2n == 1:
                        vx = fv
                    elif f2n == 2:
                        vy = fv
            res["dir"] = {"x": round(vx, 4), "y": round(vy, 4)}
        elif fn == 5 and wt == 0:
            res["speedGear"] = to_signed32(val)
        elif fn == 6 and wt == 5:
            res["moveSpeed"] = round(struct.unpack("<f", struct.pack("<I", val))[0], 4)
    return res


def decode_CSDialogFinish(payload: bytes) -> Dict[str, Any]:
    fields = decode_wire_fields(payload)
    res = {"dialogSn": "", "crucial": False}
    for fn, wt, val in fields:
        if fn == 1 and wt == 2:
            res["dialogSn"] = val.decode("utf-8", errors="replace")
        elif fn == 2 and wt == 0:
            res["crucial"] = (val != 0)
    return res


def decode_CSDialogChoice(payload: bytes) -> Dict[str, Any]:
    fields = decode_wire_fields(payload)
    res = {"dialogSn": "", "choice": 0}
    for fn, wt, val in fields:
        if fn == 1 and wt == 2:
            res["dialogSn"] = val.decode("utf-8", errors="replace")
        elif fn == 2 and wt == 0:
            res["choice"] = to_signed32(val)
    return res


def decode_CSQuestDialog(payload: bytes) -> Dict[str, Any]:
    fields = decode_wire_fields(payload)
    res = {"dialogSn": ""}
    for fn, wt, val in fields:
        if fn == 1 and wt == 2:
            res["dialogSn"] = val.decode("utf-8", errors="replace")
    return res


def decode_CSRoundSkillList(payload: bytes) -> Dict[str, Any]:
    fields = decode_wire_fields(payload)
    res: Dict[str, Any] = {
        "curRound": None,
        "opttype": None,
        "atkId": None,
        "target": None,
        "skillsn": None,
        "personaSn": None,
        "qteScore": None,
        "isSpecialOpt": None,
    }
    for fn, wt, val in fields:
        if fn == 1 and wt == 0:
            res["curRound"] = to_signed32(val)
        elif fn == 2 and wt == 0:
            res["opttype"] = to_signed32(val)
        elif fn == 3 and wt == 0:
            res["atkId"] = to_signed64(val)
        elif fn == 4 and wt == 0:
            res["target"] = to_signed64(val)
        elif fn == 5 and wt == 0:
            res["skillsn"] = to_signed32(val)
        elif fn == 6 and wt == 0:
            res["personaSn"] = to_signed32(val)
        elif fn == 7 and wt == 5:
            res["qteScore"] = struct.unpack("<f", struct.pack("<I", val))[0]
        elif fn == 8 and wt == 0:
            res["isSpecialOpt"] = (val != 0)
    return res


def decode_CSRoundSetSkill(payload: bytes) -> Dict[str, Any]:
    fields = decode_wire_fields(payload)
    res: Dict[str, Any] = {"optId": None, "skillType": None, "skillsn": None}
    for fn, wt, val in fields:
        if fn == 1 and wt == 0:
            res["optId"] = to_signed64(val)
        elif fn == 2 and wt == 0:
            res["skillType"] = to_signed32(val)
        elif fn == 3 and wt == 0:
            res["skillsn"] = to_signed32(val)
    return res


def encode_DQuest(sn: int, state: int, new_line: bool = True, targets: list = None) -> bytes:
    buf = bytearray()
    buf += encode_varint_field(1, sn)
    buf += encode_varint_field(2, state)
    buf += encode_bool_field(8, new_line)
    if targets:
        for t in targets:
            tbuf = bytearray()
            tbuf += encode_varint_field(1, t.get("targetKey", 1))
            tbuf += encode_varint_field(2, t.get("targetCurValue", 0))
            tbuf += encode_bool_field(3, t.get("finish", False))
            buf += encode_bytes_field(3, bytes(tbuf))
    return bytes(buf)


def encode_SCQuestInfo(quests: list = None, submitted_sns: list = None, tracked_lines: list = None) -> bytes:
    buf = bytearray()
    if quests:
        for q in quests:
            buf += encode_bytes_field(1, q)
    if submitted_sns:
        for s in submitted_sns:
            buf += encode_varint_field(2, s)
    if tracked_lines:
        for tl in tracked_lines:
            buf += encode_varint_field(3, tl)
    return bytes(buf)


def encode_DRoundSkillResult(skillsn: int, main_target_id: int) -> bytes:
    buf = bytearray()
    buf += encode_varint_field(1, skillsn)
    buf += encode_varint_field(2, main_target_id)
    return bytes(buf)


def encode_SCFightRoundBattleSkill(
    play_id: int, opttype: int = 1, atk_id: int = 1001, skill_res: bytes = None
) -> bytes:
    buf = bytearray()
    buf += encode_varint_field(24, play_id)  # required
    buf += encode_varint_field(1, opttype)
    buf += encode_varint_field(2, atk_id)
    if skill_res:
        buf += encode_bytes_field(3, skill_res)
    return bytes(buf)


def decode_CSEnterFight(payload: bytes) -> Dict[str, Any]:
    res = {}
    for fn, wt, val in decode_wire_fields(payload):
        if fn == 1:
            res["instSn"] = val
        elif fn == 2:
            res["launchType"] = val
        elif fn == 3:
            if "monsters" not in res:
                res["monsters"] = []
            res["monsters"].append(val)
    return res


def decode_CSFightHumanPlayEnd(payload: bytes) -> Dict[str, Any]:
    res = {}
    for fn, wt, val in decode_wire_fields(payload):
        if fn == 1:
            res["round"] = val
        elif fn == 2:
            res["playId"] = val
    return res


def encode_SCFightRoundTime(
    left_time: int = 30, round_num: int = 1, little_round_player_id: int = 1001, play_id: int = 1
) -> bytes:
    buf = bytearray()
    buf += encode_varint_field(1, left_time)
    buf += encode_varint_field(2, round_num)
    buf += encode_varint_field(9, little_round_player_id)
    buf += encode_varint_field(17, play_id)  # required field in proto definition
    return bytes(buf)


def encode_SCFightRoundEnd(round_num: int = 1, play_id: int = 1, attack_round: int = 1) -> bytes:
    buf = bytearray()
    buf += encode_varint_field(1, round_num)
    buf += encode_varint_field(2, play_id)
    buf += encode_varint_field(3, attack_round)
    return bytes(buf)


def encode_SCFightBattleEnd(battle_result: int = 1, play_id: int = 1) -> bytes:
    buf = bytearray()
    buf += encode_varint_field(1, battle_result)
    buf += encode_varint_field(2, play_id)
    return bytes(buf)


def decode_CSWorldMonsterEnterBattle(payload: bytes) -> Dict[str, Any]:
    res = {}
    for fn, wt, val in decode_wire_fields(payload):
        if fn == 1:
            res["npcSn"] = val
    return res


def encode_SCWorldMonsterEnterBattle(npc_sn: int, demon_index: int = 0) -> bytes:
    buf = bytearray()
    buf += encode_varint_field(1, npc_sn)
    if demon_index:
        buf += encode_varint_field(2, demon_index)
    return bytes(buf)


def decode_CSQuestAutoEnterBattle(payload: bytes) -> Dict[str, Any]:
    res = {}
    for fn, wt, val in decode_wire_fields(payload):
        if fn == 1:
            res["questSn"] = val
        elif fn == 2:
            res["targetIndex"] = val
        elif fn == 3:
            res["battleSn"] = val
    return res


def encode_SCPlayDialog(sn: str, delay: int = 0) -> bytes:
    buf = bytearray()
    buf += encode_string_field(1, sn)
    if delay:
        buf += encode_varint_field(2, delay)
    return bytes(buf)


def encode_SCPlayTimeLine(timeline_sn: str) -> bytes:
    buf = bytearray()
    buf += encode_string_field(1, timeline_sn)
    return bytes(buf)


def encode_SCPlayScenario(sn: int, delay: int = 0) -> bytes:
    buf = bytearray()
    buf += encode_varint_field(1, sn)
    if delay:
        buf += encode_varint_field(2, delay)
    return bytes(buf)


def encode_SCFuncOpenSync(func_open_sns: list = None, new_open: bool = False) -> bytes:
    buf = bytearray()
    if func_open_sns is None:
        # Unlock all known functional systems
        func_open_sns = list(range(1, 301))
    for sn in func_open_sns:
        buf += encode_varint_field(1, sn)
    if new_open:
        buf += encode_bool_field(2, new_open)
    return bytes(buf)


def decode_CSScenarioFinish(payload: bytes) -> Dict[str, Any]:
    res = {}
    for fn, wt, val in decode_wire_fields(payload):
        if fn == 1:
            res["scenarioSn"] = val
    return res


def encode_SCScenarioHadPlay(sns: list) -> bytes:
    buf = bytearray()
    for s in sns:
        buf += encode_varint_field(1, s)
    return bytes(buf)


def decode_CSShopQuery(payload: bytes) -> Dict[str, Any]:
    res = {}
    for fn, wt, val in decode_wire_fields(payload):
        if fn == 1:
            res["shopSn"] = val
    return res


def encode_DShopItem(goods_sn: int = 1, stock_count: int = 99) -> bytes:
    buf = bytearray()
    buf += encode_varint_field(1, goods_sn)
    buf += encode_varint_field(2, stock_count)
    return bytes(buf)


def encode_SCShopQueryResult(shop_sn: int, d_items: list = None) -> bytes:
    buf = bytearray()
    buf += encode_varint_field(1, shop_sn)
    if d_items:
        for item in d_items:
            buf += encode_bytes_field(2, item)
    return bytes(buf)


def decode_CSSceneSwitch(payload: bytes) -> Dict[str, Any]:
    res = {}
    for fn, wt, val in decode_wire_fields(payload):
        if fn == 1:
            res["sceneSn"] = val
        elif fn == 2:
            res["sceneId"] = val
        elif fn == 3:
            res["telePortSn"] = val
    return res


def encode_SCSceneSwitch(scene_sn: int, scene_id: int = 0, pos: bytes = None, dir_vec: bytes = None) -> bytes:
    buf = bytearray()
    if scene_id:
        buf += encode_varint_field(1, scene_id)
    buf += encode_varint_field(2, scene_sn)
    if pos:
        buf += encode_bytes_field(4, pos)
    if dir_vec:
        buf += encode_bytes_field(12, dir_vec)
    return bytes(buf)



