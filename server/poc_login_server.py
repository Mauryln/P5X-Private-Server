"""
PoC Local TCP Login Server for P5X Preservation Study (Fase 2).
Bound strictly to 127.0.0.1.

Implements the 6-step handshake + login flow:
  1. Trama 0: send [int32 BE 4+K][keyBytes] -> client initializes Utils.RC4(keyBytes) & _readKey=true
  2. Receive CSLogin (101) -> send SCLoginResult (102) with gameAddress="127.0.0.1:<port>" and sessionId
  3. (On new TCP connection from OnTryConnectLogic or same socket):
     Send Trama 0 on new accept() -> Receive CSLoginGate (103) -> send SCLoginGateResult (104)
  4. Send SCServerConfig (1112) with isClientBattle=false, openGM=false, valid baseTime and timeNow
  5. Receive CSQueryCharacters (1001) -> send SCQueryCharactersResult (1002)
  6. Receive CSCharacterLogin (1007) -> send SCCharacterLoginResult (1008)
"""
import os
import socket
import struct
import sys
import threading
import time
from typing import Any, Dict, List, Optional

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

from proto2_codec import (
    RC4,
    encode_varint_field,
    encode_tag,
    decode_CSCharacterLogin,
    decode_CSLogin,
    decode_CSLoginGate,
    decode_CSNetDelayDetect,
    decode_CSPing,
    decode_CSQueryCharacters,
    decode_CSSceneEnter,
    decode_CSSceneMoveStop,
    decode_CSSceneMove,
    decode_CSDialogFinish,
    decode_CSDialogChoice,
    decode_CSQuestDialog,
    decode_CSRoundSkillList,
    decode_CSRoundSetSkill,
    decode_CSEnterFight,
    decode_CSFightHumanPlayEnd,
    decode_CSWorldMonsterEnterBattle,
    encode_SCWorldMonsterEnterBattle,
    decode_CSQuestAutoEnterBattle,
    encode_SCPlayDialog,
    encode_SCPlayTimeLine,
    encode_SCPlayScenario,
    encode_SCFuncOpenSync,
    decode_CSScenarioFinish,
    encode_SCScenarioHadPlay,
    decode_CSShopQuery,
    encode_DShopItem,
    encode_SCShopQueryResult,
    decode_CSSceneSwitch,
    encode_SCSceneSwitch,
    encode_DBasic,
    encode_DCharacter,
    encode_DHuman,
    encode_DInitScene,
    encode_DOpenWorld,
    encode_DVector2,
    encode_DVector3,
    encode_DQuest,
    encode_SCQuestInfo,
    encode_DRoundSkillResult,
    encode_SCFightRoundBattleSkill,
    encode_SCFightRoundTime,
    encode_SCFightRoundEnd,
    encode_SCFightBattleEnd,
    encode_SCCharacterLoginResult,
    encode_SCInitData,
    encode_SCLoginGateResult,
    encode_SCLoginResult,
    encode_SCNetDelayDetect,
    encode_SCPing,
    encode_SCQueryCharactersResult,
    encode_SCSceneEnterEnd,
    encode_SCSceneEnterResult,
    encode_SCServerConfig,
    encode_SCServerTime,
    make_sc_frame,

    make_trama0,
    obfuscate_dict,
)

