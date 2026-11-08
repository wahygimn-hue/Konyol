"""
backtest_web.py -- STRATEGI: acuan_mss (level awal H1 -> break-out -> MSS pertama jadi acuan -> acuan tersentuh -> MSS kedua -> entry)

ALUR (Long; Short = cermin)
1) LEVEL AWAL H1 (tanpa FVG, tanpa EMA): c1 bearish lalu c2 bullish, level = ujung wick terendah c1/c2.
   (Short: c1 bullish lalu c2 bearish, level = ujung wick tertinggi c1/c2.)
   FILTER LEVEL (NS_LV_N=5): candle pemilik ujung wick terpanjang (c1 atau c2) harus punya 5 candle kiri dan 5 candle kanan
   yang tidak melebihi ujung itu (body/wick; Support: tidak ada low lebih rendah, Resisten: tidak ada high lebih tinggi).
   Angka sama persis dianggap tidak melebihi (NS_LV_EQUAL=valid; invalid = ditolak). NS_LV_N=0 = filter mati.
   Level baru dianggap ada setelah 5 candle kanan close, jadi break-out dicari mulai candle setelahnya.
2) BREAK-OUT: candle H1 pertama setelah c2 yang BODY-nya close menembus level (Long: close < level; Short: close > level).
   Sentuhan wick saja tidak dihitung.
3) MSS PERTAMA: begitu candle break-out close, langsung cari MSS M5 (aturan P valid + swing referensi, N kiri-kanan = NS_P_SWING / NS_MSS_SWING).
   MSS pertama TIDAK entry. Ujung MSS (P = low terendah utk Long, high tertinggi utk Short) dijadikan ACUAN.
4) ACUAN TERSENTUH: candle M5 pertama setelah MSS pertama yang menyentuh acuan (Long: low <= acuan, Short: high >= acuan).
5) MSS KEDUA: dari candle sentuh, cari MSS M5 lagi. Sekarang boleh ENTRY: MARKET di close candle MSS kedua.
6) SL = ujung MSS kedua (P kedua), tanpa buffer. TP = RR x jarak entry-SL (default 1:3). Tanpa batas waktu.
   Dalam 1 candle M5 SL dicek duluan. Posisi yang belum selesai di akhir data tidak dihitung.
Aturan lain: sinyal kembar (arah + candle MSS sama) dihitung sekali; sinyal dilewati kalau posisi searah di koin yang sama masih terbuka.
Risk RISK_PCT dari balance (compounding, 1 akun bersama semua koin), fee masuk FEE_ENTRY_PCT + keluar FEE_EXIT_PCT.

Deploy Railway: Start command -> python backtest_web.py ; buka domain Railway.
Endpoint: /  (dashboard) | /trades.txt (satu blok per trade, satu field per baris) | /ringkasan.txt | /logs
Env: SYMBOLS (mis. FARTCOINUSDT,ETHFIUSDT), BACKTEST_START_DATE, BACKTEST_END_DATE, RR (3), RISK_PCT, INITIAL_BALANCE,
FEE_ENTRY_PCT, FEE_EXIT_PCT, LEVERAGE, MARGIN_USAGE_CAP, MAX_CONCURRENT (kosong/0 = tanpa batas),
NS_LV_N (5), NS_LV_EQUAL (valid), NS_P_SWING (1), NS_MSS_SWING (1), NS_LOOKBACK (100), NS_P_EQUAL / NS_SW_EQUAL (merge), NS_MSS_REF (range).
"""
import os, threading, time, bisect, heapq
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

import numpy as np
import pandas as pd
try:
    from pybit.unified_trading import HTTP
except Exception:      # pybit tidak terpasang -> fetch akan gagal dgn pesan jelas
    HTTP = None

# ============================================================
# CONFIG
# ============================================================
PORT             = int(os.environ.get('PORT', 8080))
INITIAL_BALANCE  = float(os.environ.get('INITIAL_BALANCE', '100.0'))
RISK_PCT         = float(os.environ.get('RISK_PCT', '0.01'))
FEE_ENTRY_PCT    = float(os.environ.get('FEE_ENTRY_PCT', '0.0006'))
FEE_EXIT_PCT     = float(os.environ.get('FEE_EXIT_PCT', str(0.0006 * 3)))
RR               = float(os.environ.get('RR', '3'))
LEVERAGE         = float(os.environ.get('LEVERAGE', '50'))
MARGIN_USAGE_CAP = float(os.environ.get('MARGIN_USAGE_CAP', '0.90'))
_mc = os.environ.get('MAX_CONCURRENT', '').strip().lower()
MAX_CONCURRENT   = float('inf') if _mc in ('', '10', 'unlimited', 'inf') else int(_mc)

NS_MSS_SWING = int(os.environ.get('NS_MSS_SWING', 1))      # swing fractal M5: N candle kiri & kanan
NS_P_SWING   = int(os.environ.get('NS_P_SWING', 1))        # P valid M5: N candle kiri & kanan tidak melampaui P
NS_LOOKBACK  = int(os.environ.get('NS_LOOKBACK', 100))     # swing boleh dari N candle M5 sebelum candle awal pencarian MSS
NS_SW_EQUAL  = os.environ.get('NS_SW_EQUAL', 'merge').strip().lower()
NS_P_EQUAL   = os.environ.get('NS_P_EQUAL', 'merge').strip().lower()
NS_MSS_REF   = os.environ.get('NS_MSS_REF', 'range').strip().lower()
NS_LV_N      = int(os.environ.get('NS_LV_N', 5))                  # filter level: ujung wick terpanjang c1/c2 -> N candle kiri & kanan tidak melebihi (0 = matikan)
NS_LV_EQUAL  = os.environ.get('NS_LV_EQUAL', 'valid').strip().lower()  # valid = angka sama TIDAK dianggap melebihi | invalid = angka sama ditolak

