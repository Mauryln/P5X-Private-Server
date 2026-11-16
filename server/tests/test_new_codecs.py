import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from proto2_codec import (
    encode_tag,
    encode_varint,
    encode_varint_field,
    encode_bool_field,
    encode_bytes_field,
    encode_string_field,
    decode_wire_fields,
    to_signed32,
    to_signed64
)

def decode_DVector3(payload: bytes):
    fields = decode_wire_fields(payload)
    x, y, z = 0.0, 0.0, 0.0
    for fn, wt, val in fields:
        if wt == 5:
            fval = struct.unpack('<f', struct.pack('<I', val))[0]
            if fn == 1: x = fval
            elif fn == 2: y = fval
            elif fn == 3: z = fval
    return {"x": round(x, 4), "y": round(y, 4), "z": round(z, 4)}

def decode_CSSceneMoveStop(payload: bytes):
    fields = decode_wire_fields(payload)
    res = {"sendId": None, "posEnd": None, "marker": None}
    for fn, wt, val in fields:
        if fn == 1 and wt == 0:
            res["sendId"] = to_signed64(val)
        elif fn == 2 and wt == 2:
            res["posEnd"] = decode_DVector3(val)
        elif fn == 3 and wt == 0:
            res["marker"] = to_signed32(val)
    return res

def decode_CSSceneMove(payload: bytes):
    fields = decode_wire_fields(payload)
    res = {
        "objId": None,
        "posBegin": None,
        "posEnd": [],
        "dir": None,
        "speedGear": None,
        "moveSpeed": None
    }
    for fn, wt, val in fields:
        if fn == 1 and wt == 0:
            res["objId"] = to_signed64(val)
        elif fn == 2 and wt == 2:
            res["posBegin"] = decode_DVector3(val)
        elif fn == 3 and wt == 2:
            res["posEnd"].append(decode_DVector3(val))
        elif fn == 4 and wt == 2:
            # DVector2
            f2 = decode_wire_fields(val)
            vx, vy = 0.0, 0.0
            for f2n, f2wt, f2v in f2:
                if f2wt == 5:
                    fv = struct.unpack('<f', struct.pack('<I', f2v))[0]
                    if f2n == 1: vx = fv
                    elif f2n == 2: vy = fv
            res["dir"] = {"x": round(vx, 4), "y": round(vy, 4)}
        elif fn == 5 and wt == 0:
            res["speedGear"] = to_signed32(val)
        elif fn == 6 and wt == 5:
            res["moveSpeed"] = round(struct.unpack('<f', struct.pack('<I', val))[0], 4)
    return res

def decode_CSDialogFinish(payload: bytes):
    fields = decode_wire_fields(payload)
    res = {"dialogSn": "", "crucial": False}
    for fn, wt, val in fields:
        if fn == 1 and wt == 2:
            res["dialogSn"] = val.decode("utf-8", errors="replace")
        elif fn == 2 and wt == 0:
            res["crucial"] = (val != 0)
    return res

def decode_CSDialogChoice(payload: bytes):
    fields = decode_wire_fields(payload)
    res = {"dialogSn": "", "choice": 0}
    for fn, wt, val in fields:
        if fn == 1 and wt == 2:
            res["dialogSn"] = val.decode("utf-8", errors="replace")
        elif fn == 2 and wt == 0:
            res["choice"] = to_signed32(val)
    return res

def decode_CSQuestDialog(payload: bytes):
    fields = decode_wire_fields(payload)
    res = {"dialogSn": ""}
    for fn, wt, val in fields:
        if fn == 1 and wt == 2:
            res["dialogSn"] = val.decode("utf-8", errors="replace")
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

def encode_SCFightRoundBattleSkill(play_id: int, opttype: int = 1, atk_id: int = 1001, skill_res: bytes = None) -> bytes:
    buf = bytearray()
    buf += encode_varint_field(24, play_id)  # required
    buf += encode_varint_field(1, opttype)
    buf += encode_varint_field(2, atk_id)
    if skill_res:
        buf += encode_bytes_field(3, skill_res)
    return bytes(buf)

print("Test encode SCQuestInfo (empty):", encode_SCQuestInfo().hex())
q1 = encode_DQuest(sn=1001, state=1, new_line=True)
print("Test encode DQuest 1001:", q1.hex())
print("Test encode SCQuestInfo with 1001:", encode_SCQuestInfo(quests=[q1]).hex())
sres = encode_DRoundSkillResult(skillsn=1101, main_target_id=2001)
fskill = encode_SCFightRoundBattleSkill(play_id=1, skill_res=sres)
print("Test encode SCFightRoundBattleSkill:", fskill.hex())