MSG_NAMES = {
    101: "CSLogin",
    102: "SCLoginResult",
    103: "CSLoginGate",
    104: "SCLoginGateResult",
    105: "CSAccountReconnect",
    106: "SCAccountReconnectResult",
    127: "CSNotifySegaAccountBind",
    1112: "SCServerConfig",
    1136: "SCServerTime",
    1001: "CSQueryCharacters",

    1002: "SCQueryCharactersResult",
    1007: "CSCharacterLogin",
    1008: "SCCharacterLoginResult",
    1101: "CSInitData",
    1102: "SCInitData",
    1116: "CSPing",
    1117: "SCPing",
    1118: "CSNetDelayDetect",
    1119: "SCNetDelayDetect",
    1201: "CSSceneEnter",
    1202: "SCSceneEnterResult",
    1203: "SCSceneEnterEnd",
    1204: "CSSceneSwitch",
    1205: "SCSceneSwitch",
    1207: "CSSceneMove",
    1208: "SCSceneMove",
    1209: "CSSceneMoveStop",
    1210: "SCSceneMoveStop",
    1221: "CSChangeMoveType",
    1251: "CSAreaLogicInfoGet",
    1252: "SCAreaLogicInfoGet",
    1254: "CSAreaPositionSync",
    1261: "CSInfiltrationInfo",
    1262: "SCInfiltrationInfo",
    1302: "CSEnterFight",
    1325: "CSRoundSkillList",
    1326: "SCFightRoundTime",
    1327: "SCFightRoundBattleSkill",
    1330: "SCRoundSkillList",
    1331: "CSFightHumanPlayEnd",
    1332: "SCFightRoundEnd",
    1333: "SCFightBattleEnd",
    1337: "CSRoundSetSkill",
    1338: "SCRoundSetSkill",
    1418: "CSDialogFinish",
    1419: "CSGetCrucialDialog",
    1420: "SCGetCrucialDialogResult",
    1437: "CSDialogChoice",
    1467: "CSModifyAge",
    2001: "CSQuestAccept",
    2002: "SCQuestAcceptResult",
    2003: "CSQuestSubmit",
    2004: "SCQuestSubmitResult",
    2007: "SCQuestInfo",
    2008: "SCQuestInfoUpdate",
    2009: "CSQuestAutoEnterBattle",
    2020: "SCQuestAcceptable",
    2030: "CSQuestDialog",
    2101: "CSShopQuery",
    2102: "SCShopQueryResult",
    2501: "SCKeyBindInfo",
    2505: "CSKeyBindInfo",
    2801: "SCFuncOpenSync",
    4001: "SCScenarioHadPlay",
    4002: "CSScenarioFinish",
    15005: "CSWorldMonsterEnterBattle",
    15006: "SCWorldMonsterEnterBattle",
    4003: "CSSkipScenario",
    4011: "SCPlayScenario",
    4012: "SCPlayTimeLine",
    4013: "SCPlayDialog",
    127: "CSNotifySegaAccountBind",
    1112: "SCServerConfig",
    1136: "SCServerTime",
    1001: "CSQueryCharacters",

    1002: "SCQueryCharactersResult",
    1007: "CSCharacterLogin",
    1008: "SCCharacterLoginResult",
    1101: "CSInitData",
    1102: "SCInitData",
    1116: "CSPing",
    1117: "SCPing",
    1118: "CSNetDelayDetect",
    1119: "SCNetDelayDetect",
    1201: "CSSceneEnter",
    1202: "SCSceneEnterResult",
    1203: "SCSceneEnterEnd",
    1251: "CSAreaLogicInfoGet",
    1252: "SCAreaLogicInfoGet",
    1261: "CSInfiltrationInfo",
    1262: "SCInfiltrationInfo",
    1419: "CSGetCrucialDialog",
    1420: "SCGetCrucialDialogResult",
    1467: "CSModifyAge",
    2501: "SCKeyBindInfo",
    2505: "CSKeyBindInfo",
    4155: "CSReqAssistPoint",
    4156: "SCAssistPoint",
    7906: "CSGetAllUrbanNPC",
    7907: "SCGetAllUrbanNPC",
    7911: "CSNPCTouch",
    12901: "CSDayInfo",
    12902: "SCDayInfo",
    12904: "CSPersonAttrInfo",
    12905: "SCPersonAttrInfo",
    12912: "CSQueryTimeInfo",
    12913: "SCQueryTimeInfo",
    12916: "CSGetOWEventInfo",
    12917: "SCOWEventInfo",
    14467: "CSActivityDIYCakeQuery",
    14468: "SCActivityDIYCakeQuery",
    19003: "CSSeaHomeGetInfo",
    19004: "SCSeaHomeGetInfo",
    19101: "CSSeaFishingInfo",
    19102: "SCSeaFishingInfo",
    19501: "CSBingoBaseInfo",
    19502: "SCBingoBaseInfo",
    19703: "CSSandBoxGetAll",
    19704: "SCSandBoxGetAll",
    20101: "CSTwinsGachaponInfos",
    20102: "SCTwinsGachaponInfos",
}


def recv_exact(sock: socket.socket, n: int) -> Optional[bytes]:
    buf = bytearray()
    while len(buf) < n:
        try:
            chunk = sock.recv(n - len(buf))
        except OSError:
            return None
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)