BACKTEST_START_DATE = os.environ.get('BACKTEST_START_DATE', '2025-01-01')
BACKTEST_END_DATE   = os.environ.get('BACKTEST_END_DATE', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
CACHE_DIR = os.environ.get('CACHE_DIR', './data_cache')
os.makedirs(CACHE_DIR, exist_ok=True)

SYMBOLS = [
    'PENDLEUSDT', 'PYTHUSDT', 'BLURUSDT', '1000BONKUSDT', 'WUSDT',
    'USUALUSDT', 'ETHFIUSDT', 'LABUSDT', 'IOTAUSDT', '1000FLOKIUSDT',
    'HBARUSDT', 'PLUMEUSDT', 'BERAUSDT', 'MASKUSDT', 'ESPORTSUSDT',
    'IMXUSDT', 'CRVUSDT', 'ACHUSDT', 'FARTCOINUSDT', 'AEVOUSDT',
    'ICPUSDT', 'ENAUSDT', 'ADAUSDT', 'WIFUSDT', 'DYDXUSDT',
    'BATUSDT', 'LRCUSDT', 'IOUSDT', 'BOMEUSDT', 'OPUSDT',
    'POPCATUSDT', 'WOOUSDT', 'STORJUSDT', 'ROSEUSDT', 'POWRUSDT',
    'JUPUSDT', 'HUSDT', 'STRKUSDT', 'IOTXUSDT', 'MEWUSDT',
    'VIRTUALUSDT', 'POLUSDT', 'CKBUSDT', 'ASTRUSDT'
]
if os.environ.get('SYMBOLS', '').strip():
    SYMBOLS = [x.strip().upper() for x in os.environ['SYMBOLS'].split(',') if x.strip()]

H1_MS = 3600 * 1000
M5_MS = 5 * 60 * 1000


def _date_to_ms(date_str):
    dt = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)

_START_MS = _date_to_ms(BACKTEST_START_DATE)
_END_MS   = _date_to_ms(BACKTEST_END_DATE) + 86400 * 1000 - 1

# ============================================================
# GLOBAL STATE
# ============================================================
_lock = threading.Lock()
_log = []
_phase = 'running'
_trades = []
_summary = {}
_funnel = {}
_monthly = []
_avg_monthly_growth = 0.0
_per_symbol = []


def _ts():
    return (datetime.now(timezone.utc) + timedelta(hours=7)).strftime('%H:%M:%S')

def _wib(ts_ms):
    if ts_ms is None:
        return ''
    dt = datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc) + timedelta(hours=7)
    return dt.strftime('%Y-%m-%d %H:%M')

def _log_msg(msg):
    line = f"[{_ts()}] {msg}"
    print(line, flush=True)
    with _lock:
        _log.append(line)

# ============================================================
# FETCH DATA M5 DARI BYBIT (dgn cache). H1 dibentuk dari M5 (12 candle/jam, hanya jam lengkap).
# ============================================================
def _cache_path(symbol, tf):
    return os.path.join(CACHE_DIR, f"{symbol}_{tf}_{BACKTEST_START_DATE}_{BACKTEST_END_DATE}.csv")

def _load_cache(symbol, tf):
    path = _cache_path(symbol, tf)
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            if not df.empty and {'ts', 'open', 'high', 'low', 'close', 'vol'}.issubset(df.columns):
                return df
        except Exception as e:
            _log_msg(f"   ⚠ {symbol} {tf}: cache korup ({e}), fetch ulang dari Bybit.")
    return None

def _save_cache(symbol, tf, df):
    try:
        df.to_csv(_cache_path(symbol, tf), index=False)
    except Exception as e:
        _log_msg(f"   ⚠ {symbol} {tf}: gagal simpan cache — {e}")

def fetch_bybit_m5(symbol):
    cached = _load_cache(symbol, 'M5')
    if cached is not None:
        _log_msg(f"   💾 {symbol} M5: pakai cache ({len(cached):,} candle) — skip fetch Bybit.")
        return cached
    if HTTP is None:
        raise RuntimeError("pybit belum terpasang (pip install pybit)")
    session = HTTP(testnet=False)
    rows, cur_end = [], _END_MS
    while True:
        for attempt in range(4):
            try:
                res = session.get_kline(symbol=symbol, category='linear', interval=5,
                                        limit=1000, start=_START_MS, end=cur_end)
                data = res['result']['list']
                break
            except Exception as e:
                wait = 2 ** attempt
                _log_msg(f"   ⚠ {symbol} M5 API error (attempt {attempt+1}): {e} — retry {wait}s")
                time.sleep(wait)
        else:
            _log_msg(f"   ❌ {symbol} M5: gagal fetch setelah 4 percobaan.")
            break
        if not data:
            break
        for kl in data:
            rows.append({'ts': int(kl[0]), 'open': float(kl[1]), 'high': float(kl[2]),
                         'low': float(kl[3]), 'close': float(kl[4]), 'vol': float(kl[5])})
        oldest_ts = int(data[-1][0])
        if oldest_ts <= _START_MS:
            break
        cur_end = oldest_ts - 1
        time.sleep(0.15)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).drop_duplicates(subset='ts').sort_values('ts').reset_index(drop=True)
    _save_cache(symbol, 'M5', df)
    return df