class LocalPoCLoginServer:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 10403,
        rc4_key: bytes = b"P5XLocalKey2026!",
        fixed_epoch_sec: Optional[int] = None,
    ):
        if host != "127.0.0.1":
            raise ValueError("Security policy: Server MUST bind exclusively to 127.0.0.1")
        self.host = host
        self.port = port
        self.rc4_key = rc4_key
        self.fixed_epoch_sec = fixed_epoch_sec
        self.server_sock: Optional[socket.socket] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.frame_log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._conn_counter = 0

    def _log_frame(self, entry: Dict[str, Any]) -> None:
        with self._lock:
            entry["seq"] = len(self.frame_log) + 1
            self.frame_log.append(entry)
            try:
                import json
                log_path = os.environ.get(
                    "P5X_FRAME_LOG",
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "poc_frame_log.json"),
                )
                with open(log_path, "w", encoding="utf-8") as f:
                    json.dump(self.frame_log, f, indent=2)
            except Exception:
                pass
        direction = entry["direction"]
        conn_id = entry["conn_id"]
        msg_label = f"{entry['msg_id']} ({entry['msg_name']})"
        hdr_hex = entry["header_hex"]
        print(
            f"[SERVER][#{entry['seq']:02d}][Conn {conn_id}][{direction}] "
            f"msg={msg_label:<30} hdr={hdr_hex} "
            f"len={entry['total_len']} evidence={entry['evidence']}"
        )

    def start(self) -> int:
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.port = self.server_sock.getsockname()[1]
        self.server_sock.listen(5)
        self.running = True
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()
        return self.port

    def stop(self) -> None:
        self.running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except OSError:
                pass

    def _accept_loop(self) -> None:
        while self.running and self.server_sock:
            try:
                client_sock, addr = self.server_sock.accept()
            except OSError:
                break
            if addr[0] != "127.0.0.1":
                client_sock.close()
                continue
            with self._lock:
                self._conn_counter += 1
                conn_id = self._conn_counter
            t = threading.Thread(
                target=self._handle_client, args=(client_sock, conn_id), daemon=True
            )
            t.start()

    def _send_sc(
        self, sock: socket.socket, conn_id: int, msg_id: int, payload: bytes, decoded_info: Dict[str, Any]
    ) -> None:
        frame = make_sc_frame(msg_id, payload)
        self._log_frame({
            "conn_id": conn_id,
            "direction": "S -> C",
            "msg_id": msg_id,
            "msg_name": MSG_NAMES.get(msg_id, f"Msg_{msg_id}"),
            "total_len": len(frame),
            "header_hex": frame[:8].hex(" "),
            "header_decrypted_hex": frame[:8].hex(" "),
            "payload_wire_hex": payload.hex(" "),
            "payload_plain_hex": payload.hex(" "),
            "decoded": obfuscate_dict(decoded_info),
            "evidence": "CONFIRMADO",
        })
        sock.sendall(frame)

    def _send_initial_game_state(self, sock: socket.socket, conn_id: int, human_id: int, now_sec: int) -> None:
        human_bytes = encode_DHuman(
            human_id=human_id,
            name="Wonder",
            level=1,
            sex=1,
            hp=100,
            sp=100,
            model_sn="wonder_uniform",
            sn=1001,
            user_id=100001,
            create_time=1700000000000,
        )
        scene_bytes = encode_DInitScene(
            pos_now=encode_DVector3(339.0956, 203.1076, 99.5553),
            dir_now=encode_DVector2(0.0, 1.0),
            scene_id=2102,
            sn=2102,
            instance_sn=0,
            line_num=1,
        )
        basic_bytes = encode_DBasic(b_auto=False, b_enter_safe_room=False)
        ow_bytes = encode_DOpenWorld(period_sn=1, day_sn=1, day_count=1, phase_type=1)
        sc1102_bytes = encode_SCInitData(
            human=human_bytes,
            scene=scene_bytes,
            basic=basic_bytes,
            open_world=ow_bytes,
        )
        sc1102_fields = {
            "human": {
                "id": human_id,
                "name": "Wonder",
                "level": 1,
                "sex": 1,
                "hpCur": 100,
                "spCur": 100,
                "modelSn": "1001",
                "sn": 1001,
                "userId": 100001,
                "createTime": 1700000000000,
            },
            "scene": {"sn": 2102, "id": 2102, "posNow": {"x": 339.0956, "y": 203.1076, "z": 99.5553}},
            "basic": {"bAuto": False, "bEnterSafeRoom": False},
            "openWorld": {"periodSn": 1, "daySn": 1},
        }
        self._send_sc(sock, conn_id, 1102, sc1102_bytes, sc1102_fields)

        # Send SCQuestInfo (2007) with active initial mission
        dquest_bytes = encode_DQuest(
            sn=1001,
            state=1,
            new_line=True,
            targets=[{"targetKey": 1, "targetCurValue": 0, "finish": False}]
        )
        sc2007_payload = encode_SCQuestInfo(quests=[dquest_bytes], tracked_lines=[1])
        self._send_sc(sock, conn_id, 2007, sc2007_payload, {"quests": [{"sn": 1001, "state": 1}], "submittedQuestSns": [], "trackedLines": [1]})

        # Send SCFuncOpenSync (2801) to unlock all game features and HUD/menus
        sc2801_payload = encode_SCFuncOpenSync(func_open_sns=list(range(1, 301)), new_open=False)
        self._send_sc(sock, conn_id, 2801, sc2801_payload, {"funcOpenSnCount": 300, "newOpen": False})

        # Send SCServerTime (1136) to synchronize ServerTimeMgr
        sc1136_payload = encode_SCServerTime(serverTime=int(now_sec * 1000))
        self._send_sc(sock, conn_id, 1136, sc1136_payload, {"serverTime": int(now_sec * 1000)})


    def _handle_client(self, sock: socket.socket, conn_id: int) -> None:
        try:
            # Step 1: Send Trama 0 immediately on TCP accept()
            # Because Utils.TcpClient::Connect sets _readKey = false (VA 0x180CED319),
            # every new TCP connection requires Trama 0 as its first frame.
            trama0 = make_trama0(self.rc4_key)
            rc4_in = RC4(self.rc4_key)
            self._log_frame({
                "conn_id": conn_id,
                "direction": "S -> C",
                "msg_id": "TRAMA_0",
                "msg_name": "Handshake_RC4_Key",
                "total_len": len(trama0),
                "header_hex": trama0[:4].hex(" "),
                "header_decrypted_hex": trama0[:4].hex(" "),
                "payload_wire_hex": self.rc4_key.hex(" "),
                "payload_plain_hex": self.rc4_key.hex(" "),
                "decoded": {"key_len": len(self.rc4_key), "key_ascii": self.rc4_key.decode("ascii", errors="replace")},
                "evidence": "CONFIRMADO",
            })
            sock.sendall(trama0)

            while self.running:
                len_bytes = recv_exact(sock, 4)
                if not len_bytes:
                    break
                total_len = struct.unpack(">i", len_bytes)[0]
                if total_len < 8 or total_len > 65535:
                    break
                rem_enc = recv_exact(sock, total_len - 4)
                if not rem_enc:
                    break

                wire_frame = bytearray(len_bytes + rem_enc)
                plain_frame = bytearray(wire_frame)
                # Client -> Server encrypts [4..totalLen) with _rc4.Crypt(_sendBuffer, 4, totalLen)
                rc4_in.crypt_in_place(plain_frame, 4, total_len)

                msg_id = struct.unpack(">i", plain_frame[4:8])[0]
                payload_plain = bytes(plain_frame[8:total_len])
                payload_wire = bytes(wire_frame[8:total_len])

                now_sec = self.fixed_epoch_sec if self.fixed_epoch_sec is not None else int(time.time())
                now_ms = now_sec * 1000

                if msg_id == 101:
                    decoded = decode_CSLogin(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 101,
                        "msg_name": "CSLogin",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": obfuscate_dict(decoded),
                        "evidence": "CONFIRMADO",
                    })
                    # Respond SCLoginResult (102)
                    game_addr = f"127.0.0.1:{self.port}"
                    sc102_fields = {
                        "resultCode": 1,
                        "account": decoded.get("account", "preserve_local"),
                        "zoneTime": None,
                        "serverId": 1,
                        "gameAddress": game_addr,
                        "sessionId": 100001,
                        "timeout": 30,
                        "prepareReconnection": False,
                        "isNeedUpdate": False,
                        "revision": "13965237",
                    }

                    sc102_bytes = encode_SCLoginResult(**sc102_fields)
                    self._send_sc(sock, conn_id, 102, sc102_bytes, sc102_fields)

                elif msg_id == 103:
                    decoded = decode_CSLoginGate(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 103,
                        "msg_name": "CSLoginGate",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": obfuscate_dict(decoded),
                        "evidence": "CONFIRMADO",
                    })
                    # Respond SCLoginGateResult (104)
                    sc104_fields = {"errorCode": 0}
                    sc104_bytes = encode_SCLoginGateResult(**sc104_fields)
                    self._send_sc(sock, conn_id, 104, sc104_bytes, sc104_fields)

                    # Send SCServerConfig (1112) with openGM=True
                    sc1112_fields = {
                        "isClientBattle": False,
                        "openGM": True,
                        "timeNow": now_sec,
                        "baseTime": now_sec,
                        "timeZone": 28800,
                    }
                    sc1112_bytes = encode_SCServerConfig(**sc1112_fields)
                    self._send_sc(sock, conn_id, 1112, sc1112_bytes, sc1112_fields)

                    # Send SCServerTime (1136)
                    sc1136_payload = encode_SCServerTime(serverTime=int(now_sec * 1000))
                    self._send_sc(sock, conn_id, 1136, sc1136_payload, {"serverTime": int(now_sec * 1000)})


                elif msg_id == 105:
                    # CSAccountReconnect -> SCAccountReconnectResult (106)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 105,
                        "msg_name": "CSAccountReconnect",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    sc106_bytes = encode_varint_field(1, 0)
                    self._send_sc(sock, conn_id, 106, sc106_bytes, {"errorCode": 0})

                    # Also re-push SCServerConfig (1112) with openGM=True
                    sc1112_fields = {
                        "isClientBattle": False,
                        "openGM": True,
                        "timeNow": now_sec,
                        "baseTime": now_sec,
                        "timeZone": 28800,
                    }
                    sc1112_bytes = encode_SCServerConfig(**sc1112_fields)
                    self._send_sc(sock, conn_id, 1112, sc1112_bytes, sc1112_fields)

                    # Send SCServerTime (1136)
                    sc1136_payload = encode_SCServerTime(serverTime=int(now_sec * 1000))
                    self._send_sc(sock, conn_id, 1136, sc1136_payload, {"serverTime": int(now_sec * 1000)})


                elif msg_id == 1001:
                    decoded = decode_CSQueryCharacters(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1001,
                        "msg_name": "CSQueryCharacters",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded,
                        "evidence": "CONFIRMADO",
                    })
                    # Respond SCQueryCharactersResult (1002)
                    char_dict = {
                        "id": 10001,
                        "name": "Wonder",
                        "profession": 1,
                        "level": 1,
                        "sex": 1,
                        "model": "wonder_uniform",
                        "sn": 1001,
                    }
                    dchar_bytes = encode_DCharacter(
                        char_id=char_dict["id"],
                        name=char_dict["name"],
                        profession=char_dict["profession"],
                        level=char_dict["level"],
                        sex=char_dict["sex"],
                        model=char_dict["model"],
                        sn=char_dict["sn"],
                    )
                    sc1002_bytes = encode_SCQueryCharactersResult([dchar_bytes])
                    self._send_sc(
                        sock, conn_id, 1002, sc1002_bytes, {"characters": [char_dict]}
                    )

                elif msg_id == 1007:
                    decoded = decode_CSCharacterLogin(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1007,
                        "msg_name": "CSCharacterLogin",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded,
                        "evidence": "CONFIRMADO",
                    })
                    # Respond SCCharacterLoginResult (1008)
                    sc1008_fields = {"resultCode": 0, "loginType": 1}
                    sc1008_bytes = encode_SCCharacterLoginResult(**sc1008_fields)
                    self._send_sc(sock, conn_id, 1008, sc1008_bytes, sc1008_fields)

                    # Send full initial game state
                    self._send_initial_game_state(sock, conn_id, decoded.get("humanId", 10001), now_sec)

                elif msg_id == 1101:
                    # CSInitData -> re-send full initial game state upon reconnect or scene reset
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1101,
                        "msg_name": "CSInitData",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    self._send_initial_game_state(sock, conn_id, 10001, now_sec)

                elif msg_id == 1504:
                    # CSGetPrivateChatBuffer
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1504,
                        "msg_name": "CSGetPrivateChatBuffer",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })

                elif msg_id == 1610:
                    # CSItemRefresh
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1610,
                        "msg_name": "CSItemRefresh",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })

                elif msg_id == 13431:
                    # CSUnlockPersona -> SCUnlockPersona (13432)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 13431,
                        "msg_name": "CSUnlockPersona",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    self._send_sc(sock, conn_id, 13432, b"", {"personas": []})

                elif msg_id == 1201:
                    decoded = decode_CSSceneEnter(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1201,
                        "msg_name": "CSSceneEnter",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded,
                        "evidence": "CONFIRMADO",
                    })
                    # Respond SCSceneEnterResult (1202)
                    sc1202_fields = {"tarHumanId": 10001, "obj": []}
                    sc1202_bytes = encode_SCSceneEnterResult(obj_list=[], tar_human_id=10001)
                    self._send_sc(sock, conn_id, 1202, sc1202_bytes, sc1202_fields)

                    # Respond SCSceneEnterEnd (1203)
                    sc1203_fields = {"seek": [], "produces": []}
                    sc1203_bytes = encode_SCSceneEnterEnd(seek_list=[], produces_list=[])
                    self._send_sc(sock, conn_id, 1203, sc1203_bytes, sc1203_fields)

                elif msg_id == 1116:
                    decoded = decode_CSPing(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1116,
                        "msg_name": "CSPing",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded,
                        "evidence": "CONFIRMADO",
                    })
                    # Respond SCPing (1117)
                    client_ts = decoded.get("clientTimeStamp", 0.0)
                    sc1117_fields = {"clientTimeStamp": client_ts}
                    sc1117_bytes = encode_SCPing(clientTimeStamp=client_ts)
                    self._send_sc(sock, conn_id, 1117, sc1117_bytes, sc1117_fields)

                elif msg_id == 1118:
                    decoded = decode_CSNetDelayDetect(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1118,
                        "msg_name": "CSNetDelayDetect",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded,
                        "evidence": "CONFIRMADO",
                    })
                    client_ts = decoded.get("clientTimeStamp", 0.0)
                    sc1119_fields = {"clientTimeStamp": client_ts, "serverTimeStamp": now_ms}
                    sc1119_bytes = encode_SCNetDelayDetect(clientTimeStamp=client_ts, serverTimeStamp=now_ms)
                    self._send_sc(sock, conn_id, 1119, sc1119_bytes, sc1119_fields)

                elif msg_id == 1419:
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1419,
                        "msg_name": "CSGetCrucialDialog",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    # Respond SCGetCrucialDialogResult (1420)
                    sc1420_payload = b"\x0a\x00"
                    self._send_sc(sock, conn_id, 1420, sc1420_payload, {"crucialDialogs": ""})

                elif msg_id == 14467:
                    # CSActivityDIYCakeQuery -> SCActivityDIYCakeQuery (14468) [Weak Check target]
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 14467,
                        "msg_name": "CSActivityDIYCakeQuery",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    sc14468_payload = b"\x08\x00\x18\x00"
                    self._send_sc(sock, conn_id, 14468, sc14468_payload, {"error": 0, "activitySn": 0})

                elif msg_id == 7906:
                    # CSGetAllUrbanNPC -> SCGetAllUrbanNPC (7907)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 7906,
                        "msg_name": "CSGetAllUrbanNPC",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    sc7907_payload = b""
                    self._send_sc(sock, conn_id, 7907, sc7907_payload, {"urbanNpcs": []})

                elif msg_id == 12901:
                    # CSDayInfo -> SCDayInfo (12902)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 12901,
                        "msg_name": "CSDayInfo",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    sc12902_payload = b"\x08\x01\x10\x01\x20\x01\x28\x64"
                    self._send_sc(sock, conn_id, 12902, sc12902_payload, {"timeSn": 1, "day": 1, "weather": 1, "energyValue": 100})

                elif msg_id == 12904:
                    # CSPersonAttrInfo -> SCPersonAttrInfo (12905)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 12904,
                        "msg_name": "CSPersonAttrInfo",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    sc12905_payload = b"\x08\x01\x10\x01\x18\x01\x20\x01\x28\x01"
                    self._send_sc(sock, conn_id, 12905, sc12905_payload, {"personAttr1": 1, "personAttr2": 1, "personAttr3": 1, "personAttr4": 1, "personAttr5": 1})

                elif msg_id == 12916:
                    # CSGetOWEventInfo -> SCOWEventInfo (12917)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 12916,
                        "msg_name": "CSGetOWEventInfo",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    sc12917_payload = b""
                    self._send_sc(sock, conn_id, 12917, sc12917_payload, {"events": []})

                elif msg_id == 19703:
                    # CSSandBoxGetAll -> SCSandBoxGetAll (19704)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 19703,
                        "msg_name": "CSSandBoxGetAll",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    sc19704_payload = b"\x08\x00\x18\x00"
                    self._send_sc(sock, conn_id, 19704, sc19704_payload, {"error": 0, "velvetStar": 0})

                elif msg_id == 20101:
                    # CSTwinsGachaponInfos -> SCTwinsGachaponInfos (20102)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 20101,
                        "msg_name": "CSTwinsGachaponInfos",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    sc20102_payload = b""
                    self._send_sc(sock, conn_id, 20102, sc20102_payload, {"goals": []})

                elif msg_id == 2505:
                    # CSKeyBindInfo -> SCKeyBindInfo (2501)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 2505,
                        "msg_name": "CSKeyBindInfo",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    sc2501_payload = b""
                    self._send_sc(sock, conn_id, 2501, sc2501_payload, {"keyBinds": []})

                elif msg_id == 19501:
                    # CSBingoBaseInfo -> SCBingoBaseInfo (19502)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 19501,
                        "msg_name": "CSBingoBaseInfo",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    sc19502_payload = b"\x12\x04\x08\x00\x10\x00\x18\x00"
                    self._send_sc(sock, conn_id, 19502, sc19502_payload, {"base": {"layout": 0, "layoutAward": 0}, "activitySn": 0})

                elif msg_id == 1261:
                    # CSInfiltrationInfo -> SCInfiltrationInfo (1262)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1261,
                        "msg_name": "CSInfiltrationInfo",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    sc1262_payload = b"\x08\x00"
                    self._send_sc(sock, conn_id, 1262, sc1262_payload, {"settingItemSn": 0})

                elif msg_id == 1251:
                    # CSAreaLogicInfoGet -> SCAreaLogicInfoGet (1252)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1251,
                        "msg_name": "CSAreaLogicInfoGet",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    self._send_sc(sock, conn_id, 1252, b"", {"areaLogic": []})

                elif msg_id == 12912:
                    # CSQueryTimeInfo -> SCQueryTimeInfo (12913)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 12912,
                        "msg_name": "CSQueryTimeInfo",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    sc12913_payload = bytes.fromhex("08 01 10 01 20 01 28 01 30 01")
                    self._send_sc(sock, conn_id, 12913, sc12913_payload, {"periodSn": 1, "daySn": 1, "weather": 1, "dayCount": 1, "phaseType": 1})

                elif msg_id == 4155:
                    # CSReqAssistPoint -> SCAssistPoint (4156)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 4155,
                        "msg_name": "CSReqAssistPoint",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    sc4156_payload = bytes.fromhex("08 00 10 e8 07")
                    self._send_sc(sock, conn_id, 4156, sc4156_payload, {"assistPointToGet": 0, "assistPointToGetMax": 1000})

                elif msg_id == 19003:
                    # CSSeaHomeGetInfo -> SCSeaHomeGetInfo (19004)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 19003,
                        "msg_name": "CSSeaHomeGetInfo",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })
                    sc19004_payload = bytes.fromhex("08 00")
                    self._send_sc(sock, conn_id, 19004, sc19004_payload, {"error": 0})

                elif msg_id == 1209:
                    # CSSceneMoveStop
                    decoded_1209 = decode_CSSceneMoveStop(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1209,
                        "msg_name": "CSSceneMoveStop",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded_1209,
                        "evidence": "CONFIRMADO",
                    })

                elif msg_id == 1207:
                    # CSSceneMove
                    decoded_1207 = decode_CSSceneMove(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1207,
                        "msg_name": "CSSceneMove",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded_1207,
                        "evidence": "CONFIRMADO",
                    })

                elif msg_id == 1418:
                    # CSDialogFinish
                    decoded_1418 = decode_CSDialogFinish(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1418,
                        "msg_name": "CSDialogFinish",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded_1418,
                        "evidence": "CONFIRMADO",
                    })

                elif msg_id == 1437:
                    # CSDialogChoice
                    decoded_1437 = decode_CSDialogChoice(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1437,
                        "msg_name": "CSDialogChoice",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded_1437,
                        "evidence": "CONFIRMADO",
                    })

                elif msg_id == 2030:
                    # CSQuestDialog
                    decoded_2030 = decode_CSQuestDialog(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 2030,
                        "msg_name": "CSQuestDialog",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded_2030,
                        "evidence": "CONFIRMADO",
                    })

                elif msg_id == 1325:
                    # CSRoundSkillList -> SCRoundSkillList (1330) + SCFightRoundBattleSkill (1327)
                    decoded_1325 = decode_CSRoundSkillList(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1325,
                        "msg_name": "CSRoundSkillList",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded_1325,
                        "evidence": "CONFIRMADO",
                    })
                    sc1330_payload = bytes.fromhex("08 01")  # result = true
                    self._send_sc(sock, conn_id, 1330, sc1330_payload, {"result": True})
                    # Minimal combat response stub
                    sres = encode_DRoundSkillResult(
                        skillsn=decoded_1325.get("skillsn") or 1001,
                        main_target_id=decoded_1325.get("target") or 2001
                    )
                    sc1327_payload = encode_SCFightRoundBattleSkill(
                        play_id=1,
                        opttype=1,
                        atk_id=decoded_1325.get("atkId") or 1001,
                        skill_res=sres
                    )
                    self._send_sc(sock, conn_id, 1327, sc1327_payload, {"playId": 1, "opttype": 1, "atkId": 1001})

                elif msg_id == 1337:
                    # CSRoundSetSkill -> SCRoundSetSkill (1338)
                    decoded_1337 = decode_CSRoundSetSkill(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1337,
                        "msg_name": "CSRoundSetSkill",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded_1337,
                        "evidence": "CONFIRMADO",
                    })
                    sc1338_payload = bytes.fromhex("08 01")  # result = true
                    self._send_sc(sock, conn_id, 1338, sc1338_payload, {"result": True})

                elif msg_id == 1302:
                    # CSEnterFight -> respond with SCFightRoundTime (1326)
                    decoded_1302 = decode_CSEnterFight(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1302,
                        "msg_name": "CSEnterFight",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded_1302,
                        "evidence": "CONFIRMADO",
                    })
                    sc1326_payload = encode_SCFightRoundTime(left_time=30, round_num=1, little_round_player_id=1001)
                    self._send_sc(sock, conn_id, 1326, sc1326_payload, {"leftTime": 30, "round": 1, "littleRoundPlayerId": 1001})

                elif msg_id == 1331:
                    # CSFightHumanPlayEnd -> respond with SCFightRoundEnd (1332) + SCFightBattleEnd (1333)
                    decoded_1331 = decode_CSFightHumanPlayEnd(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1331,
                        "msg_name": "CSFightHumanPlayEnd",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded_1331,
                        "evidence": "CONFIRMADO",
                    })
                    play_id = decoded_1331.get("playId", 1)
                    round_num = decoded_1331.get("round", 1)
                    sc1332_payload = encode_SCFightRoundEnd(round_num=round_num, play_id=play_id)
                    self._send_sc(sock, conn_id, 1332, sc1332_payload, {"round": round_num, "playId": play_id})
                    sc1333_payload = encode_SCFightBattleEnd(battle_result=1, play_id=play_id)
                    self._send_sc(sock, conn_id, 1333, sc1333_payload, {"battleResult": 1, "playId": play_id})

                elif msg_id == 15005:
                    # CSWorldMonsterEnterBattle -> respond with SCWorldMonsterEnterBattle (15006) + SCFightRoundTime (1326)
                    decoded_15005 = decode_CSWorldMonsterEnterBattle(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 15005,
                        "msg_name": "CSWorldMonsterEnterBattle",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded_15005,
                        "evidence": "CONFIRMADO",
                    })
                    npc_sn = decoded_15005.get("npcSn", 1)
                    sc15006_payload = encode_SCWorldMonsterEnterBattle(npc_sn=npc_sn, demon_index=1)
                    self._send_sc(sock, conn_id, 15006, sc15006_payload, {"npcSn": npc_sn, "demonIndex": 1})
                    sc1326_payload = encode_SCFightRoundTime(left_time=30, round_num=1, little_round_player_id=1001, play_id=1)
                    self._send_sc(sock, conn_id, 1326, sc1326_payload, {"leftTime": 30, "round": 1, "littleRoundPlayerId": 1001, "playId": 1})

                elif msg_id == 2009:
                    # CSQuestAutoEnterBattle -> respond with SCFightRoundTime (1326)
                    decoded_2009 = decode_CSQuestAutoEnterBattle(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 2009,
                        "msg_name": "CSQuestAutoEnterBattle",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded_2009,
                        "evidence": "CONFIRMADO",
                    })
                    sc1326_payload = encode_SCFightRoundTime(left_time=30, round_num=1, little_round_player_id=1001, play_id=1)
                    self._send_sc(sock, conn_id, 1326, sc1326_payload, {"leftTime": 30, "round": 1, "littleRoundPlayerId": 1001, "playId": 1})

                elif msg_id == 4002:
                    # CSScenarioFinish -> respond with SCScenarioHadPlay (4001)
                    decoded_4002 = decode_CSScenarioFinish(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 4002,
                        "msg_name": "CSScenarioFinish",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded_4002,
                        "evidence": "CONFIRMADO",
                    })
                    scen_sn = decoded_4002.get("scenarioSn", 2803)
                    sc4001_payload = encode_SCScenarioHadPlay(sns=[scen_sn])
                    self._send_sc(sock, conn_id, 4001, sc4001_payload, {"sns": [scen_sn]})

                elif msg_id == 2101:
                    # CSShopQuery -> respond with SCShopQueryResult (2102)
                    decoded_2101 = decode_CSShopQuery(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 2101,
                        "msg_name": "CSShopQuery",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded_2101,
                        "evidence": "CONFIRMADO",
                    })
                    shop_sn = decoded_2101.get("shopSn", 2)
                    sample_items = [encode_DShopItem(goods_sn=i, stock_count=99) for i in range(1, 6)]
                    sc2102_payload = encode_SCShopQueryResult(shop_sn=shop_sn, d_items=sample_items)
                    self._send_sc(sock, conn_id, 2102, sc2102_payload, {"shopSn": shop_sn, "itemCount": len(sample_items)})

                elif msg_id == 7911:
                    # CSNPCTouch
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 7911,
                        "msg_name": "CSNPCTouch",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "CONFIRMADO",
                    })

                elif msg_id == 1204:
                    # CSSceneSwitch -> respond with SCSceneSwitch (1205)
                    decoded_1204 = decode_CSSceneSwitch(payload_plain)
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": 1204,
                        "msg_name": "CSSceneSwitch",
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": decoded_1204,
                        "evidence": "CONFIRMADO",
                    })
                    target_sn = decoded_1204.get("sceneSn", 2102)
                    pos_b = encode_DVector3(339.0, 203.0, 99.5)
                    dir_b = encode_DVector2(0.0, 1.0)
                    sc1205_payload = encode_SCSceneSwitch(scene_sn=target_sn, scene_id=target_sn, pos=pos_b, dir_vec=dir_b)
                    self._send_sc(sock, conn_id, 1205, sc1205_payload, {"sceneSn": target_sn})



                else:
                    self._log_frame({
                        "conn_id": conn_id,
                        "direction": "C -> S",
                        "msg_id": msg_id,
                        "msg_name": MSG_NAMES.get(msg_id, f"Unknown_{msg_id}"),
                        "total_len": total_len,
                        "header_hex": bytes(wire_frame[:8]).hex(" "),
                        "header_decrypted_hex": bytes(plain_frame[:8]).hex(" "),
                        "payload_wire_hex": payload_wire.hex(" "),
                        "payload_plain_hex": payload_plain.hex(" "),
                        "decoded": {},
                        "evidence": "OBSERVADO",
                    })
        except Exception:
            import traceback
            traceback.print_exc()
        finally:
            try:
                sock.close()
            except OSError:
                pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="P5X PoC Local TCP Server")
    parser.add_argument("--port", type=int, default=10403, help="Port to bind (default 10403)")
    args = parser.parse_args()

    srv = LocalPoCLoginServer(host="127.0.0.1", port=args.port, fixed_epoch_sec=1700000000)
    port = srv.start()
    print(f"[*] P5X PoC Local Login Server listening on 127.0.0.1:{port}", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        srv.stop()