def build_h1(m5df):
    d = m5df[['ts', 'open', 'high', 'low', 'close']].copy()
    d['hh'] = (d['ts'] // H1_MS) * H1_MS
    g = d.groupby('hh')
    h1 = pd.DataFrame({'ts': g['hh'].first(), 'open': g['open'].first(), 'high': g['high'].max(),
                       'low': g['low'].min(), 'close': g['close'].last(), 'n': g.size()})
    return h1[h1['n'] == 12].drop(columns='n').reset_index(drop=True)

# ============================================================
# MSS M5 (P valid + swing referensi) -- sama dgn versi backtest_web.py sebelumnya
# ============================================================
def _ns_fractals(arr, lo, hi, N, sup, mode):
    """Swing fractal pada arr[lo:hi] (Long: high, Short: low), N candle kiri & kanan harus STRIKT kurang ekstrem.
    mode 'merge': candle berurutan dgn angka sama = SATU KESATUAN (kesatuan valid kalau N candle sebelum dan N candle sesudah kesatuan
      strikt tidak melebihi/sama). mode 'invalid': angka sama dgn tetangga = bukan swing. mode 'valid': sama boleh (cara lama).
    Return (list idx candle TERAKHIR tiap swing (menentukan kapan swing terkonfirmasi), dict {idx terakhir: idx candle PERTAMA kesatuan})."""
    m = hi - lo
    if m < 2 * N + 1:
        return [], {}
    seg = arr[lo:hi]
    if mode == 'valid':
        w = np.lib.stride_tricks.sliding_window_view(seg, 2 * N + 1)
        c_ = w[:, N]
        m_ = (c_ >= w.max(axis=1)) if sup else (c_ <= w.min(axis=1))
        ids = (np.flatnonzero(m_) + lo + N).tolist()
        return ids, {i: i for i in ids}
    chg = np.flatnonzero(seg[1:] != seg[:-1]) + 1
    starts = np.concatenate(([0], chg)); ends = np.concatenate((chg - 1, [m - 1]))
    if mode != 'merge':
        keep = ends == starts
        starts, ends = starts[keep], ends[keep]
    ok = (starts - N >= 0) & (ends + N < m)
    starts, ends = starts[ok], ends[ok]
    v = seg[starts]
    good = np.ones(len(v), dtype=bool)
    for kk in range(1, N + 1):
        if sup:
            good &= (seg[starts - kk] < v) & (seg[ends + kk] < v)
        else:
            good &= (seg[starts - kk] > v) & (seg[ends + kk] > v)
    st = (starts[good] + lo).tolist(); en = (ends[good] + lo).tolist()
    return en, dict(zip(en, st))


def _ns_find_mss(sup, tj0, stop, H5, L5, C5, resume=None):
    """Market Structure Shift M5 setelah acuan tersentuh di candle tj0 (SMC).
    Long : harga turun ke acuan, low terendah = P. MSS = candle M5 pertama yang CLOSE di atas swing high referensi.
    Short: kebalikannya (P = high tertinggi, referensi = swing low).
    P VALID: candle ekstrem (Long: low terendah sejak sentuh; Short: high tertinggi) yang tidak dilampaui oleh NS_P_SWING (default 1) candle di kirinya
      dan NS_P_SWING candle di kanannya (P baru valid setelah candle kanan ke-N closed; kiri boleh candle sebelum sentuh). Angka SAMA PERSIS dgn tetangga kiri/kanan juga TIDAK valid (NS_P_EQUAL='invalid', default): P harus
      benar-benar lebih dalam dari kedua tetangganya (Long: low-nya < low kiri DAN < low kanan). P baru dianggap valid setelah candle
      kanannya closed; kalau candle kanan membuat ekstrem yang lebih jauh, kandidat lama gugur (bukan P) dan kandidat baru yang dipakai;
      kalau candle kanan sama persis, kandidat itu tidak valid sampai ada ekstrem baru yang lebih dalam.
      MSS hanya dicek terhadap P yang valid.
    Swing referensi:
     - Selama baru ada 1 P valid: swing fractal (NS_MSS_SWING kiri-kanan, default 1; angka sama dgn tetangga = BUKAN swing, NS_SW_EQUAL='invalid';
       boleh dari NS_LOOKBACK candle sebelum sentuh) terakhir sebelum P.
     - NS_MSS_REF='range' (default): swing BARU ADA kalau sebuah P valid tertembus P valid baru (ekstrem lebih jauh); P pertama saja belum punya swing (tidak ada fallback ke fractal sebelum P). Tiap P valid baru muncul, swing = swing FRACTAL (NS_MSS_SWING kiri-kanan) dengan HIGH TERTINGGI (Short: LOW TERENDAH) antara P valid lama s/d
       P valid baru (inklusif). Dihitung ulang di SETIAP pergeseran P (tidak kumulatif). Tidak ada swing fractal di range -> swing lama dipertahankan.
     - NS_MSS_REF='range_max': sama, tapi swing hanya naik (Long) / turun (Short), tidak pernah diturunkan (tertinggi sejak P pertama).
     - NS_MSS_REF='fractal' (cara lama): referensi selalu swing fractal terakhir sebelum P.
    resume=(idx candle penembus P lama, idx P lama, idx terakhir kesatuan P lama, idx swing lama): lanjutkan alur setelah MSS GAGAL (P lama tertembus ekstrem baru):
      kandidat P baru mulai dari candle penembus, swing = swing fractal tertinggi/terendah antara P lama s/d P baru, lalu tunggu MSS berikutnya.
    Return (idx candle MSS, idx P valid, idx candle swing yang ditembus, idx terakhir kesatuan P) / None."""
    N = NS_MSS_SWING
    NP = NS_P_SWING
    hi = min(stop, len(H5))
    lo = max(tj0 - NS_LOOKBACK, 0)
    arr = H5 if sup else L5
    use_range = (NS_MSS_REF != 'fractal')
    sw, sw_first = _ns_fractals(arr, lo, hi, N, sup, NS_SW_EQUAL)
    if not sw and not use_range:
        return None
    more = (lambda a, b: L5[a] < L5[b]) if sup else (lambda a, b: H5[a] > H5[b])        # a lebih ekstrem dari b
    strict = (NS_P_EQUAL != 'valid')
    if strict:      # tetangga b harus benar-benar tidak melampaui a: sama persis = tidak valid
        ok_nb = (lambda a, b: L5[b] > L5[a]) if sup else (lambda a, b: H5[b] < H5[a])
    else:           # sama dianggap boleh
        ok_nb = (lambda a, b: L5[b] >= L5[a]) if sup else (lambda a, b: H5[b] <= H5[a])
    merge = (NS_P_EQUAL == 'merge')
    ext5 = L5 if sup else H5

    def left_ok_fn(c):      # NP candle di kiri P tidak boleh melampaui P (boleh candle sebelum sentuh)
        if c - NP < 0:
            return False
        return all(ok_nb(c, c - kk) for kk in range(1, NP + 1))

    def range_swing(a, b):  # swing fractal N kiri-kanan TERTINGGI (Short: TERENDAH) yg kesatuannya ada di [a, b]; None kalau tidak ada
        best = None; bv = None
        for e in sw[bisect.bisect_left(sw, a):]:
            if e > b:
                break
            f = sw_first[e]
            if f < a:
                continue
            v = H5[f] if sup else L5[f]
            if best is None or ((v > bv) if sup else (v < bv)):
                best, bv = f, v
        return best

    cand = tj0; cand_last = tj0
    if merge:       # kesatuan angka sama: ikut melebar ke kiri (candle sebelum sentuh yg angkanya sama)
        while cand - 1 >= 0 and ext5[cand - 1] == ext5[tj0]:
            cand -= 1
    left_ok = left_ok_fn(cand); right_bad = False
    Pv = None; Pv_last = None; rref = None
    t0 = tj0 + 1
    if resume is not None:     # lanjut setelah MSS gagal: P baru = ekstrem yang menembus P lama
        t_new, Pv, Pv_last, rref = resume
        cand = t_new; cand_last = t_new
        left_ok = left_ok_fn(cand); right_bad = False
        t0 = t_new + 1
    for t in range(t0, hi):
        if more(t, cand):                               # ekstrem baru -> kandidat lama gugur
            cand = t; cand_last = t; left_ok = left_ok_fn(cand); right_bad = False
            continue
        if merge and t == cand_last + 1 and ext5[t] == ext5[cand]:
            cand_last = t                               # angka sama menyambung -> satu kesatuan, jendela kanan dihitung ulang dari sini
            continue
        # candle t tidak melampaui cand: sisi kanan (NP candle setelah cand/kesatuan) harus semuanya tidak melampaui / sama
        if t <= cand_last + NP and not ok_nb(cand, t):
            right_bad = True                            # sama persis / melampaui di jendela kanan -> cand bukan P (sampai ada ekstrem baru)
        if Pv != cand and left_ok and not right_bad and t >= cand_last + NP:
            if use_range and Pv is not None:            # P valid baru: swing = swing fractal tertinggi/terendah antara P lama s/d P baru
                cx = range_swing(Pv_last, cand)
                if cx is not None:
                    if NS_MSS_REF == 'range_max' and rref is not None and ((H5[cx] <= H5[rref]) if sup else (L5[cx] >= L5[rref])):
                        pass            # 'range_max': swing hanya naik/turun, tidak pernah diturunkan
                    else:
                        rref = cx       # 'range': dihitung ulang di SETIAP pergeseran P valid; tidak ada swing fractal di range -> swing lama dipertahankan
            Pv = cand; Pv_last = cand_last
        if Pv != cand:
            continue
        if use_range:
            if rref is None:
                continue        # belum ada P yang tertembus P baru (atau belum ada swing di antaranya) -> belum ada swing, belum bisa MSS
            ref = rref
        else:
            k = bisect.bisect_right(sw, min(cand - 1, t - N)) - 1
            if k < 0:
                continue
            ref = sw_first[sw[k]]
        if (C5[t] > H5[ref]) if sup else (C5[t] < L5[ref]):
            return t, cand, ref, cand_last
    return None


# ============================================================
# DETEKSI SINYAL PER KOIN
# ============================================================
def find_exit(sup, t, sl, tp, H5, L5):
    """Return (idx candle exit, harga exit, 'SL'/'TP') atau None kalau belum selesai. SL dicek duluan."""
    n5 = len(H5); s = t + 1
    while s < n5:
        e = min(s + 4096, n5)
        if sup:
            a = np.flatnonzero(L5[s:e] <= sl); bb = np.flatnonzero(H5[s:e] >= tp)
        else:
            a = np.flatnonzero(H5[s:e] >= sl); bb = np.flatnonzero(L5[s:e] <= tp)
        ia = int(a[0]) if len(a) else None
        ib = int(bb[0]) if len(bb) else None
        if ia is not None and (ib is None or ia <= ib):
            return s + ia, sl, 'SL'
        if ib is not None:
            return s + ib, tp, 'TP'
        s = e
    return None


def process_coin(symbol, m5df):
    m5df = m5df.sort_values('ts').reset_index(drop=True)
    TS5 = m5df['ts'].values.astype(np.int64)
    H5 = m5df['high'].values.astype(float); L5 = m5df['low'].values.astype(float); C5 = m5df['close'].values.astype(float)
    n5 = len(TS5)
    h1 = build_h1(m5df)
    ts = h1['ts'].values.astype(np.int64)
    o = h1['open'].values.astype(float); h = h1['high'].values.astype(float)
    l = h1['low'].values.astype(float); c = h1['close'].values.astype(float)
    n = len(c)
    st = dict(level=0, level_valid=0, breakout=0, no_mss1=0, mss1=0, no_touch=0, touch=0, no_mss2=0, signal=0, dup=0)
    cands = []
    r1_cache = {}; r2_cache = {}
    for i in range(0, n - 2):
        for sup in (True, False):
            if sup and not (c[i] < o[i] and c[i + 1] > o[i + 1]):
                continue
            if (not sup) and not (c[i] > o[i] and c[i + 1] < o[i + 1]):
                continue
            lvl = min(l[i], l[i + 1]) if sup else max(h[i], h[i + 1])
            st['level'] += 1
            start = i + 2
            if NS_LV_N > 0:
                # ujung wick terpanjang antara c1/c2 (Support: low terendah, Resisten: high tertinggi)
                if sup:
                    m = i if l[i] <= l[i + 1] else i + 1
                else:
                    m = i if h[i] >= h[i + 1] else i + 1
                if m - NS_LV_N < 0 or m + NS_LV_N >= n:
                    continue
                if sup:
                    left = l[m - NS_LV_N:m]; right = l[m + 1:m + 1 + NS_LV_N]
                    bad = (left <= lvl).any() or (right <= lvl).any() if NS_LV_EQUAL == 'invalid' else (left < lvl).any() or (right < lvl).any()
                else:
                    left = h[m - NS_LV_N:m]; right = h[m + 1:m + 1 + NS_LV_N]
                    bad = (left >= lvl).any() or (right >= lvl).any() if NS_LV_EQUAL == 'invalid' else (left > lvl).any() or (right > lvl).any()
                if bad:
                    continue
                start = m + NS_LV_N + 1        # level baru pasti setelah N candle kanan close
            st['level_valid'] += 1
            seg = c[start:]
            hit = np.flatnonzero(seg < lvl) if sup else np.flatnonzero(seg > lvl)
            if len(hit) == 0:
                continue
            k = start + int(hit[0]); st['breakout'] += 1
            tj0 = int(np.searchsorted(TS5, ts[k] + H1_MS)) - 1        # candle M5 terakhir di dalam candle break-out
            if tj0 < 0 or tj0 + 2 >= n5:
                continue
            key1 = (sup, tj0)
            if key1 not in r1_cache:
                r1_cache[key1] = _ns_find_mss(sup, tj0, n5, H5, L5, C5)
            r1 = r1_cache[key1]
            if r1 is None:
                st['no_mss1'] += 1; continue
            st['mss1'] += 1
            t1, P1 = r1[0], r1[1]
            acuan = float(L5[P1] if sup else H5[P1])
            key2 = (sup, t1, P1)
            if key2 not in r2_cache:
                rest = (L5[t1 + 1:] <= acuan) if sup else (H5[t1 + 1:] >= acuan)
                tt = np.flatnonzero(rest)
                if len(tt) == 0:
                    r2_cache[key2] = ('no_touch', None, None)
                else:
                    jt = t1 + 1 + int(tt[0])
                    r2_cache[key2] = ('ok', jt, _ns_find_mss(sup, jt, n5, H5, L5, C5) if jt + 2 < n5 else None)
            tag, jt, r2 = r2_cache[key2]
            if tag == 'no_touch':
                st['no_touch'] += 1; continue
            st['touch'] += 1
            if r2 is None:
                st['no_mss2'] += 1; continue
            t, P = r2[0], r2[1]
            entry = float(C5[t]); sl = float(L5[P] if sup else H5[P])
            dist = (entry - sl) if sup else (sl - entry)
            if dist <= 0:
                continue
            tp = entry + RR * dist if sup else entry - RR * dist
            st['signal'] += 1
            cands.append(dict(symbol=symbol, sup=sup, d='Long' if sup else 'Short', lvl=float(lvl), formed=int(ts[i + 1]),
                              bo=int(ts[k]), mss1=int(TS5[t1]), acuan=acuan, touch=int(TS5[jt]), mss=int(TS5[t]),
                              ptime=int(TS5[P]), entry=entry, sl=sl, tp=tp, dist=dist, t=t, entry_ts=int(TS5[t])))
    cands.sort(key=lambda x: (x['t'], x['lvl']))
    seen = set(); uniq = []
    for cd in cands:
        key = (cd['d'], cd['t'])
        if key in seen:
            st['dup'] += 1; continue
        seen.add(key); uniq.append(cd)
    for cd in uniq:
        ex = find_exit(cd['sup'], cd['t'], cd['sl'], cd['tp'], H5, L5)
        if ex is None:
            cd['exit_ts'] = None; cd['why'] = None; cd['exit_px'] = None
        else:
            cd['exit_ts'] = int(TS5[ex[0]]); cd['exit_px'] = ex[1]; cd['why'] = ex[2]
    return uniq, st

# ============================================================
# SIMULASI GABUNGAN (1 balance, semua koin)
# ============================================================
def simulate(cands):
    cands = sorted(cands, key=lambda x: (x['entry_ts'], x['symbol']))
    fee = FEE_ENTRY_PCT + FEE_EXIT_PCT
    heap = []; closed_pnl = 0.0; used = 0.0; n_open = 0; open_sd = set()
    trades = []; bl = dict(open_same=0, slot=0, margin=0, terbuka=0)
    for idx, cd in enumerate(cands):
        t0 = cd['entry_ts']
        while heap and heap[0][0] <= t0:
            _, _, pnl, margin, sd = heapq.heappop(heap)
            closed_pnl += pnl; used -= margin; n_open -= 1; open_sd.discard(sd)
        sd = (cd['symbol'], cd['d'])
        if sd in open_sd:
            bl['open_same'] += 1; continue
        if n_open >= MAX_CONCURRENT:
            bl['slot'] += 1; continue
        bal = INITIAL_BALANCE + closed_pnl
        risk = bal * RISK_PCT
        notional = risk / (cd['dist'] / cd['entry'])
        margin = notional / LEVERAGE
        if used + margin > bal * MARGIN_USAGE_CAP:
            bl['margin'] += 1; continue
        if cd['why'] is None:                      # belum selesai di akhir data: menahan slot/margin, tidak dihitung
            bl['terbuka'] += 1
            heapq.heappush(heap, (float('inf'), idx, 0.0, margin, sd)); used += margin; n_open += 1; open_sd.add(sd)
            continue
        feeR = fee * cd['entry'] / cd['dist']
        r = (RR if cd['why'] == 'TP' else -1.0) - feeR
        pnl = r * risk
        tr = dict(cd); tr['r'] = r; tr['pnl'] = pnl; tr['bal_before'] = bal
        trades.append(tr)
        heapq.heappush(heap, (cd['exit_ts'], idx, pnl, margin, sd)); used += margin; n_open += 1; open_sd.add(sd)
    run = INITIAL_BALANCE; pk = INITIAL_BALANCE; mdd = 0.0
    for tr in sorted(trades, key=lambda x: x['exit_ts']):
        run += tr['pnl']; tr['bal_after'] = run
        pk = max(pk, run); mdd = max(mdd, (pk - run) / pk * 100)
    trades.sort(key=lambda x: x['entry_ts'])
    nt = len(trades); nw = sum(1 for x in trades if x['why'] == 'TP'); tot_r = sum(x['r'] for x in trades)
    summ = dict(n_trades=nt, n_win=nw, n_loss=nt - nw, wr=(nw / nt * 100 if nt else 0.0), total_r=tot_r,
                avg_r=(tot_r / nt if nt else 0.0), final_balance=run, roi=(run / INITIAL_BALANCE - 1) * 100, mdd=mdd)
    return trades, summ, bl


def monthly_breakdown(trades):
    by = {}
    for tr in sorted(trades, key=lambda x: x['exit_ts']):
        by.setdefault(_wib(tr['exit_ts'])[:7], []).append(tr)
    rows = []; bal = INITIAL_BALANCE
    for mth, L in by.items():
        pr = sum(x['pnl'] for x in L); nw = sum(1 for x in L if x['why'] == 'TP')
        rows.append(dict(month=mth, start=bal, end=bal + pr, profit=pr, growth=(pr / bal * 100 if bal else 0.0),
                         n=len(L), wr=nw / len(L) * 100, total_r=sum(x['r'] for x in L)))
        bal += pr
    avg = sum(r['growth'] for r in rows) / len(rows) if rows else 0.0
    return rows, avg


def per_symbol_breakdown(trades):
    by = {}
    for tr in trades:
        by.setdefault(tr['symbol'], []).append(tr)
    rows = []
    for sym, L in by.items():
        nw = sum(1 for x in L if x['why'] == 'TP')
        rows.append(dict(symbol=sym, n=len(L), tp=nw, sl=len(L) - nw, wr=nw / len(L) * 100,
                         total_r=sum(x['r'] for x in L), profit=sum(x['pnl'] for x in L)))
    rows.sort(key=lambda r: -r['total_r'])
    return rows

# ============================================================
# RUN
# ============================================================
def _run():
    global _phase, _trades, _summary, _funnel, _monthly, _avg_monthly_growth, _per_symbol
    try:
        _log_msg(f"🚀 Backtest acuan_mss — {len(SYMBOLS)} koin, {BACKTEST_START_DATE} s/d {BACKTEST_END_DATE}")
        _log_msg(f"   Level awal H1 (tanpa FVG, filter ujung wick {NS_LV_N} kiri-kanan) -> break-out body -> MSS pertama (acuan) -> acuan tersentuh -> MSS kedua -> entry MARKET, "
                 f"SL ujung MSS kedua, TP 1:{RR:g}. Risk {RISK_PCT*100:.1f}%/trade, leverage {LEVERAGE:g}x, slot {'tanpa batas' if MAX_CONCURRENT == float('inf') else int(MAX_CONCURRENT)}.")
        all_c = []; tot = {}
        for symbol in SYMBOLS:
            _log_msg(f"📊 {symbol}: fetch M5...")
            df = fetch_bybit_m5(symbol)
            if df is None or df.empty:
                _log_msg(f"   ⚠ {symbol}: data kosong, skip."); continue
            cands, st = process_coin(symbol, df)
            all_c.extend(cands)
            for k, v in st.items():
                tot[k] = tot.get(k, 0) + v
            _log_msg(f"   ✅ {symbol}: {len(df):,} candle M5, {st['level']} level ({st['level_valid']} lolos filter), {st['breakout']} break-out, MSS1 {st['mss1']}, "
                     f"acuan tersentuh {st['touch']}, sinyal {st['signal']} (kembar {st['dup']}) -> {len(cands)} kandidat entry.")
        _log_msg(f"🧮 Simulasi gabungan ({len(all_c)} kandidat)...")
        trades, summ, bl = simulate(all_c)
        monthly, avg = monthly_breakdown(trades)
        per_sym = per_symbol_breakdown(trades)
        funnel = dict(tot); funnel.update(bl)
        with _lock:
            _trades[:] = trades; _summary.clear(); _summary.update(summ); _funnel.clear(); _funnel.update(funnel)
            _monthly[:] = monthly; _avg_monthly_growth = avg; _per_symbol[:] = per_sym
            _phase = 'done'
        _log_msg(f"✅ SELESAI. {summ['n_trades']} trade, WR {summ['wr']:.1f}%, Total R {summ['total_r']:.2f}, "
                 f"Balance akhir ${summ['final_balance']:.2f} (ROI {summ['roi']:+.1f}%), max DD {summ['mdd']:.1f}%")
    except Exception as e:
        import traceback
        _log_msg(f"❌ ERROR: {e}")
        _log_msg(traceback.format_exc())
        with _lock:
            _phase = 'error'

# ============================================================
# OUTPUT TXT
# ============================================================
def _trades_txt():
    with _lock:
        trades = list(_trades); phase = _phase
    if not trades:
        return ('Belum ada trade (backtest masih berjalan atau tidak ada sinyal).\n' if phase != 'done' else 'Tidak ada trade.\n').encode('utf-8')
    out = []
    for k, tr in enumerate(trades, 1):
        out += [f"Trade : {k}", f"Coin : {tr['symbol']}", f"Dir : {tr['d']}", f"Hasil : {tr['why']} {tr['r']:+.2f}R",
                f"Level : {tr['lvl']:.8g}", f"Level terbentuk : {_wib(tr['formed'])}", f"Break-out H1 : {_wib(tr['bo'])}",
                f"MSS pertama : {_wib(tr['mss1'])}", f"Acuan : {tr['acuan']:.8g}", f"Acuan tersentuh : {_wib(tr['touch'])}",
                f"P MSS kedua : {_wib(tr['ptime'])}", f"MSS kedua (entry) : {_wib(tr['mss'])}",
                f"Entry : {tr['entry']:.8g}", f"SL : {tr['sl']:.8g}", f"TP : {tr['tp']:.8g}",
                f"Exit waktu : {_wib(tr['exit_ts'])}", f"Balance setelah : ${tr['bal_after']:.2f}", ""]
    return '\n'.join(out).encode('utf-8')


def _ringkasan_txt():
    with _lock:
        s = dict(_summary); f = dict(_funnel); mo = list(_monthly); avg = _avg_monthly_growth; ps = list(_per_symbol); phase = _phase
    if phase != 'done':
        return f'Backtest belum selesai (status: {phase}).\n'.encode('utf-8')
    o = ["RINGKASAN BACKTEST acuan_mss", f"Periode : {BACKTEST_START_DATE} s/d {BACKTEST_END_DATE}", f"Koin : {len(SYMBOLS)}",
         f"Total trade : {s['n_trades']}", f"Menang / Kalah : {s['n_win']} / {s['n_loss']}", f"Win rate : {s['wr']:.1f}%",
         f"Total R : {s['total_r']:.2f}", f"Rata-rata R : {s['avg_r']:.2f}", f"Balance awal : ${INITIAL_BALANCE:.2f}",
         f"Balance akhir : ${s['final_balance']:.2f}", f"ROI : {s['roi']:+.1f}%", f"Max drawdown : {s['mdd']:.1f}%",
         f"Rata-rata growth per bulan : {avg:+.2f}%", "", "FUNNEL",
         f"Level H1 awal (pola c1/c2) : {f.get('level',0)}", f"Level lolos filter 5 kiri-kanan : {f.get('level_valid',0)}", f"Break-out : {f.get('breakout',0)}", f"Tanpa MSS pertama : {f.get('no_mss1',0)}",
         f"MSS pertama (acuan) : {f.get('mss1',0)}", f"Acuan tak pernah tersentuh : {f.get('no_touch',0)}",
         f"Acuan tersentuh : {f.get('touch',0)}", f"Tanpa MSS kedua : {f.get('no_mss2',0)}", f"Sinyal entry (MSS kedua) : {f.get('signal',0)}",
         f"Sinyal kembar dilewati : {f.get('dup',0)}", f"Dilewati posisi searah masih terbuka : {f.get('open_same',0)}",
         f"Dilewati batas slot : {f.get('slot',0)}", f"Dilewati margin kurang : {f.get('margin',0)}",
         f"Posisi belum selesai di akhir data : {f.get('terbuka',0)}", "", "PER BULAN (basis waktu exit, WIB)"]
    for m in mo:
        o += [f"Bulan : {m['month']}", f"Trade : {m['n']}", f"Win rate : {m['wr']:.1f}%", f"Total R : {m['total_r']:.2f}",
              f"Balance awal : ${m['start']:.2f}", f"Balance akhir : ${m['end']:.2f}", f"Growth : {m['growth']:+.2f}%", ""]
    o += ["PER KOIN (urut total R)"]
    for r in ps:
        o += [f"Coin : {r['symbol']}", f"Trade : {r['n']}", f"TP / SL : {r['tp']} / {r['sl']}", f"Win rate : {r['wr']:.1f}%",
              f"Total R : {r['total_r']:.2f}", f"Profit : ${r['profit']:.2f}", ""]
    return '\n'.join(o).encode('utf-8')

# ============================================================
# DASHBOARD
# ============================================================
def _render_html():
    with _lock:
        phase = _phase; s = dict(_summary); f = dict(_funnel); mo = list(_monthly); avg = _avg_monthly_growth
        ps = list(_per_symbol); log_cp = list(_log[-200:])
    refresh = '<meta http-equiv="refresh" content="8">' if phase == 'running' else ''
    st_txt = {'running': '⏳ Berjalan...', 'done': '✅ Selesai', 'error': '❌ Error (lihat log)'}.get(phase, phase)
    body = [f"<h2>Backtest acuan_mss</h2><p>{st_txt} — {len(SYMBOLS)} koin, {BACKTEST_START_DATE} s/d {BACKTEST_END_DATE}</p>",
            f"<div class='note'>Level awal H1 (tanpa FVG, ujung wick {NS_LV_N} kiri-kanan) → break-out body → <b>MSS pertama</b> (ujungnya jadi acuan) → acuan tersentuh → "
            f"<b>MSS kedua</b> → entry market, SL ujung MSS kedua, TP 1:{RR:g}. Risk {RISK_PCT*100:.1f}%/trade (compounding), leverage {LEVERAGE:g}x.</div>"]
    if phase == 'done' and s:
        cls = 'pos' if s['total_r'] >= 0 else 'neg'
        body.append(f"<div class='cards'><div class='c'><span>Trade</span><b>{s['n_trades']}</b></div>"
                    f"<div class='c'><span>Win rate</span><b>{s['wr']:.1f}%</b></div>"
                    f"<div class='c'><span>Total R</span><b class='{cls}'>{s['total_r']:+.2f}</b></div>"
                    f"<div class='c'><span>ROI</span><b class='{cls}'>{s['roi']:+.1f}%</b></div>"
                    f"<div class='c'><span>Balance</span><b>${s['final_balance']:.2f}</b></div>"
                    f"<div class='c'><span>Max DD</span><b>{s['mdd']:.1f}%</b></div></div>")
        body.append("<p><a href='/trades.txt'>📄 trades.txt</a> &nbsp; <a href='/ringkasan.txt'>📄 ringkasan.txt</a> &nbsp; <a href='/logs'>📜 logs</a></p>")
        body.append("<h3>Funnel</h3><p class='small'>"
                    f"Level {f.get('level',0)} → lolos filter {f.get('level_valid',0)} → break-out {f.get('breakout',0)} → MSS pertama {f.get('mss1',0)} → acuan tersentuh {f.get('touch',0)} → "
                    f"sinyal MSS kedua {f.get('signal',0)} (kembar {f.get('dup',0)}, posisi searah terbuka {f.get('open_same',0)}, slot {f.get('slot',0)}, margin {f.get('margin',0)}).</p>")
        body.append(f"<h3>Pertumbuhan per Bulan <small>(rata-rata {avg:+.2f}%/bulan)</small></h3><table><tr><th>Bulan</th><th>Trade</th><th>WR</th><th>R</th><th>Awal</th><th>Akhir</th><th>Growth</th></tr>")
        for m in mo:
            c_ = 'pos' if m['profit'] >= 0 else 'neg'
            body.append(f"<tr><td>{m['month']}</td><td>{m['n']}</td><td>{m['wr']:.0f}%</td><td class='{c_}'>{m['total_r']:+.2f}</td><td>${m['start']:.2f}</td><td>${m['end']:.2f}</td><td class='{c_}'>{m['growth']:+.2f}%</td></tr>")
        body.append("</table>")
        body.append("<h3>Per Koin</h3><table><tr><th>Koin</th><th>Trade</th><th>TP/SL</th><th>WR</th><th>R</th><th>Profit</th></tr>")
        for r in ps:
            c_ = 'pos' if r['total_r'] >= 0 else 'neg'
            body.append(f"<tr><td>{r['symbol']}</td><td>{r['n']}</td><td>{r['tp']}/{r['sl']}</td><td>{r['wr']:.0f}%</td><td class='{c_}'>{r['total_r']:+.2f}</td><td class='{c_}'>${r['profit']:.2f}</td></tr>")
        body.append("</table>")
    body.append("<h3>Log</h3><pre>" + '\n'.join(log_cp).replace('<', '&lt;') + "</pre>")
    css = ("body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#0f1419;color:#e6e6e6;margin:0;padding:14px;max-width:900px}"
           "h2,h3{margin:.6em 0 .3em}a{color:#6cb6ff}.note{background:#1a2230;border-left:3px solid #6cb6ff;padding:8px 10px;font-size:13px;margin:8px 0}"
           ".cards{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0}.c{background:#1a2230;border-radius:8px;padding:8px;text-align:center}"
           ".c span{display:block;font-size:11px;color:#9aa4b2}.c b{font-size:17px}.pos{color:#3fb950}.neg{color:#f85149}"
           "table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:5px 6px;border-bottom:1px solid #263041;text-align:right}th:first-child,td:first-child{text-align:left}"
           ".small{font-size:13px;color:#b8c0cc}pre{background:#0b0f14;padding:8px;font-size:11px;overflow:auto;max-height:320px;white-space:pre-wrap}")
    html = f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>{refresh}<title>Backtest acuan_mss</title><style>{css}</style></head><body>{''.join(body)}</body></html>"
    return html.encode('utf-8')

# ============================================================
# HTTP HANDLER + ENTRY POINT
# ============================================================
class _Handler(BaseHTTPRequestHandler):
    def _send(self, body, ctype):
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/trades.txt':
            return self._send(_trades_txt(), 'text/plain; charset=utf-8')
        if path == '/ringkasan.txt':
            return self._send(_ringkasan_txt(), 'text/plain; charset=utf-8')
        if path == '/logs':
            with _lock:
                body = '\n'.join(_log).encode('utf-8')
            return self._send(body, 'text/plain; charset=utf-8')
        return self._send(_render_html(), 'text/html; charset=utf-8')

    def log_message(self, *_):
        pass


if __name__ == '__main__':
    threading.Thread(target=_run, daemon=True).start()
    server = HTTPServer(('0.0.0.0', PORT), _Handler)
    print(f"🌐 Server running on port {PORT}", flush=True)
    server.serve_forever()
