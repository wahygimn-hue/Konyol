"""
backtest_web.py -- bias_sweep + MSS M5 (BS_ENTRY=mss_m5, DEFAULT; BS_ENTRY=eng = cara lama sweep+engulfing). Bias H1 & pencarian low/high H1 tetap sama. Bedanya konfirmasi entry (Long; Short = cermin):
  1) Low H1 kandidat tersentuh (cek di M5: low M5 <= low H1). Ujung bawah M5 (P) = low terendah M5 di dalam candle H1 pemilik low itu.
  2) Swing = high tertinggi dari P sampai candle sentuh (BS_M5_SWFRAC=0 default: swing bebas = titik terjauh di antara P sebelumnya dan P terakhir tanpa syarat kiri-kanan; =1 swing wajib kiri-kanan 1-1; P selalu wajib kiri-kanan). Swing itu harus di-break (close M5 menembus) = MSS.
  3) Struktur bearish: kalau P bawah ditembus P M5 baru (swing low 1-1 yang lebih rendah), swing dihitung ulang = high tertinggi (valid 1-1) antara P lama dan P baru; itu yang harus di-break.
  4) MSS -> entry LIMIT di swing yang di-break (BS_M5_ENTRY=limit_sw, default; market = di close MSS; limit batal kalau TP tersentuh dulu), SL ujung MSS (low terendah dari P terakhir s/d MSS) + pengaman BS_M5_SLBUF% (default 0.2), TP titik tertinggi range H1. Batal kalau harga sampai titik tertinggi range / ujung bias tersentuh / bias berubah.
  5) Kalau kena SL: bias TIDAK berakhir. Cari low H1 baru yang LEBIH BAWAH dari low yang tadi disentuh -> disentuh -> MSS M5 -> limit lagi. Bias hanya selesai kalau titik tertinggi range tercapai atau H1 melakukan MSS+struktur melawan bias (BS_M5_ENDBREAK=1 = cara lama, ujung bias tersentuh ikut mengakhiri).
  SL: BS_M5_SLMODE=end (default) = ujung MSS; low_mss = low M5 kiri-1 kanan-1 terdekat ke belakang dari candle break (harus di bawah entry), kalau tidak ada = ujung MSS. Lalu + BS_M5_SLBUF%.
  6) BS_M5_MSS2=1 (default): setelah MSS-1 JANGAN entry. Tunggu ujung MSS-1 tersentuh; swing MSS-2 = high tertinggi dari candle break MSS-1 s/d candle ujung tersentuh (kiri-kanan 1); kalau bikin struktur bearish lagi (P baru menembus P bawah) swing dihitung ulang. Close menembus swing = MSS-2 -> limit di swing itu, SL ujung MSS-2 + BS_M5_SLBUF% (default 0.3), TP titik tertinggi range.
  SL default: ujung BODY candle ujung MSS (BS_M5_SLREF=body; wick = ujung wick), buffer BS_M5_SLBUF default 0.
  RR: hanya trade kalau RR rencana (limit->TP : limit->SL) >= BS_M5_MINRR (default 2). Di bawah itu limit tidak dipasang, low dianggap terpakai, cari low yang lebih bawah.
  FIBONACCI (BS_FIB=1 default): range pada struktur H1. 100% = ujung bawah struktur H1 terbaru (P baru yang menembus P lama sesudah bias; kalau belum ada = ujung bias), 0% = titik tertinggi range (Short: terendah). Struktur baru terbentuk -> 100% pindah ke low baru (range melebar). Low (kandidat) hanya dicari/dipakai kalau kedalamannya >= BS_FIB_DEPTH (0.5 = 50% range).
  Default sekarang: MSS satu kali (BS_M5_MSS2=0), tanpa filter RR (BS_M5_MINRR=0), SL ujung wick MSS buffer 0.
  WARM-UP: BS_WARMUP=100 candle H1 pertama tiap koin tidak ada trade. Fibonacci default 61.8% (BS_FIB_DEPTH). Fibonacci (strict) = pada struktur H1 aktif: 100% = ujung swing struktur TERBARU (struktur1, lalu pindah ke swing struktur2, dst), 0% = titik tertinggi/terendah range; low boleh melebihi 100% asal MSS lawan belum terjadi lebih dulu. Selama MSS lawan menunggu konfirmasi: tidak ada low baru/entry baru.
  RANTAI H1 SATU ARAH (BS_STRICT=1 default): bias Long hanya cari P high ditembus P high lebih tinggi (struktur bullish); swing low di antaranya di-break close = MSS short. Tidak ada MSS long saat bias Long (tidak ada refresh/reset). Struktur yang mengkonfirmasi bias tidak direset: swing-nya langsung jadi swing yang harus di-break untuk MSS lawan. Rantai low baru dimulai SETELAH MSS short, hanya untuk konfirmasi (struktur low) sebelum bias jadi Short. Bias Short kebalikannya. Fibonacci 100% tetap di ujung bias.
  MSS GAGAL (BS_PMFAIL_KEEP=1 default): kalau MSS yang menunggu struktur gagal (ujung MSS ter-break), rantai P bias tidak dihapus: P terakhir dipertahankan sehingga low/high baru yang melewatinya dihitung struktur (cara lama: kedua rantai dihapus dan P mulai dari nol, bisa membuat rantai terkunci berbulan-bulan).
  STRUKTUR H1 (BS_STRUCT_HIGHER=1 default): P high baru HARUS LEBIH TINGGI dari wick P high sebelumnya (Short: P low lebih rendah dari wick P low sebelumnya). 0 = cara lama (cukup menyentuh BODY P sebelumnya, MF_BODY).
  MSS M5 DARI PERTAMA KALI MASUK ZONA (BS_ZONE_FIRST=1 default): begitu harga pertama kali masuk zona, MSS langsung dicari (tetap dicari walau harga keluar zona). MSS hanya SAH kalau FVG sudah tersentuh sebelum MSS; kalau MSS keduluan = tidak valid, tunggu FVG disentuh lalu cari MSS lagi.
  PEMICU (BS_TRIGGER=fvg default): TIDAK cari low. Setelah harga masuk zona, tunggu FVG (sisa gap, di dalam zona) disentuh -> cari MSS M5 (P = low terdalam sejak masuk zona). Gagal = trade dari MSS itu kena SL -> tunggu FVG lain disentuh untuk cari MSS lagi (tiap FVG hanya dipakai sekali, tersentuh = terpakai). BS_TRIGGER=low = cara lama.
  ZONA LOW (BS_ZONE=1 default): low hanya jadi kandidat kalau berada DI BAWAH ujung bawah swing struktur terbaru (mis. MSS Long + 3 struktur bullish = swing low struktur ke-3) sampai ujung MSS. Short = cermin. Bias lama (BS_DUAL) menghitung struktur searahnya sendiri sejak bias live berganti.
  FVG (BS_FVG=1 default, Fibonacci dimatikan BS_FIB=0): cari FVG H1 dari awal MSS sampai titik tertinggi. BS_FVG_GAP=0 (default) = FRESH: gap belum dimasuki candle mana pun sesudah 3 candle FVG. BS_FVG_GAP=1 = yang MASIH ADA GAP-nya: boleh sudah terisi sebagian, zona valid = sisa gap. Low hanya jadi kandidat kalau ada FVG fresh DI BAWAH low (Short: di atas). Low tersentuh -> harus menyentuh FVG itu -> baru MSS M5 sah; MSS duluan = gugur, cari low lain.
  Env: BS_ENTRY (mss_m5|eng), BS_M5_N (1), BS_M5_SLBUF (0).

backtest_web.py -- MODE bias_sweep (NS_MODE=bias_sweep): TF struktur BS_TF (default 60 = H1), struktur hanya jadi BIAS, entry = limit setelah sweep + engulfing
  Bias (Long; Short = cermin): struktur P -> MSS seperti mode mss_flip. MSS baru mengubah bias kalau SESUDAH MSS ada minimal satu struktur searah MSS (BS_CONFIRM=1: P awal baru sesudah MSS lalu P2 menembus P awal; Long = swing high makin tinggi). Sebelum itu bias lama tetap; ujung MSS ter-break sebelum ada struktur = MSS gagal. Kalau ujung MSS di-break (wick menyentuh), bias berbalik ke arah sebelumnya
  (ujung bias baru = pergerakan terjauh sebelum break). Kalau ujung bias hasil balik itu di-break lagi, bias dikosongkan sampai ada MSS baru.
  Range = dari ujung bias sampai titik tertinggi (Long) / terendah (Short) sejak bias. Harga MENYENTUH titik tertinggi (Short: terendah) range = pencarian low direset dan dicari lagi dari candle sesudahnya (terus berulang sampai MSS lawan / bias berubah).
  Entry (bias Long): dari ujung atas range cari swing low (BS_N kiri-kanan) pertama = kandidat. Kalau ada candle CLOSE menembus level kandidat (BS_SWEEP=close; body = min(open,close)) low itu terbreak = gagal, cari low baru yang lebih bawah. Candle yang PERTAMA KALI menyentuh kandidat (wick, tanpa close menembus) = candle sweep; candle TEPAT sesudahnya HARUS engulfing
  (close di atas high candle sweep, low tidak di bawah low candle sweep) = setup. Tidak engulfing = low gagal, cari low lain yang lebih bawah. Limit di 50% body engulfing, SL di ujung wick candle sweep (BS_SL=wick, default), ujung wick candle engulfing (BS_SL=eng), atau 50% range candle sweep (BS_SL=mid), TP = titik tertinggi range. TP tersentuh sebelum limit terisi = batal.
  (limit juga dibatalkan kalau bias berubah). Satu posisi / satu limit pada satu waktu. Env: BS_TF (60), BS_N (1), MF_MIN_STRUCT, MF_EQUAL, MF_BODY, MF_SL_REV (balik bias saat ujung MSS di-break).
backtest_web.py -- STRATEGI: mss_flip (NS_MODE=mss_flip)
MODE mss_flip (M5 default, bisa MF_TF=15 dst, Long & Short, stop-and-reverse, TANPA TP). Alur (Long; Short = cermin):
  1) P awal boleh acak: swing low valid (MF_N=1 candle kiri & 1 kanan tidak melebihi; angka sama = tidak valid, MF_EQUAL=invalid). P berikutnya HANYA yang mengikuti P sebelumnya:
     swing low yang lebih rendah dari P terakhir (di-break/di-sweep) = P baru = struktur terbentuk. Swing low yang tidak lebih rendah diabaikan (bukan bagian struktur).
  2) Swing (referensi) = high tertinggi di antara P lama dan P baru, dihitung ulang tiap P baru. Minimal MF_MIN_STRUCT=1 struktur.
  3) Swing di-break = MSS: candle M5 pertama yang CLOSE di atas swing. Entry MARKET di close candle MSS. SL = ujung MSS (low terendah dari P sampai candle MSS). TANPA TP.
  4) Posisi keluar hanya lewat SL atau MSS LAWAN: begitu struktur lawan terbentuk (mis. setelah Long naik, bikin struktur naik lalu MSS Short), posisi lama ditutup
     di close candle MSS lawan (FLIP) dan langsung entry arah lawan. MSS searah saat posisi masih terbuka diabaikan. Setelah entry atau SL, kedua rantai P dimulai dari nol
     (P hanya dari candle sesudah entry/SL). R hasil = (exit - entry) / jarak SL, dikurangi fee. Posisi belum selesai di akhir data tidak dihitung.
  Env: MF_TF (5; 15 = M15), MF_N (1), MF_EQUAL (invalid|valid), MF_MIN_STRUCT (1), MF_FLIP (1; 0 = MSS lawan diabaikan, keluar hanya lewat SL).
backtest_web.py -- (strategi lama) acuan_mss
BOS (env NS_BOS=1, DEFAULT di mode mss_only): setelah MSS jangan langsung entry. Tunggu BOS: SH1 (swing ref MSS) tertembus SH2, SH2 tertembus SH3 (swing low harus ada di antara
SH2-SH3). Entry MARKET di close candle konfirmasi BOS (SH3 terkonfirmasi), SL di swing low BOS (Short: swing high). Gagal kalau ujung MSS (P) tertembus sebelum BOS. NS_BOS=0 = entry langsung di MSS.
TP struct1 (env NS_TP=struct1, DEFAULT utk mode mss_only): TP di ujung swing STRUKTUR PERTAMA. Lookback dari P1 (P valid pertama): P lama yang melebihi/menyamai
P terbaru menjadi batas (bukan bagian struktur); P-1 = swing pertama sesudah batas; TP = swing low (Short) / swing high (Long) dari P-1 s/d P1. NS_TP=rr -> TP 1:RR.
STRUKTUR (env NS_MIN_STRUCT, default 2): sebelum MSS boleh terjadi, harus ada minimal 2 struktur: P1 tertembus P2 (struktur 1), lalu P2 tertembus P3
(struktur 2). Baru setelah itu MSS dicek terhadap P terakhir. Boleh 3 struktur atau lebih, asal tidak cuma satu. NS_MIN_STRUCT=0 = cara lama (tanpa syarat struktur); 1 = cukup P1 tertembus P2.
MODE fibo_bos (env NS_MODE=fibo_bos, DEFAULT; M5 saja, Long & Short). Aturan: P lama harus di-BREAK BODY (close) oleh P baru, bukan cuma di-sweep wick;
  sedangkan swing low harus di-SWEEP wick (close tidak menembusnya). FB_BREAK_BODY=0 = P lama cukup dilewati wick/high.
  1) BOS BESAR (Long; Short = cermin): P lama ditembus P baru (swing high lebih tinggi), swing low valid di antaranya = L. Setelah P baru terkonfirmasi, L di-sweep WICK
     (low <= L, body/close tidak di bawah L; close < L = batal), lalu P baru di-break (close > P baru) => BOS besar. Ujung bawah = low terendah dari sweep s/d break.
  2) Dari ujung bawah cari rantai P1,P2,P3,... (swing high makin tinggi) terus melanjutkan, sampai swing low dari P terbaru TERSENTUH (setelah BOS besar terbentuk).
     Kalau ujung bawah diambil (low < ujung bawah) sebelum itu => batal.
  3) Fibonacci: 0% = ujung atas (high tertinggi sejak ujung bawah sampai sebelum sentuh), 100% = ujung bawah. Saat swing low tersentuh: LIMIT entry 75% (FB_ENTRY_DEPTH),
     SL 100%, TP -15% (FB_TP_EXT, di atas 0%). Limit dipasang setelah candle sentuh close; batal kalau TP tercapai sebelum terfill. FB_PAIR_MAX = jarak maks 2 P berurutan.
MODE (env NS_MODE):
  mss_only         : murni M5, tanpa level H1. Cari MSS (per arah, berurutan; MSS berikutnya dicari mulai candle MSS sebelumnya). MSS terbentuk ->
                     langsung entry MARKET di close candle MSS, SL ujung MSS (P), TP 1:RR (NS_ENTRY/NS_TP diabaikan). MSS_WINDOW = jendela pencarian (candle).
  touch (DEFAULT)  : level awal H1 langsung jadi ACUAN. Level tersentuh di M5 (Long: low <= level, Short: high >= level) -> langsung cari MSS M5
                     -> entry MARKET di close candle MSS, SL ujung MSS, TP 1:RR. Tanpa break-out.
  breakout_acuan   : level tertembus body H1 (break-out) -> MSS pertama (ujungnya jadi acuan) -> acuan tersentuh -> MSS kedua -> entry.
ENTRY (env NS_ENTRY):
  bo_bi (DEFAULT)  : setelah MSS jangan langsung entry. Tunggu ujung MSS (P) BREAK-OUT (body/close M5 menembus keluar), lalu BREAK-IN (close M5 kembali
                     ke dalam ujung itu). Entry MARKET di close candle break-in. SL = pergerakan terjauh di luar MSS dari break-out s/d break-in
                     (Long: low terendah, Short: high tertinggi). Kadaluarsa NS_EXPIRE_MIN (60) menit sejak break-out kalau tidak break-in.
                     TP (NS_TP=far, DEFAULT) = pergerakan terjauh dari MSS sebelum ujung MSS break-out (Long: high tertinggi dari candle MSS s/d candle break-out,
                     Short: low terendah). NS_TP=rr -> TP fix 1:RR. RR hasil jadi bervariasi per trade (ditampilkan 'RR target').
  mss              : entry MARKET langsung di close candle MSS, SL di ujung MSS.
Keterangan alur di bawah menjelaskan mode breakout_acuan; mode touch memakai langkah 1 lalu loncat ke langkah 4 (sentuh level) dan 5-6.

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
Endpoint: /  (dashboard) | /struktur.txt (download; struktur H1 tanpa trade: struktur, mss_long/mss_short, pembalikan arah; ?coin=XXX) | /trades.txt (DOWNLOAD; satu blok per trade, satu field per baris; ?view=1 = lihat di browser) | /ringkasan.txt (download; ?view=1) | /logs
Env: SYMBOLS (mis. FARTCOINUSDT,ETHFIUSDT), BACKTEST_START_DATE, BACKTEST_END_DATE, RR (3), RISK_PCT, INITIAL_BALANCE,
FEE_ENTRY_PCT, FEE_EXIT_PCT, LEVERAGE, MARGIN_USAGE_CAP, MAX_CONCURRENT (kosong/0 = tanpa batas),
NS_MODE (fibo_bos|touch|breakout_acuan|mss_only), FB_ENTRY_DEPTH (0.786), FB_TP_MODE (body|ext), FB_P_MODE (pairs|chain), FB_BREAK_BODY (1), FB_SW_EQUAL (valid|merge|invalid), FB_TRACK_MAX, FB_TRACK_CAP, FB_TP_EXT (0.15), FB_PAIR_MAX (500), NS_MIN_STRUCT (2), NS_BOS (1; hanya mss_only), NS_TP (far|rr|struct1), NS_STRUCT_LOOKBACK (1000), ONE_POS_PER_DIR (1; 0 = boleh banyak posisi searah), MSS_WINDOW (3000), NS_ENTRY (bo_bi|mss), NS_TP (far|rr), NS_EXPIRE_MIN (60), NS_LV_N (5), NS_LV_EQUAL (valid), NS_P_SWING (1), NS_MSS_SWING (1), NS_LOOKBACK (100), NS_P_EQUAL / NS_SW_EQUAL (merge), NS_MSS_REF (range).
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
MAX_CONCURRENT   = float('inf') if _mc in ('', '0', 'unlimited', 'inf') else int(_mc)

NS_MSS_SWING = int(os.environ.get('NS_MSS_SWING', 1))      # swing fractal M5: N candle kiri & kanan
NS_P_SWING   = int(os.environ.get('NS_P_SWING', 1))        # P valid M5: N candle kiri & kanan tidak melampaui P
NS_LOOKBACK  = int(os.environ.get('NS_LOOKBACK', 100))     # swing boleh dari N candle M5 sebelum candle awal pencarian MSS
NS_SW_EQUAL  = os.environ.get('NS_SW_EQUAL', 'merge').strip().lower()
NS_P_EQUAL   = os.environ.get('NS_P_EQUAL', 'merge').strip().lower()
NS_MSS_REF   = os.environ.get('NS_MSS_REF', 'fractal').strip().lower()
NS_MODE      = os.environ.get('NS_MODE', 'bias_sweep').strip().lower()      # touch (default) = level tersentuh M5 -> MSS | breakout_acuan = break-out -> MSS1 jadi acuan -> MSS2
NS_ENTRY     = os.environ.get('NS_ENTRY', 'bo_bi').strip().lower()     # bo_bi (default) = tunggu ujung MSS break-out lalu break-in, entry market di break-in | mss = entry market langsung di close MSS
NS_TP        = os.environ.get('NS_TP', 'far').strip().lower()          # far (default) = TP di pergerakan terjauh dari MSS sebelum ujung MSS break-out | rr = TP fix 1:RR
NS_EXPIRE_MIN = int(os.environ.get('NS_EXPIRE_MIN', 60))             # kadaluarsa (menit) sejak break-out ujung MSS kalau belum break-in
SEPARATE_COINS  = os.environ.get('SEPARATE_COINS', '1').strip() not in ('0', 'false', 'no')   # 1 (default) = backtest TERPISAH per koin, modal INITIAL_BALANCE sendiri-sendiri | 0 = satu akun gabungan (saldo, margin, slot dipakai bersama)
ONE_POS_PER_DIR = os.environ.get('ONE_POS_PER_DIR', '1').strip() not in ('0', 'false', 'no')   # 1 posisi per arah per koin (sinyal searah dilewati selama posisi terbuka)
MSS_WINDOW   = int(os.environ.get('MSS_WINDOW', 3000))            # mode mss_only: jendela pencarian MSS (candle M5) per percobaan
NS_MIN_STRUCT = int(os.environ.get('NS_MIN_STRUCT', 2))              # minimal jumlah struktur sebelum MSS boleh (P1 tertembus P2 = 1, P2 tertembus P3 = 2). 0 = cara lama (MSS boleh tanpa struktur), 1 = cukup P1 tertembus P2
NS_STRUCT_LOOKBACK = int(os.environ.get('NS_STRUCT_LOOKBACK', 1000))   # NS_TP=struct1: lookback (candle M5) ke belakang dari P1 utk mencari awal struktur pertama
NS_BOS       = os.environ.get('NS_BOS', '1').strip() not in ('0', 'false', 'no')   # mode mss_only: setelah MSS tunggu BOS (SH1->SH2->SH3), entry market di konfirmasi BOS, SL swing low BOS
FB_ENTRY_DEPTH = float(os.environ.get('FB_ENTRY_DEPTH', '0.786'))       # mode fibo_bos: limit entry di kedalaman 78.6% (0% = ujung atas BOS besar, 100% = ujung bawah)
FB_TP_MODE   = os.environ.get('FB_TP_MODE', 'body').strip().lower()     # body (default) = TP di ujung BODY atas BOS besar | ext = TP di -FB_TP_EXT% di atas 0%
FB_TP_EXT    = float(os.environ.get('FB_TP_EXT', '0.15'))               # (FB_TP_MODE=ext) TP di -15% (15% dari range, DI ATAS ujung atas / 0%)
FB_P_MODE    = os.environ.get('FB_P_MODE', 'pairs').strip().lower()     # pairs (default) = tiap 2 P berurutan yang naik jadi pasangan | chain = hanya rantai P yang terus naik
FB_SW_EQUAL  = os.environ.get('FB_SW_EQUAL', 'valid').strip().lower()   # P/swing low: valid = ujung yang tidak DILEBIHI kiri-kanan (angka sama boleh) | merge/invalid = strikt
FB_BREAK_BODY = os.environ.get('FB_BREAK_BODY', '1').strip() not in ('0', 'false', 'no')   # P lama harus di-BREAK BODY (close) oleh P baru, bukan cuma wick/sweep. Swing low tetap harus di-sweep wick
FB_TRACK_MAX = int(os.environ.get('FB_TRACK_MAX', 1500))                # mode pairs: umur maks sebuah pasangan (candle M5)
FB_TRACK_CAP = int(os.environ.get('FB_TRACK_CAP', 40))                  # mode pairs: jumlah maks pasangan aktif paralel
FB_PAIR_MAX  = int(os.environ.get('FB_PAIR_MAX', 500))                  # jarak maks (candle M5) antar 2 P berurutan utk dianggap satu struktur
MF_N         = int(os.environ.get('MF_N', 1))                    # mss_flip: P valid = N candle kiri & N kanan tidak melebihi
MF_EQUAL     = os.environ.get('MF_EQUAL', 'invalid').strip().lower()   # invalid = angka sama dgn tetangga bukan P | valid = sama boleh
MF_MIN_STRUCT = int(os.environ.get('MF_MIN_STRUCT', 1))             # minimal struktur (P tertembus P baru) sebelum MSS boleh
BS_ZONE_FIRST = os.environ.get('BS_ZONE_FIRST', '1') == '1'                   # pemicu fvg: 1 (default) = begitu PERTAMA KALI masuk zona langsung cari MSS M5 (tetap dicari walau harga keluar zona); MSS baru SAH kalau FVG sudah tersentuh sebelumnya (MSS yang keduluan = tidak valid, tunggu FVG disentuh -> cari MSS lagi). 0 = tunggu FVG disentuh dulu baru cari MSS
BS_M5_STRICT_SW = os.environ.get('BS_M5_STRICT_SW', '1') == '1'            # mss_m5: 1 (default) = seperti H1: MSS sah hanya setelah minimal BS_M5_MINSTRUCT struktur (P baru yang menembus P sebelumnya), dan swing yang dibreak = swing DI ANTARA P sebelumnya dan P terakhir (struktur terakhir). Kalau di antaranya tidak ada swing valid, MSS belum bisa (tidak memakai swing lama / swing sesudah P). 0 = cara lama
BS_M5_MINSTRUCT = int(os.environ.get('BS_M5_MINSTRUCT', 1))             # mss_m5: minimal struktur sebelum MSS sah (dipakai jika BS_M5_STRICT_SW=1)
BS_OC_SEED    = os.environ.get('BS_OC_SEED', '1') == '1'                   # BS_DUAL: rantai P bias lama MELANJUTKAN rantai terakhirnya saat bias berganti (struktur baru harus melewati P terakhirnya). 0 = rantai bias lama dimulai dari nol (bisa membuat struktur 'sendiri')
BS_TXT_NP     = int(os.environ.get('BS_TXT_NP', 6))                       # TXT trade: berapa P terakhir (rantai struktur H1) yang ditampilkan di bagian Bias H1
BS_PMFAIL_KEEP = os.environ.get('BS_PMFAIL_KEEP', '1') == '1'              # strict: saat MSS yang menunggu struktur GAGAL (ujung MSS ter-break), rantai P bias TIDAK dihapus: P terakhir dipertahankan, jadi low/high baru yang melewatinya langsung dihitung struktur (mis. P 0.03965 lalu low 0.0385 = struktur). 0 = cara lama (kedua rantai dihapus, P dimulai dari nol)
BS_STRUCT_HIGHER = os.environ.get('BS_STRUCT_HIGHER', '1') == '1'          # struktur H1 bias_sweep: P baru HARUS LEBIH TINGGI dari wick P sebelumnya (Short: lebih rendah) -> P high ditembus P lebih high. 0 = cara lama (P baru cukup menyentuh BODY P sebelumnya, MF_BODY)
MF_BODY      = os.environ.get('MF_BODY', '1').strip() not in ('0', 'false', 'no')   # P2,P3,... (bukan P awal): P baru harus menyentuh ujung BODY P sebelumnya (bukan wick). 0 = wick
MF_SL_REV    = os.environ.get('MF_SL_REV', '1').strip() not in ('0', 'false', 'no')   # posisi hasil MSS kena SL (= ujung MSS ter-break) -> entry lawan arah di level itu, SL di pergerakan terjauh sebelum break
MF_TF        = int(os.environ.get('MF_TF', 5))                   # timeframe mss_flip dalam menit: 5 (default) atau kelipatan 5 (mis. 15), diresample dari data M5
BS_TF        = int(os.environ.get('BS_TF', 60))                  # bias_sweep: timeframe (menit) diresample dari M5; 60 = H1
BS_SL        = os.environ.get('BS_SL', 'wick').strip().lower()    # bias_sweep: eng = SL di ujung wick candle ENGULFING (Long: low, Short: high) | wick = ujung wick candle sweep | mid = 50% range candle sweep
BS_ENTRY     = os.environ.get('BS_ENTRY', 'mss_m5').strip().lower()   # mss_m5 (default) = low H1 tersentuh -> cari MSS di M5 -> entry market | eng = cara lama (sweep + candle engulfing, limit 50% body)
BS_M5_ENTRY  = os.environ.get('BS_M5_ENTRY', 'limit_sw').strip().lower()   # mss_m5: limit_sw (default) = limit di swing yang di-break | market = market di close MSS
BS_DUAL      = os.environ.get('BS_DUAL', '1') == '1'                       # bias DUA ARAH: bias Long dan Short sama-sama hidup. Bias live (terbaru, dari MSS+struktur H1) menentukan MSS H1; bias lama (arah lawan) TETAP cari low/high -> MSS M5 -> entry, TP di titik tertinggi (Long) / terendah (Short) range-nya sendiri. 0 = cara lama (hanya 1 bias, bias lama dibuang saat bias berganti)
BS_DUAL_PM   = os.environ.get('BS_DUAL_PM', '1') == '1'                    # BS_DUAL=1: 1 (default) = TIDAK ada blokir: walau MSS lawan sudah terjadi (menunggu struktur konfirmasi) pencarian entry bias live TETAP jalan (mode dua bias); 0 = bias live diblok saat MSS lawan menunggu seperti cara lama
BS_M5_ENDBREAK = os.environ.get('BS_M5_ENDBREAK', '0') == '1'            # mss_m5: 1 = ujung bias tersentuh mengakhiri/membalik bias (cara lama); 0 (default) = TIDAK. Bias hanya selesai kalau titik tertinggi range tercapai atau H1 MSS+struktur melawan bias
BS_M5_SWFRAC = os.environ.get('BS_M5_SWFRAC', '0') == '1'                # mss_m5: 0 (default) = swing bebas: titik terjauh di antara P sebelumnya dan P terakhir (Long: high tertinggi; Short: low terendah), TANPA syarat kiri-kanan; 1 = swing MSS wajib kiri-kanan N (fractal); 0 = swing bebas = high tertinggi (Short: low terendah) antara P lama dan P baru. Aturan P (kiri-kanan N) tetap.
BS_M5_SLMODE = os.environ.get('BS_M5_SLMODE', 'end').strip().lower()   # mss_m5: end (default) = SL di ujung MSS | low_mss = SL di low M5 (kiri 1 kanan 1) terdekat ke belakang dari candle break, kalau tidak ada = ujung MSS
BS_TRIGGER   = os.environ.get('BS_TRIGGER', 'fvg')                         # mss_m5: pemicu pencarian MSS M5. 'fvg' (default) = TIDAK cari low: setelah harga masuk zona, tunggu FVG (yang masih ada gap-nya, di dalam zona) disentuh -> cari MSS M5; kalau gagal (trade dari MSS itu kena SL) tunggu FVG lain. 'low' = cara lama (cari low H1 kandidat -> tersentuh -> FVG -> MSS)
BS_ZONE      = os.environ.get('BS_ZONE', '1') == '1'                       # mss_m5: low (Long) HANYA jadi kandidat kalau berada DI BAWAH ujung bawah swing struktur terbaru (struktur searah bias yang terakhir), sampai ujung MSS. Short = cermin (high di atas ujung atas swing struktur terbaru, sampai ujung MSS). 0 = semua low di bawah titik tertinggi
BS_FVG_GAP   = os.environ.get('BS_FVG_GAP', '0') == '1'                   # FVG: 0 (default) = FVG FRESH (gap belum dimasuki candle mana pun sesudah 3 candle FVG); 1 = FVG yang MASIH ADA GAP-nya (boleh sudah terisi sebagian; zona valid = sisa gap yang belum tersentuh, selama belum tertutup penuh). 0 = FVG fresh (gap belum dimasuki sama sekali)
BS_FVG       = os.environ.get('BS_FVG', '1') == '1'                       # mss_m5: FVG fresh (H1) dari awal MSS sampai titik tertinggi. Low kandidat hanya dipakai kalau ada FVG fresh DI BAWAH-nya (Short: di atas). Setelah low tersentuh, harga harus menyentuh FVG itu dulu, baru MSS M5 sah. MSS duluan = gugur, cari low lain
BS_FIB       = os.environ.get('BS_FIB', '0') == '1'                       # mss_m5: Fibonacci pada struktur H1. 100% = ujung bawah struktur H1 terbaru (P baru menembus P lama; Short: ujung atas), 0% = titik tertinggi (Short: terendah). Low hanya dicari di kedalaman >= BS_FIB_DEPTH
BS_FIB_DEPTH = float(os.environ.get('BS_FIB_DEPTH', 0.618))                 # kedalaman minimum low (0.5 = 50% range)
BS_WARMUP    = int(os.environ.get('BS_WARMUP', 100))                      # mss_m5: N candle H1 pertama tiap koin TIDAK boleh ada trade (data awal, pergerakan kecil). Struktur/bias tetap dihitung; low yang tersentuh saat warm-up dianggap terpakai
BS_M5_N      = int(os.environ.get('BS_M5_N', 1))                   # mss_m5: P dan swing M5 = N candle kiri & N kanan
BS_M5_MSS2   = os.environ.get('BS_M5_MSS2', '0') == '1'                 # mss_m5: 1 (default) = setelah MSS-1 JANGAN entry; tunggu ujung MSS tersentuh lalu cari MSS-2 (swing = high tertinggi dari awal break MSS-1 s/d ujung tersentuh; kalau bikin struktur bearish lagi, swing dihitung ulang) | 0 = entry setelah MSS-1
BS_M5_SLREF  = os.environ.get('BS_M5_SLREF', 'wick').strip().lower()      # mss_m5 (SLMODE=end): wick (default) = SL di ujung wick MSS | body = di ujung BODY candle ujung MSS (Long: min(open,close) candle low terendah; Short: max)
BS_M5_MINRR  = float(os.environ.get('BS_M5_MINRR', 0))                     # mss_m5: RR rencana minimum (entry limit, SL, TP). Di bawah ini TIDAK trade (limit tidak dipasang). 0 = tanpa filter
BS_M5_SLBUF  = float(os.environ.get('BS_M5_SLBUF', 0))             # mss_m5: buffer SL di luar ujung MSS (dalam % harga, 0 = tepat di ujung)
BS_SWEEP     = os.environ.get('BS_SWEEP', 'close').strip().lower()  # bias_sweep: low dianggap TERBREAK (bukan sweep) kalau close candle menembus levelnya (close) | atau body menembus (body)
_bt_ = os.environ.get('BS_TRACE', '').strip()
_BS_TRACE = tuple(int(x) for x in _bt_.split(',')) if _bt_ else None   # debug saja
_BS_LOG = []
_STRUCT_EV = {}
BS_CONFIRM   = int(os.environ.get('BS_CONFIRM', 1))               # bias_sweep: bias baru baru berlaku setelah MSS DIIKUTI minimal N struktur searah MSS (P2 menembus P awal sesudah MSS). 0 = bias langsung berubah saat MSS
BS_STRICT    = os.environ.get('BS_STRICT', '1') == '1'                  # mss_m5: 1 (default) = rantai H1 satu arah: bias Long hanya cari P high (struktur bullish) -> MSS hanya short; bias Short hanya P low -> MSS hanya long. Rantai lawan baru jalan setelah MSS, hanya untuk konfirmasi struktur. 0 = dua rantai selalu jalan (lama)
BS_N         = int(os.environ.get('BS_N', 1))                    # bias_sweep: swing N kiri & N kanan (rantai P dan pencarian low/high entry)
MF_FLIP      = os.environ.get('MF_FLIP', '1').strip() not in ('0', 'false', 'no')   # MSS lawan menutup posisi & entry arah lawan
NS_LV_N      = int(os.environ.get('NS_LV_N', 5))                  # filter level: ujung wick terpanjang c1/c2 -> N candle kiri & kanan tidak melebihi (0 = matikan)
NS_LV_EQUAL  = os.environ.get('NS_LV_EQUAL', 'valid').strip().lower()  # valid = angka sama TIDAK dianggap melebihi | invalid = angka sama ditolak

if NS_MODE == 'mss_only':          # murni M5: MSS terbentuk -> entry market di close MSS, SL ujung MSS, TP 1:RR (tanpa level/break-out/break-in)
    NS_ENTRY = 'mss'; NS_TP = 'rr' if NS_TP == 'rr' else 'struct1'      # default mss_only: TP di ujung swing struktur pertama (NS_TP=rr -> TP 1:RR)

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
_coin_res = []


def _entry_desc():
    if NS_MODE == 'bias_sweep' and BS_ENTRY == 'mss_m5':
        return "bias H1 dari struktur/MSS; low H1 tersentuh -> cari MSS di M5 (swing 1 kiri-1 kanan antara ujung bawah M5 s/d candle sentuh; kalau P bawah ditembus P baru, swing dihitung ulang) -> " + ("entry market di close MSS" if BS_M5_ENTRY == 'market' else "entry LIMIT di swing yang di-break (batal kalau TP tersentuh dulu)") + ", SL ujung MSS, TP titik tertinggi/terendah range"
    if NS_MODE == 'bias_sweep':
        return f"bias dari struktur/MSS → limit 50% body engulfing setelah sweep low/high, SL {'di ujung wick candle engulfing' if BS_SL == 'eng' else 'di ujung wick candle sweep' if BS_SL == 'wick' else '50% range candle sweep'}, TP titik tertinggi/terendah range"
    if NS_MODE == 'mss_flip':
        return 'MSS (swing antara P lama-P baru di-break close) → entry market di close MSS, SL ujung MSS, TANPA TP; keluar hanya lewat SL atau MSS lawan (flip)'
    if NS_MODE == 'fibo_bos':
        return (f'Fibonacci dari ujung atas (0%) ke ujung bawah (100%) BOS besar; swing low P tersentuh → limit entry {FB_ENTRY_DEPTH*100:.1f}%, '
                f'SL 100%, ' + ('TP di ujung body atas BOS besar' if FB_TP_MODE == 'body' else f'TP -{FB_TP_EXT*100:.0f}% (di atas 0%)'))
    if NS_ENTRY == 'bo_bi':
        tp = 'TP = pergerakan terjauh dari MSS sebelum ujungnya break-out' if NS_TP == 'far' else f'TP 1:{RR:g}'
        return (f"ujung MSS break-out lalu break-in (maks {NS_EXPIRE_MIN} menit) → entry market di break-in, "
                f"SL pergerakan terjauh di luar MSS, {tp}")
    if NS_MODE == 'mss_only' and NS_BOS:
        return 'MSS → tunggu BOS (SH1→SH2→SH3) → entry market di konfirmasi BOS, SL swing low BOS, ' + ('TP di ujung swing struktur pertama (P-1 s/d P1)' if NS_TP == 'struct1' else f'TP 1:{RR:g}')
    return f"entry market di close MSS, SL ujung MSS, " + ('TP di ujung swing struktur pertama (P-1 s/d P1)' if NS_TP == 'struct1' else f'TP 1:{RR:g}')


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
    Return (idx candle MSS, idx P valid, idx candle swing yang ditembus, idx terakhir kesatuan P, idx P valid PERTAMA) / None."""
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
    Pv = None; Pv_last = None; rref = None; P1_first = None     # P1_first = P valid PERTAMA (awal rantai struktur)
    nstruct = 0         # jumlah STRUKTUR: berapa kali P valid tertembus P valid yang lebih ekstrem (P1->P2 = 1, P2->P3 = 2). MSS baru boleh kalau nstruct >= NS_MIN_STRUCT
    t0 = tj0 + 1
    if resume is not None:     # lanjut setelah MSS gagal: P baru = ekstrem yang menembus P lama
        t_new, Pv, Pv_last, rref = resume
        nstruct = 1; P1_first = Pv
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
            if Pv is not None:
                nstruct += 1                            # P valid lama tertembus P valid baru = 1 struktur
            if Pv is None:
                P1_first = cand
            Pv = cand; Pv_last = cand_last
        if Pv != cand:
            continue
        if nstruct < NS_MIN_STRUCT:
            continue            # struktur belum cukup (mis. min 2: P1 tertembus P2, P2 tertembus P3), belum boleh MSS
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
            return t, cand, ref, cand_last, P1_first
    return None


def _ns_find_bos(sup, tj0, q, P, ref, slv, stop, H5, L5):
    """BOS M5 setelah MSS (candle q) -- dipakai NS_ENTRY_MODE='bos_swinglow'. Long (Short = cermin):
      SH1 = swing high referensi MSS (ref). SH2 = swing high fractal (NS_MSS_SWING kiri-kanan) pertama yang terbentuk di/setelah candle MSS dan
      lebih tinggi dari SH1 (SH1 tertembus SH2). SH3 = swing high fractal berikutnya yang lebih tinggi dari SH2 (SH2 tertembus SH3).
      SWING LOW = low TERENDAH di antara SH2 dan SH3 (candle di antaranya); harus swing fractal NS_MSS_SWING kiri-kanan juga.
      Kalau SWING LOW tidak valid -> SH3 menjadi SH2 yang baru, lanjut cari SH3 berikutnya (rantai).
      BOS terbentuk saat SH3 terkonfirmasi (candle kanan ke-N closed); limit entry dipasang di harga SWING LOW setelah itu.
      GAGAL kalau sebelum BOS terbentuk P (ujung MSS) tertembus ekstrem yang lebih jauh: MSS tidak jadi konfirmasi, alur P-swing-MSS dilanjutkan (cari MSS berikutnya).
    Return ('ok', {conf, sh2, sh3, sl, entry, fi}) | ('gagal', idx candle yang menembus P) | None (belum ada BOS sampai stop)."""
    N = NS_MSS_SWING
    hi = min(stop, len(H5))
    lo = max(tj0 - NS_LOOKBACK, 0)
    ah, al = (H5, L5) if sup else (L5, H5)          # ah: sisi swing high (Short: low), al: sisi swing low (Short: high)
    hs, hf = _ns_fractals(ah, lo, hi, N, sup, NS_SW_EQUAL)
    ls, lf = _ns_fractals(al, lo, hi, N, not sup, NS_SW_EQUAL)
    beats = (lambda a, b: a > b) if sup else (lambda a, b: a < b)
    bos = None; sh2 = None
    for e in hs:
        f = hf[e]
        if f < q:
            continue
        v = float(ah[f])
        if sh2 is None:
            if beats(v, float(ah[ref])):
                sh2 = (f, e)
            continue
        if not beats(v, float(ah[sh2[0]])):
            continue
        a, b = sh2[1] + 1, f - 1
        slx = None
        if a <= b:
            m = float(al[a:b + 1].min() if sup else al[a:b + 1].max())
            for e2 in ls:
                f2 = lf[e2]
                if f2 < a:
                    continue
                if f2 > b:
                    break
                if float(al[f2]) == m:
                    slx = f2; break
        if slx is not None:
            bos = {'conf': e + N, 'sh2': sh2[0], 'sh3': f, 'sl': slx, 'entry': float(al[slx])}
            break
        sh2 = (f, e)                                # swing low tidak valid -> SH3 jadi SH2 baru
    fi = None
    if q + 1 < hi:
        seg = (L5[q + 1:hi] < L5[P]) if sup else (H5[q + 1:hi] > H5[P])        # P tertembus ekstrem baru
        if seg.any():
            fi = q + 1 + int(seg.argmax())
    if bos is not None and (fi is None or fi > bos['conf']):
        bos['fi'] = fi              # candle pertama yang menembus P setelah BOS terbentuk (None = belum pernah sampai stop)
        return 'ok', bos
    if fi is not None:
        return 'gagal', fi
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


def _first_close(sup, C5, start, tip, outside=True):
    """Index candle M5 pertama (>= start) yang BODY (close) menembus tip ke luar: Long close < tip, Short close > tip."""
    n5 = len(C5); s = start
    while s < n5:
        seg = C5[s:s + 4096]
        w = np.flatnonzero(seg < tip) if sup else np.flatnonzero(seg > tip)
        if len(w):
            return s + int(w[0])
        s += 4096
    return None


def tp_first_structure(sup, P1, Pn, H5, L5):
    """TP di ujung swing STRUKTUR PERTAMA.
    Contoh struktur naik (P = high; entry Short): P-2 0.120, P-1 0.105, P1 0.110, P2 0.115, P3 0.120 (P3 = P terbaru/ujung MSS).
    Lookback dari P1 ke belakang: struktur yang benar-benar pertama = rantai P lama yang TIDAK melebihi (>=) P terbaru. P-2 (0.120 >= 0.120) bukan bagian
    struktur -> batas. P-1 = swing (fractal) pertama sesudah batas -> awal/ujung struktur. TP = swing low (Short) / swing high (Long) dari P-1 sampai P1.
    Kalau tidak ada swing sebelum P1 (P-1 = P1): pakai rentang dari candle sesudah batas sampai P1.
    Long (P = low, struktur turun) adalah cermin: batas = low <= P terbaru, TP = high tertinggi dari P-1 sampai P1.
    Return (tp, idx awal struktur) / (None, None) kalau tidak valid."""
    n5 = len(H5); NP = NS_P_SWING
    lo = max(0, P1 - NS_STRUCT_LOOKBACK)
    if sup:
        w = np.flatnonzero(L5[lo:P1] <= L5[Pn])
    else:
        w = np.flatnonzero(H5[lo:P1] >= H5[Pn])
    b = lo + int(w[-1]) if len(w) else lo - 1                 # candle batas (P lama yang melebihi/menyamai P terbaru); tidak ada -> awal lookback
    start = P1
    for j in range(b + 1, P1):
        if j - NP < 0 or j + NP >= n5:
            continue
        if sup:
            if L5[j] < L5[j - NP:j].min() and L5[j] < L5[j + 1:j + NP + 1].min():
                start = j; break
        else:
            if H5[j] > H5[j - NP:j].max() and H5[j] > H5[j + 1:j + NP + 1].max():
                start = j; break
    a = start if start != P1 else max(b + 1, 0)
    if a > P1:
        return None, None
    tp = float(H5[a:P1 + 1].max() if sup else L5[a:P1 + 1].min())
    return tp, a


def _first_idx(arr, start, thr, ge):
    """Index pertama >= start dengan arr >= thr (ge=True) atau arr <= thr (ge=False). None kalau tidak ada."""
    n = len(arr); s = start
    while s < n:
        seg = arr[s:s + 4096]
        w = np.flatnonzero(seg >= thr) if ge else np.flatnonzero(seg <= thr)
        if len(w):
            return s + int(w[0])
        s += 4096
    return None


class _FbChain:
    """Rantai P (swing high yang saling menembus ke atas) + swing low di antara 2 P terakhir."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.Qf = None; self.Pf = None; self.Pe = None; self.conf = None; self.Pv = None
        self.L = None; self.Li = None; self.swept = False; self.sweep_i = None; self.hist = []

    def _set(self, qf, f, e, j, h, L, Li):
        self.hist.append(f)
        self.Qf = qf; self.Pf = f; self.Pe = e; self.conf = j; self.Pv = float(h[f])
        self.L = L; self.Li = Li; self.swept = False; self.sweep_i = None

    def new_high(self, f, e, j, h, l, lowfirst, st=None, c=None):
        if self.Pf is None:
            self._set(None, f, e, j, h, None, None); return
        if not (h[f] > self.Pv):
            return                                   # swing high lebih rendah dari P terbaru: abaikan
        if FB_BREAK_BODY and c is not None and not (c[self.Pe + 1:f + 1].max() > self.Pv):
            if st is not None:
                st['fb_wickonly'] += 1
            return                                   # P lama cuma dilewati wick (sweep), belum di-break body: bukan struktur
        L = Li = None
        if f - self.Pf <= FB_PAIR_MAX:
            a, b = self.Pe + 1, f - 1
            if a <= b:
                seg = l[a:b + 1]; m = seg.min()
                for x in (a + np.flatnonzero(seg == m)).tolist():
                    if x in lowfirst:                # swing low harus fractal valid
                        L, Li = float(m), x; break
        if st is not None:
            st['fb_pair' if L is not None else 'fb_pair_noL'] += 1
        self._set(self.Pf if L is not None else None, f, e, j, h, L, Li)


def _fibo_dir(symbol, sup, sg, TS5, h, l, c, st, o=None):
    """Long pada (h, l, c) apa adanya. Short = cermin: h=-low, l=-high, c=-close, harga dikembalikan dgn sg=-1.
    P = ujung candle yang tidak dilebihi N candle kiri & kanan (FB_SW_EQUAL=valid: angka sama tidak dianggap melebihi). Tiap P = kandidat P awal.
    FASE A (BOS besar): P lama di-BREAK BODY oleh P baru (ada candle close di atas P lama; FB_BREAK_BODY=1) dengan swing low valid di antaranya = L. Setelah P baru terkonfirmasi: L di-sweep WICK (low<=L, close>=L;
      close < L = batal) lalu P baru di-break BODY (close > P baru) => BOS besar. Ujung bawah = low terendah dari sweep s/d break.
      FB_P_MODE=pairs: setiap 2 P berurutan yang naik (P lama = P tepat sebelumnya) membentuk satu pasangan, semua dilacak paralel.
      FB_P_MODE=chain: hanya rantai P yang terus naik (P lebih rendah dari P terbaru diabaikan).
    FASE B: dari ujung bawah cari rantai P1,P2,P3... (swing high makin tinggi) terus sampai swing low P terbaru tersentuh SETELAH BOS besar terbentuk.
      Ujung bawah diambil (low < ujung bawah) sebelum itu => batal. Pemicu: Fibonacci dari ujung atas (0%) ke ujung bawah (100%):
      limit entry 75%, SL 100%, TP -15% (di atas 0%). Limit dipasang setelah candle pemicu close; batal kalau TP tercapai dulu."""
    n = len(h); N = NS_P_SWING
    hs, hf = _ns_fractals(h, 0, n, N, True, FB_SW_EQUAL)
    ls, lf = _ns_fractals(l, 0, n, N, False, FB_SW_EQUAL)
    conf_h = {}
    for e in hs:
        conf_h.setdefault(e + N, []).append((hf[e], e))
    lowfirst = set(lf.values())
    pairs_mode = (FB_P_MODE == 'pairs')
    out = []
    A = _FbChain(); trk = []; lastP = None; j = 0
    while j < n:
        bos = None
        if pairs_mode:
            for (f, e) in conf_h.get(j, ()):
                if lastP is not None and h[f] > h[lastP[0]] and f - lastP[0] <= FB_PAIR_MAX and FB_BREAK_BODY and not (c[lastP[1] + 1:f + 1].max() > h[lastP[0]]):
                    st['fb_wickonly'] += 1            # P lama cuma dilewati wick (sweep), belum di-break body
                elif lastP is not None and h[f] > h[lastP[0]] and f - lastP[0] <= FB_PAIR_MAX:
                    a_, b_ = lastP[1] + 1, f - 1
                    got = False
                    if a_ <= b_:
                        seg = l[a_:b_ + 1]; m = seg.min()
                        for x in (a_ + np.flatnonzero(seg == m)).tolist():
                            if x in lowfirst:
                                trk.append([lastP[0], f, e, j, float(h[f]), float(m), x, False, None]); got = True; break
                    st['fb_pair' if got else 'fb_pair_noL'] += 1
                lastP = (f, e)
            if trk:
                alive = []
                for tk in trk:
                    if j < tk[3]:
                        alive.append(tk); continue
                    if c[j] < tk[5]:
                        st['fb_closebreak'] += 1; continue          # swing low di-BREAK body: batal
                    if l[j] <= tk[5] and not tk[7]:
                        tk[7] = True; tk[8] = j; st['fb_sweep'] += 1  # swing low di-sweep wick
                    if c[j] > tk[4]:
                        if tk[7]:
                            if bos is None:
                                bos = tk
                        else:
                            st['fb_nosweep'] += 1                     # P ditembus tanpa sweep: pasangan ini tidak jadi BOS besar
                        continue
                    if j - tk[3] > FB_TRACK_MAX:
                        continue
                    alive.append(tk)
                trk = alive[-FB_TRACK_CAP:]
            if bos is None:
                j += 1; continue
            qf, pf, pv, Lsw, sw_i, Lsw_i = bos[0], bos[1], bos[4], bos[5], bos[8], bos[6]
        else:
            for (f, e) in conf_h.get(j, ()):
                A.new_high(f, e, j, h, l, lowfirst, st, c)
            if A.Pf is None or j < A.conf:
                j += 1; continue
            if A.L is not None:
                if c[j] < A.L:
                    st['fb_closebreak'] += 1; A.reset(); j += 1; continue
                if l[j] <= A.L and not A.swept:
                    A.swept = True; A.sweep_i = j; st['fb_sweep'] += 1
            if c[j] > A.Pv:
                if A.swept and A.L is not None:
                    qf, pf, pv, Lsw, sw_i, Lsw_i = A.Qf, A.Pf, A.Pv, A.L, A.sweep_i, A.Li
                else:
                    if A.L is not None:
                        st['fb_nosweep'] += 1
                    A.L = None; j += 1; continue
            else:
                j += 1; continue
        # ---- BOS besar terbentuk di candle j ----
        st['fb_bos'] += 1
        j0 = j
        b = sw_i + int(np.argmin(l[sw_i:j0 + 1])); bottom = float(l[b])
        B = _FbChain(); trig = None; jj = b + 1
        while jj < n:
            if l[jj] < bottom:
                break                                 # ujung bawah (100%) diambil sebelum pemicu
            for (f, e) in conf_h.get(jj, ()):
                if f > b:
                    B.new_high(f, e, jj, h, l, lowfirst, None, c)
            if B.Pf is not None and B.L is not None and jj >= B.conf and l[jj] <= B.L:
                if jj > j0:
                    trig = jj; break
                B.L = None                            # swing low sudah tersentuh sebelum BOS besar terbentuk: tidak berlaku
            jj += 1
        A.reset(); trk = []; lastP = None
        if trig is None:
            if jj < n:
                st['fb_invalid'] += 1
            j = jj + 1; continue
        jt = trig; st['fb_trigger'] += 1
        ti = b + int(np.argmax(h[b:jt])); top = float(h[ti]); R = top - bottom
        Ltr, Lti = B.L, B.Li
        j = jt + 1
        if R <= 0:
            continue
        entry_t = bottom + (1.0 - FB_ENTRY_DEPTH) * R
        tp_ts_ = None
        if FB_TP_MODE == 'body':
            bt_ = np.maximum(o[b:jt], c[b:jt]); kb = int(np.argmax(bt_))     # ujung BODY atas (max open/close) di BOS besar
            tp_t = float(bt_[kb]); tp_ts_ = int(TS5[b + kb])
        else:
            tp_t = top + FB_TP_EXT * R
        if tp_t <= entry_t:
            st['tp_invalid'] += 1; continue
        fi = _first_idx(l, jt + 1, entry_t, False)    # fill: low <= limit
        tpi = _first_idx(h, jt + 1, tp_t, True)       # TP tercapai
        if fi is None:
            st['fb_nofill'] += 1; continue
        if tpi is not None and tpi < fi:
            st['fb_cancel'] += 1; continue
        brk_ts_ = brk_cl_ = None
        if qf is not None:
            wk = np.flatnonzero(c[qf + 1:pf + 1] > h[qf])
            if len(wk):
                brk_ts_ = int(TS5[qf + 1 + int(wk[0])]); brk_cl_ = sg * float(c[qf + 1 + int(wk[0])])
        entry = sg * entry_t; sl = sg * bottom; tp = sg * tp_t
        dist = abs(entry - sl)
        if dist <= 0:
            continue
        cd = dict(symbol=symbol, sup=sup, d='Long' if sup else 'Short', mode='fibo_bos', lvl=0.0, formed=None, bo=None, mss1=None, acuan=None,
                  touch=None, mss=None, bo_m5=None, bi_m5=None, ptime=None, entry=entry, sl=sl, tp=tp, rr=abs(tp - entry) / dist, dist=dist,
                  t=fi, entry_ts=int(TS5[fi]),
                  fb=dict(p_old=(int(TS5[qf]) if qf is not None else None), p_new=int(TS5[pf]), p_new_px=sg * pv, L_sweep=sg * Lsw,
                          sweep_ts=int(TS5[sw_i]), bos_ts=int(TS5[j0]), bottom_ts=int(TS5[b]), bottom_px=sg * bottom, top_ts=int(TS5[ti]),
                          top_px=sg * top, L_trig=sg * Ltr, L_trig_ts=int(TS5[Lti]), trig_ts=int(TS5[jt]), fill_ts=int(TS5[fi]),
                          p_old_px=(sg * float(h[qf]) if qf is not None else None), L_sw_ts=(int(TS5[Lsw_i]) if Lsw_i is not None else None),
                          sweep_px=sg * float(l[sw_i]), sweep_close=sg * float(c[sw_i]), bos_close=sg * float(c[j0]),
                          chain=[(int(TS5[x]), sg * float(h[x])) for x in B.hist], trig_px=sg * float(l[jt]),
                          tp_ts=tp_ts_, range=abs(top - bottom), brk_ts=brk_ts_, brk_close=brk_cl_))
        if l[fi] <= bottom:                           # candle fill juga menembus SL: dianggap langsung SL
            cd['ex_override'] = (fi, sl, 'SL')
        out.append(cd)
        st['signal'] += 1
    return out


def fibo_signals(symbol, TS5, H5, L5, C5, st, O5=None):
    O5 = C5 if O5 is None else O5
    return (_fibo_dir(symbol, True, 1.0, TS5, H5, L5, C5, st, O5) +
            _fibo_dir(symbol, False, -1.0, TS5, -L5, -H5, -C5, st, -O5))


# ============================================================
# MODE mss_flip: struktur P -> MSS -> entry market, SL ujung MSS, tanpa TP, balik arah saat MSS lawan
# ============================================================
def _mf_swing_at(arr, j, N, sup, lo):
    """Swing valid di candle j. sup=True: swing LOW (low lebih rendah dari N kiri & N kanan); sup=False: swing HIGH.
    MF_EQUAL=invalid: angka sama dgn tetangga = bukan swing. Candle kiri paling jauh (j-N) tidak boleh sebelum indeks lo (awal rantai)."""
    if j - N < lo or j + N >= len(arr):
        return False
    v = arr[j]
    for k in range(1, N + 1):
        a = arr[j - k]; b = arr[j + k]
        if sup:
            if (a <= v or b <= v) if MF_EQUAL == 'invalid' else (a < v or b < v):
                return False
        else:
            if (a >= v or b >= v) if MF_EQUAL == 'invalid' else (a > v or b > v):
                return False
    return True


def mssflip_signals(symbol, TS5, H5, L5, C5, st, O5):
    """Rantai P per arah. sup=True: rantai swing LOW makin rendah -> MSS Long (close di atas swing high di antara P lama & P baru).
    sup=False: rantai swing HIGH makin tinggi -> MSS Short. Sekali entry / SL: kedua rantai direset (P hanya dari candle sesudahnya)."""
    n = len(C5); N = MF_N
    for k in ('mf_rev', 'mf_p', 'mf_struct', 'mf_mss', 'mf_flip', 'mf_sl', 'mf_same', 'mf_nodist'):
        st.setdefault(k, 0)
    new_chain = lambda reset: dict(reset=reset, p=None, first=None, prev=None, ns=0, sw=None, sw_px=None)
    ch = {True: new_chain(0), False: new_chain(0)}
    pos = None; out = []

    def close_pos(t, px, why):
        gr = ((px - pos['entry']) if pos['sup'] else (pos['entry'] - px)) / pos['dist']
        out.append(dict(symbol=symbol, sup=pos['sup'], d='Long' if pos['sup'] else 'Short', mode='mss_flip', entry=pos['entry'], sl=pos['sl'], tp=None,
                        dist=pos['dist'], rr=gr, gross_r=gr, why=why, t=pos['t'], entry_ts=int(TS5[pos['t']]), exit_ts=int(TS5[t]), exit_px=float(px), exit_idx=t,
                        **pos['info']))

    for t in range(n):
        if pos is not None and t > pos['t']:                      # SL dicek duluan (sebelum MSS di close candle yang sama)
            hit = (L5[t] <= pos['sl']) if pos['sup'] else (H5[t] >= pos['sl'])
            if hit:
                prev = pos; sl_px = prev['sl']
                close_pos(t, sl_px, 'SL'); pos = None; st['mf_sl'] += 1
                ch = {True: new_chain(t), False: new_chain(t)}
                if MF_SL_REV and prev['kind'] == 'mss':
                    # ujung MSS ter-break (SL) -> entry lawan arah di level ujung MSS. SL = pergerakan terjauh (Long gagal -> high tertinggi, Short gagal -> low terendah)
                    # dari P (ujung MSS) sampai candle SEBELUM candle break
                    seg = H5[prev['p_idx']:t] if prev['sup'] else L5[prev['p_idx']:t]
                    k_ = int(np.argmax(seg) if prev['sup'] else np.argmin(seg)); ext = float(seg[k_])
                    dist_r = (ext - sl_px) if prev['sup'] else (sl_px - ext)
                    if dist_r > 0:
                        pos = dict(sup=not prev['sup'], t=t, entry=float(sl_px), sl=ext, dist=dist_r, kind='rev', p_idx=prev['p_idx'],
                                   info=dict(kind='rev', brk_level=float(sl_px), ext_ts=int(TS5[prev['p_idx'] + k_]), ext_px=ext, from_ts=int(TS5[prev['t']])))
                        st['signal'] += 1; st['mf_rev'] += 1
        sigs = []
        for sup in (True, False):
            c = ch[sup]; arr = L5 if sup else H5; j = t - N
            if j >= 0 and _mf_swing_at(arr, j, N, sup, c['reset']):
                st['mf_p'] += 1
                if c['p'] is None:
                    c['p'] = j; c['first'] = j                                   # P awal (acak, asal N kiri & N kanan)
                elif (lambda a_, body_: (arr[j] <= (min(O5[a_], C5[a_]) if body_ else arr[a_])) if sup else (arr[j] >= (max(O5[a_], C5[a_]) if body_ else arr[a_])))(c['p'], MF_BODY and c['p'] != c['first']):
                    # struktur: P baru menyentuh P lama. P awal -> ujung wick; P2,P3,... -> ujung BODY P sebelumnya (MF_BODY=1)
                    a = c['p']
                    c['touch_px'] = float((min(O5[a], C5[a]) if sup else max(O5[a], C5[a])) if (MF_BODY and a != c['first']) else arr[a])
                    c['touch_kind'] = 'body' if (MF_BODY and a != c['first']) else 'wick'
                    seg_arr = H5 if sup else L5
                    lo_, hi_ = (a + 1, j) if j - a > 1 else (a, j + 1)
                    seg = seg_arr[lo_:hi_]
                    k_ = int(np.argmax(seg) if sup else np.argmin(seg))
                    c['sw'] = lo_ + k_; c['sw_px'] = float(seg[k_])
                    c['prev'] = a; c['p'] = j; c['ns'] += 1; st['mf_struct'] += 1
                # selain itu: swing tidak mengikuti P sebelumnya -> diabaikan
            if c['sw'] is not None and c['ns'] >= MF_MIN_STRUCT and ((C5[t] > c['sw_px']) if sup else (C5[t] < c['sw_px'])):
                sigs.append(sup)
        for sup in sigs:
            c = ch[sup]
            sl = float(L5[c['p']:t + 1].min()) if sup else float(H5[c['p']:t + 1].max())      # ujung MSS
            entry = float(C5[t]); dist = (entry - sl) if sup else (sl - entry)
            info = dict(p_first_ts=int(TS5[c['first']]), p_prev_ts=int(TS5[c['prev']]), p_ts=int(TS5[c['p']]), p_px=float(L5[c['p']] if sup else H5[c['p']]),
                        sw_ts=int(TS5[c['sw']]), sw_px=c['sw_px'], ns=c['ns'], mss_ts=int(TS5[t]), touch_px=c.get('touch_px'), touch_kind=c.get('touch_kind'))
            st['mf_mss'] += 1
            if pos is not None and pos['sup'] == sup:                          # MSS searah saat posisi terbuka: diabaikan
                st['mf_same'] += 1; ch[sup] = new_chain(t); continue
            if dist <= 0:
                st['mf_nodist'] += 1; ch[sup] = new_chain(t); continue
            if pos is not None:                                                # MSS lawan = flip
                if not MF_FLIP:
                    ch[sup] = new_chain(t); continue
                close_pos(t, entry, 'FLIP'); st['mf_flip'] += 1
            info['kind'] = 'mss'
            pos = dict(sup=sup, t=t, entry=entry, sl=sl, dist=dist, kind='mss', p_idx=c['p'], info=info)
            st['signal'] += 1
            ch = {True: new_chain(t), False: new_chain(t)}
            break
    if pos is not None:                                                        # belum selesai di akhir data
        px = float(C5[n - 1]); gr = ((px - pos['entry']) if pos['sup'] else (pos['entry'] - px)) / pos['dist']
        out.append(dict(symbol=symbol, sup=pos['sup'], d='Long' if pos['sup'] else 'Short', mode='mss_flip', entry=pos['entry'], sl=pos['sl'], tp=None,
                        dist=pos['dist'], rr=gr, gross_r=gr, why=None, t=pos['t'], entry_ts=int(TS5[pos['t']]), exit_ts=None, exit_px=px, exit_idx=n - 1, **pos['info']))
    return out


# ============================================================
# MODE bias_sweep: struktur = bias saja; entry limit setelah sweep + engulfing di dalam range
# ============================================================
def _tf_arrays(m5df, tf):
    ts = m5df['ts'].values.astype(np.int64)
    if tf == 5:
        return (ts,) + tuple(m5df[c].values.astype(float) for c in ('open', 'high', 'low', 'close'))
    step = tf * 60000
    d = m5df.assign(_g=ts // step).groupby('_g').agg(ts=('ts', 'first'), open=('open', 'first'), high=('high', 'max'), low=('low', 'min'), close=('close', 'last'), n=('ts', 'count'))
    d = d[d['n'] == tf // 5].reset_index(drop=True)                 # hanya candle TF yang lengkap
    d['ts'] = (d['ts'] // step) * step
    return (d['ts'].values.astype(np.int64),) + tuple(d[c].values.astype(float) for c in ('open', 'high', 'low', 'close'))


def biassweep_signals(symbol, TS, O, H, L, C, st, M5=None, ev=None):
    n = len(C); N = BS_N
    def TR(kind, ts, **kw):                                                   # debug: BS_TRACE=awal,akhir (ms epoch UTC) -> catat keputusan bot
        if _BS_TRACE is not None and _BS_TRACE[0] <= ts <= _BS_TRACE[1]:
            _BS_LOG.append(dict(kind=kind, t=int(ts), **kw))
    def E(**kw):                                                              # log kejadian struktur H1 (hanya kalau ev diberikan)
        if ev is not None:
            ev.append(kw)
    m5mode = (BS_ENTRY == 'mss_m5' and M5 is not None and BS_TF > 5)
    strict = m5mode and BS_STRICT
    dual = m5mode and BS_DUAL
    fvgz = m5mode and BS_TRIGGER == 'fvg'
    endbrk = BS_M5_ENDBREAK and not dual            # dual: ujung bias tidak mengakhiri bias
    if m5mode:
        TSm, Om, Hm, Lm, Cm = M5; NM = BS_M5_N
    for k in ('fvgz_first', 'pmfail_keep', 'fvgz_touch', 'fvgz_fail', 'fvgz_sl', 'fvgz_busy', 'zone_skip_cand', 'zone_drop', 'bs_p', 'bs_struct', 'bs_mss', 'bs_bias', 'bs_flipback', 'bs_clear', 'bs_sweep', 'bs_engulf', 'bs_setup', 'bs_cancel_tp', 'bs_cancel_bias', 'bs_fill', 'bs_pend_end', 'bs_cand_fail', 'bs_top_reset', 'bs_refresh', 'bs_eng_fail', 'bs_eng_wick', 'bs_pm', 'bs_pm_ok', 'bs_pm_fail', 'bs_pm_cancel', 'm5_touch', 'm5_touch_busy', 'm5_mss1', 'm5_wait_touch', 'm5_rr_skip', 'fib_skip_touch', 'warm_skip', 'm5_cancel_pm', 'pm_block', 'fvg_skip_cand', 'fvg_touch', 'fvg_mss_first', 'm5_newp', 'm5_noswing', 'm5_mss', 'm5_mss_skip', 'm5_cancel_top', 'm5_cancel_end', 'm5_cancel_bias'):
        st.setdefault(k, 0)
    new_chain = lambda reset: dict(reset=reset, p=None, first=None, prev=None, ns=0, sw=None, sw_px=None, hist=[])
    ch = {True: new_chain(0), False: new_chain(0)}
    bias = None; pend = None; pos = None; out = []; pm = None; trk = None
    # DUA ARAH: slot per arah (Long=True, Short=False). Variabel bias/trk/pend/pos = konteks slot yang sedang dimuat (cur). live = arah bias terbaru.
    S = {True: dict(bias=None, trk=None, pend=None, pos=None), False: dict(bias=None, trk=None, pend=None, pos=None)}
    live = None; cur = None

    def ctx_save():
        if cur is not None:
            S[cur].update(bias=bias, trk=trk, pend=pend, pos=pos)

    def ctx_load(d):
        nonlocal bias, trk, pend, pos, cur
        ctx_save()
        cur = d; s_ = S[d]
        bias = s_['bias']; trk = s_['trk']; pend = s_['pend']; pos = s_['pos']
          # pm = MSS yang menunggu struktur searah sebelum bias berubah

    def swing(sup, j, lo):
        return _mf_swing_at(L if sup else H, j, N, sup, lo)

    def set_bias(sup, kind, end, ext, ext_idx, p_idx, t, keep=None):
        nonlocal bias, pend, ch, pm, trk, live
        E(type='bias', sup=sup, kind=kind, prev=(None if bias is None else bias['sup']), end=float(end), ext=float(ext), ext_ts=int(TS[ext_idx]), t=int(TS[t]))
        if dual:                                                    # simpan konteks bias lama (tetap hidup di slot arahnya), muat slot arah bias baru (bias/limit/tracker lama di slot itu diganti; posisi terbuka tetap)
            src_ch_ = pm['chain'] if (pm is not None and pm['sup'] == sup and pm.get('chain') is not None) else ch.get(sup)   # rantai bias lama sampai saat MSS lawan terjadi
            ctx_load(sup); live = sup
            ob_ = S[not sup]['bias']
            if ob_ is not None and ob_.get('oc') is None:           # bias lama (arah lawan) MELANJUTKAN rantai P-nya sendiri (P terakhir tetap), bukan mulai dari nol
                if BS_OC_SEED and src_ch_ is not None:
                    oc_ = dict(src_ch_); oc_['hist'] = list(src_ch_['hist']); ob_['oc'] = oc_
                else:
                    ob_['oc'] = new_chain(t)
        if trk is not None:
            trk = None; st['m5_cancel_bias'] += 1
        pm = None
        if pend is not None:
            pend = None; st['bs_cancel_bias'] += 1
        bias = dict(sup=sup, kind=kind, end=float(end), ext=float(ext), ext_idx=int(ext_idx), p_idx=int(p_idx), cand=None, floor=None, touch=None, t=t, fib100=float(end), fib_src=None, zone=None, oc=None, cand_zone=None, fv=None, zin=None, zone_src=None)
        ch = {True: new_chain(t), False: new_chain(t)}
        if keep is not None and keep.get('sw') is not None and keep.get('ns', 0) >= 1:
            bias['zone_src'] = (int(keep['prev']), int(keep['p']), int(keep['sw']), int(keep['ns']), keep.get('touch_px'), keep.get('touch_kind'), tuple(keep['hist'][-8:]))
            bias['zone'] = float(keep['sw_px'])                    # ujung (bawah utk Long / atas utk Short) swing struktur terakhir yang mengkonfirmasi bias
        if keep is not None:                                        # strict: struktur yang MENGKONFIRMASI bias tetap dipakai (swing-nya yang harus di-break untuk MSS lawan), tidak ikut direset
            ch[not sup] = keep
        st['bs_bias'] += 1
        for tt in (range(ext_idx + 1, t) if not fvgz else ()):     # kandidat dari ujung atas (tanpa membuat setup dari masa lalu)
            cand_step(tt, False)

    def fib_range():
        """Range Fibonacci dari struktur H1. 100% = ujung bawah struktur H1 TERBARU: kalau sesudah bias terbentuk ada struktur baru (P menembus P sebelumnya) = low P baru itu, kalau lebih rendah dari ujung bias; selain itu ujung bias. Range melebar tiap struktur baru. 0% = titik tertinggi range (Short: terendah)."""
        if dual and cur != live:
            return None                                                           # Fibonacci hanya untuk bias live
        if strict:
            # Fibonacci pada struktur H1 AKTIF: 100% = ujung swing struktur TERBARU (swing yang harus di-break untuk MSS lawan). Struktur baru terbentuk -> 100% pindah ke swing struktur itu. 0% = titik tertinggi range (Short: terendah).
            c = ch[not bias['sup']]
            if c['sw'] is None or c['ns'] < 1:
                return None                                                       # belum ada struktur -> belum ada range
            return float(c['sw_px']), float(bias['ext']), int(c['sw']), int(c['ns'])
        return float(bias['fib100']), float(bias['ext']), bias['fib_src'], 0

    def fib_update():
        """Struktur H1 baru sesudah bias (P menembus P sebelumnya) dengan low lebih rendah (Short: lebih tinggi) dari 100% sekarang -> 100% pindah ke sana (range melebar). 100% tidak pernah menyempit."""
        sup = bias['sup']; arr = L if sup else H; c = ch[sup]
        if c['p'] is not None and c['ns'] >= 1:
            px = float(arr[c['p']])
            if (px < bias['fib100']) if sup else (px > bias['fib100']):
                bias['fib100'] = px; bias['fib_src'] = int(c['p'])

    def fib_depth(px):
        r_ = fib_range()
        if r_ is None or r_[0] == r_[1]:
            return None
        return (r_[1] - px) / (r_[1] - r_[0])

    def fib_ok(px):
        # kedalaman minimal BS_FIB_DEPTH; BOLEH melebihi 100% (asal MSS lawan belum terjadi lebih dulu)
        if not BS_FIB or (dual and cur != live):
            return True
        d_ = fib_depth(px)
        return d_ is not None and d_ >= BS_FIB_DEPTH - 1e-12

    def zone_ok(lvl):
        """Long: ujung MSS (end) <= low <= ujung bawah swing struktur terbaru (zone). Short: zone <= high <= end."""
        z = bias.get('zone')
        if (not BS_ZONE) or z is None:
            return True
        return (bias['end'] <= lvl <= z) if bias['sup'] else (z <= lvl <= bias['end'])

    def zone_set(z, src=None):
        bias['zone'] = float(z); bias['zone_src'] = src             # src = (P awal, P yang menembus, swing, nomor struktur) indeks H1
        if trk is None and bias['cand'] is not None and bias['sup'] is not None and not zone_ok(float((L if bias['sup'] else H)[bias['cand']])):
            bias['cand'] = None; st['zone_drop'] += 1              # struktur baru membuat zona turun/naik: kandidat lama di luar zona dibuang

    def old_chain_step(t):
        """Bias lama (bukan live): hitung struktur searah biasnya sendiri (Long: P high yang menembus P sebelumnya; swing = low di antaranya) supaya zona low-nya ikut struktur terbaru."""
        c = bias['oc']; sc = not bias['sup']; arr = L if sc else H; j = t - N
        if j >= 0 and _mf_swing_at(arr, j, N, sc, c['reset']):
            if c['p'] is None:
                c['p'] = j; c['first'] = j; c['hist'].append(int(j))
            else:
                a_ = c['p']; body_ = MF_BODY and a_ != c['first'] and not BS_STRUCT_HIGHER
                thr = (min(O[a_], C[a_]) if sc else max(O[a_], C[a_])) if body_ else arr[a_]
                if ((arr[j] < thr) if BS_STRUCT_HIGHER else (arr[j] <= thr)) if sc else ((arr[j] > thr) if BS_STRUCT_HIGHER else (arr[j] >= thr)):
                    sa = H if sc else L
                    lo_, hi_ = (a_ + 1, j) if j - a_ > 1 else (a_, j + 1)
                    seg = sa[lo_:hi_]; k_ = int(np.argmax(seg) if sc else np.argmin(seg))
                    c['sw'] = lo_ + k_; c['sw_px'] = float(seg[k_]); c['prev'] = a_; c['p'] = j; c['ns'] += 1; c['hist'].append(int(j))
                    zone_set(c['sw_px'], (int(a_), int(j), int(lo_ + k_), int(c['ns']), float(thr), 'body' if body_ else 'wick', tuple(c['hist'][-8:])))

    def fvg_target(sup, lvl, tt):
        """FVG fresh H1 terdekat DI BAWAH lvl (Long; bullish FVG: low[i+1] > high[i-1], zona = high[i-1]..low[i+1]) atau DI ATAS lvl (Short; bearish FVG). 3 candle FVG ada di leg dari awal MSS (ujung bias) sampai titik tertinggi/terendah. Fresh (BS_FVG_GAP=0) = tidak ada candle lain (sesudah 3 candle FVG sampai candle H1 ke-tt) yang masuk ke gap. BS_FVG_GAP=1 (default): gap boleh sudah terisi sebagian; zona valid = sisa gap (edge = ujung terdalam yang sudah dimasuki harga), tertutup penuh = tidak valid. Edge = sisi zona yang pertama dikenai harga (Long: atas zona; Short: bawah zona)."""
        p0 = bias['p_idx']; e1 = bias['ext_idx']
        if e1 - p0 < 2:
            return None
        seg = (L if sup else H)[p0:e1 + 1]
        hit = np.where(seg == bias['end'])[0]
        st_i = p0 + (int(hit[0]) if len(hit) else 0)
        best = None
        for i in range(st_i + 1, e1):
            if sup:
                edge = float(L[i + 1]); far = float(H[i - 1])
                if edge <= far:
                    continue
                if BS_FVG_GAP:                                                     # sisa gap: far .. min(edge, low terendah sesudah FVG). Tertutup penuh (low <= far) = tidak valid
                    ml_ = float(L[i + 2:tt + 1].min()) if i + 2 <= tt else edge
                    if ml_ <= far:
                        continue
                    e_ = min(edge, ml_)
                    if e_ >= lvl:
                        continue
                    if best is None or e_ > best['edge']:
                        best = dict(edge=e_, far=far, i=i, edge0=edge)
                    continue
                if edge >= lvl:
                    continue
                fresh = (i + 2 > tt) or (float(L[i + 2:tt + 1].min()) > edge)
                if fresh and (best is None or edge > best['edge']):
                    best = dict(edge=edge, far=far, i=i)
            else:
                edge = float(H[i + 1]); far = float(L[i - 1])
                if edge >= far:
                    continue
                if BS_FVG_GAP:
                    mh_ = float(H[i + 2:tt + 1].max()) if i + 2 <= tt else edge
                    if mh_ >= far:
                        continue
                    e_ = max(edge, mh_)
                    if e_ <= lvl:
                        continue
                    if best is None or e_ < best['edge']:
                        best = dict(edge=e_, far=far, i=i, edge0=edge)
                    continue
                if edge <= lvl:
                    continue
                fresh = (i + 2 > tt) or (float(H[i + 2:tt + 1].max()) < edge)
                if fresh and (best is None or edge < best['edge']):
                    best = dict(edge=edge, far=far, i=i)
        if best is not None:
            best['ts'] = int(TS[best['i']])
        return best

    def cand_step(tt, live):
        """Satu langkah pencarian low/high di range bias pada candle tt.
        Kandidat = swing low (Short: swing high). Candle yang PERTAMA KALI menyentuh kandidat (wick) = candle sweep A. Kalau A close menembus level = terbreak -> gagal.
        Candle tepat sesudah A (tt = A+1) HARUS engulfing (close di atas high A, dan low-nya tidak di bawah low A = A tetap swing 1 kiri 1 kanan). Kalau tidak engulfing -> low gagal.
        Low gagal -> cari low lain yang LEBIH BAWAH dari low yang gagal (Short: lebih atas)."""
        nonlocal pend
        sup = bias['sup']; a = L if sup else H; j = tt - N
        if m5mode:
            # mode mss_m5: sentuhan low dicek di M5 (di loop utama). Di sini hanya replay masa lalu: low yang sudah tersentuh sebelum bias terbentuk dianggap terpakai.
            c0 = bias['cand']
            if (not live) and c0 is not None and tt > c0 and ((L[tt] <= a[c0]) if sup else (H[tt] >= a[c0])):
                bias['floor'] = float(a[c0]); bias['cand'] = None
        # (1) candle sesudah candle sweep A harus engulfing
        A = bias['touch']
        if (not m5mode) and A is not None and tt == A + 1:
            bias['touch'] = None; c0 = bias['cand']; e = tt
            body_ok = (C[e] > H[A]) if sup else (C[e] < L[A])                                   # close body menembus ujung wick candle sweep
            if MF_EQUAL == 'valid':                                                            # wick engulfing tidak boleh melebihi wick candle sweep (sama persis boleh)
                wick_ok = (L[e] >= L[A]) if sup else (H[e] <= H[A])
            else:                                                                              # default: sama persis dianggap melebihi/tidak valid (seperti swing 1 kiri 1 kanan)
                wick_ok = (L[e] > L[A]) if sup else (H[e] < H[A])
            if live and body_ok and not wick_ok:
                st['bs_eng_wick'] += 1
            eng = body_ok and wick_ok
            if eng:
                if live:
                    st['bs_engulf'] += 1
                    lim = (O[e] + C[e]) / 2.0; slp = ((L[e] if sup else H[e]) if BS_SL == 'eng' else (L[A] if sup else H[A]) if BS_SL == 'wick' else (H[A] + L[A]) / 2.0)
                    tp = max(bias['ext'], float(H[e])) if sup else min(bias['ext'], float(L[e]))
                    if pend is None and pos is None and ((tp > lim > slp) if sup else (tp < lim < slp)):
                        rr = abs(tp - lim) / abs(lim - slp)
                        pend = dict(sup=sup, limit=float(lim), sl=float(slp), tp=float(tp), rr=rr, t=tt,
                                    info=dict(bias_kind=bias['kind'], bias_end=bias['end'], cand_ts=int(TS[c0]), cand_px=float(a[c0]), sw_ts=int(TS[A]), sw_lo=float(L[A]), sw_hi=float(H[A]),
                                              eng_ts=int(TS[e]), eng_o=float(O[e]), eng_c=float(C[e]), set_ts=int(TS[tt])))
                        st['bs_setup'] += 1
                bias['cand'] = A                                       # low yang menyapu jadi kandidat berikutnya
            else:
                if live:
                    st['bs_eng_fail'] += 1
                bias['floor'] = float(a[c0]); bias['cand'] = None      # tidak engulfing = low gagal
        # (2) candle yang pertama kali menyentuh kandidat
        c0 = bias['cand']
        if (not m5mode) and c0 is not None and bias['touch'] is None and tt > c0:
            lvl = a[c0]
            if (L[tt] <= lvl) if sup else (H[tt] >= lvl):
                if sup:
                    bad = (min(O[tt], C[tt]) if BS_SWEEP == 'body' else C[tt]) < lvl
                else:
                    bad = (max(O[tt], C[tt]) if BS_SWEEP == 'body' else C[tt]) > lvl
                if bad:                                                   # close/body menembus = terbreak, bukan sweep wick
                    if live:
                        st['bs_cand_fail'] += 1
                    bias['floor'] = float(lvl); bias['cand'] = None
                else:
                    if live:
                        st['bs_sweep'] += 1
                    bias['touch'] = tt                                    # tunggu candle berikutnya: harus engulfing
        # (3) cari kandidat (swing low/high) baru
        if bias['cand'] is None and bias['touch'] is None and j >= 0 and swing(sup, j, bias['ext_idx']):
            fl = bias['floor']
            if not (fl is None or ((a[j] < fl) if sup else (a[j] > fl))):
                TR('cand', TS[tt], j_ts=int(TS[j]), px=float(a[j]), why='DITOLAK: tidak lebih ' + ('bawah' if sup else 'atas') + f' dari floor {fl}')
            elif m5mode and not fib_ok(float(a[j])):
                TR('cand', TS[tt], j_ts=int(TS[j]), px=float(a[j]), why='DITOLAK: Fibonacci')
            elif m5mode and not zone_ok(float(a[j])):
                if live:
                    st['zone_skip_cand'] += 1
                TR('cand', TS[tt], j_ts=int(TS[j]), px=float(a[j]), why='DITOLAK: di luar zona (' + ('harus di bawah ujung bawah swing struktur terbaru' if sup else 'harus di atas ujung atas swing struktur terbaru') + f' {bias.get("zone")}, sampai ujung MSS {bias["end"]})', live=live)
            else:                                                                 # kandidat baru harus lebih bawah (Long) / lebih atas (Short) dari low yang gagal
                tg_ = fvg_target(sup, float(a[j]), tt) if (m5mode and BS_FVG) else None
                if m5mode and BS_FVG and tg_ is None:
                    if live:
                        st['fvg_skip_cand'] += 1                                  # tidak ada FVG fresh di bawah low ini: bukan kandidat
                    TR('cand', TS[tt], j_ts=int(TS[j]), px=float(a[j]), why='DITOLAK: tidak ada FVG fresh ' + ('di bawah' if sup else 'di atas') + ' level ini', live=live)
                else:
                    bias['cand'] = j; bias['floor'] = None; bias['cand_fvg'] = tg_; bias['cand_zone'] = bias.get('zone')
                    TR('cand', TS[tt], j_ts=int(TS[j]), px=float(a[j]), why='JADI KANDIDAT', fvg=(None if tg_ is None else (tg_['edge'], tg_['far'], tg_['ts'])), live=live)

    def close_pos(p, t, px, why):
        if why == 'SL' and p['info'].get('trig') == 'fvg':
            st['fvgz_sl'] += 1                                      # MSS dari FVG ini kena SL = gagal: tunggu FVG lain
        gr = ((px - p['entry']) if p['sup'] else (p['entry'] - px)) / p['dist']
        TSx = TSm if p.get('m5') else TS
        out.append(dict(symbol=symbol, sup=p['sup'], d='Long' if p['sup'] else 'Short', mode='bias_sweep', entry=p['entry'], sl=p['sl'], tp=p['tp'], dist=p['dist'],
                        rr=p['rr'], gross_r=gr, why=why, t=p['t'], entry_ts=int(TSx[p['t']]), exit_ts=(int(TSx[t]) if why else None), exit_px=float(px), exit_idx=t, bs_m5=bool(p.get('m5')), **p['info']))


    def m5_best_swing(sup, a_i, b_i):
        """Swing M5 (NM kiri & NM kanan tidak melebihi) TERBAIK di antara indeks a_i dan b_i (eksklusif). Long: swing HIGH tertinggi; Short: swing LOW terendah. None kalau tidak ada yang valid."""
        arr = Hm if sup else Lm; best = None
        if not BS_M5_SWFRAC:
            if b_i - a_i < 2:
                return None
            seg = arr[a_i + 1:b_i]
            return a_i + 1 + int(np.argmax(seg) if sup else np.argmin(seg))
        for jj in range(a_i + 1, b_i):
            if _mf_swing_at(arr, jj, NM, not sup, 0):
                if best is None or ((arr[jj] > arr[best]) if sup else (arr[jj] < arr[best])):
                    best = jj
        return best

    def fv_rebuild(t):
        """Daftar FVG H1 yang MASIH ADA GAP-nya (sisa gap) di leg ujung MSS -> titik tertinggi, per candle H1 ke-t (inklusif)."""
        sup = bias['sup']; p0_ = bias['p_idx']; e1 = bias['ext_idx']; fv = {}
        if e1 - p0_ >= 2:
            ar = L if sup else H
            hit = np.where(ar[p0_:e1 + 1] == bias['end'])[0]
            st_i = p0_ + (int(hit[0]) if len(hit) else 0)
            tail = ar[st_i + 2:t + 1]
            rc = (np.minimum.accumulate(tail[::-1])[::-1] if sup else np.maximum.accumulate(tail[::-1])[::-1]) if len(tail) else tail
            for i in range(st_i + 1, e1):
                if i + 1 > t:
                    break
                kk = i - st_i
                if sup:
                    e0 = float(L[i + 1]); far = float(H[i - 1])
                    if e0 <= far:
                        continue
                    ml = float(rc[kk]) if kk < len(rc) else e0
                    if (ml <= far) if BS_FVG_GAP else (ml <= e0):                  # BS_FVG_GAP=0: FRESH (gap belum dimasuki candle mana pun); 1: masih ada sisa gap
                        continue
                    fv[i] = dict(edge=(min(e0, ml) if BS_FVG_GAP else e0), far=far, edge0=e0, ts=int(TS[i]), used=False)
                else:
                    e0 = float(H[i + 1]); far = float(L[i - 1])
                    if e0 >= far:
                        continue
                    mh = float(rc[kk]) if kk < len(rc) else e0
                    if (mh >= far) if BS_FVG_GAP else (mh >= e0):
                        continue
                    fv[i] = dict(edge=(max(e0, mh) if BS_FVG_GAP else e0), far=far, edge0=e0, ts=int(TS[i]), used=False)
        bias['fv'] = fv

    def fv_step(t):
        if bias.get('fv') is None:
            fv_rebuild(t); return
        sup = bias['sup']; fv = bias['fv']
        for i in list(fv):
            f = fv[i]
            if sup:
                if L[t] <= (f['far'] if BS_FVG_GAP else f['edge']):
                    del fv[i]
                elif L[t] < f['edge']:
                    f['edge'] = float(L[t])
            else:
                if H[t] >= (f['far'] if BS_FVG_GAP else f['edge']):
                    del fv[i]
                elif H[t] > f['edge']:
                    f['edge'] = float(H[t])

    def fvg_trigger(t, m):
        """Pemicu FVG. BS_ZONE_FIRST=1: pertama kali harga masuk zona -> tracker MSS M5 langsung mulai (tetap jalan walau harga keluar zona); FVG (sisa gap/fresh, di dalam zona) harus tersentuh SEBELUM MSS, kalau tidak MSS gugur (tidak valid) dan tunggu FVG disentuh -> cari MSS lagi. FVG yang sudah dipakai tidak dipakai lagi.
        BS_ZONE_FIRST=0: masuk zona -> tunggu FVG tersentuh -> baru tracker MSS mulai."""
        nonlocal trk
        sup = bias['sup']; fv = bias.get('fv')
        z = bias.get('zone') if BS_ZONE else None
        bend = bias['end']
        first = False
        if BS_ZONE_FIRST:
            if (Cm[m] < bend) if sup else (Cm[m] > bend):                          # close M5 di luar ujung MSS: bukan di dalam zona
                return
            if bias.get('zin') is None:
                if z is not None and not ((Lm[m] <= z) if sup else (Hm[m] >= z)):
                    return                                                         # belum pernah masuk zona
                bias['zin'] = m; first = True                                      # candle M5 PERTAMA masuk zona (tidak direset saat keluar zona)
        else:
            if z is not None and not ((Lm[m] <= z) if sup else (Hm[m] >= z)):
                bias['zin'] = None                                                 # di luar zona: harus masuk zona lagi
                return
            if (Cm[m] < bend) if sup else (Cm[m] > bend):
                bias['zin'] = None
                return
            if bias.get('zin') is None:
                bias['zin'] = m
        if first and trk is None and pos is None and pend is None:                 # T1: langsung cari MSS saat pertama kali masuk zona
            bias['tries'] = bias.get('tries', 0) + 1
            st['m5_touch'] += 1; st['fvgz_first'] += 1; st['m5_noswing'] += 1
            c0 = max(int(np.searchsorted(TS, TSm[m], 'right')) - 1, 0)
            trk = dict(sup=sup, c0=c0, T=m, p0=m, p=m, sw=None, nP=0, hist=[(m, None)], lvl=float((Lm if sup else Hm)[m]),
                       fvg=None, fvg_hit=False, need_fvg=True, try_no=bias['tries'], fib=(None, None, None, 0, None),
                       trig='fvg', start='zona', zone_at=z, zin=m, zone_src=bias.get('zone_src'))
            TR('touch', TSm[m], res='MASUK ZONA PERTAMA KALI -> tracker MSS mulai (MSS sah kalau FVG sudah tersentuh)', zone=z)
        if not fv:
            return
        best = None
        for i, f in fv.items():
            if f['used']:
                continue
            fe = max(f['far'], bend) if sup else min(f['far'], bend)               # gap dipotong oleh ujung MSS (zona berakhir di ujung MSS)
            up = f['edge'] if z is None else (min(f['edge'], z) if sup else max(f['edge'], z))
            if (fe >= up) if sup else (fe <= up):                                  # tidak ada irisan gap dengan zona
                continue
            trig = up
            if not ((Lm[m] <= trig) if sup else (Hm[m] >= trig)):                  # belum disentuh
                continue
            f['used'] = True                                                       # tersentuh = terpakai (tiap FVG hanya satu kali, termasuk yang tersentuh saat tracker/posisi masih ada)
            if (Hm[m] < fe) if sup else (Lm[m] > fe):                              # candle seluruhnya di luar gap (melompati gap): tidak ada sentuhan di dalam gap
                continue
            if best is None or ((trig > best[0]) if sup else (trig < best[0])):
                best = (trig, i)
        if best is None:
            return
        f = fv[best[1]]
        if trk is not None:
            if trk.get('need_fvg') and not trk['fvg_hit']:                         # FVG tersentuh SEBELUM MSS: MSS berikutnya sah
                trk['fvg'] = dict(edge=f['edge'], far=f['far'], edge0=f['edge0'], ts=f['ts']); trk['fvg_hit'] = True; trk['fvg_m'] = m
                st['fvgz_touch'] += 1; TR('trk', TSm[m], res='FVG tersentuh (sebelum MSS)', edge=f['edge'])
            return
        if pos is not None or pend is not None:
            st['fvgz_busy'] += 1; TR('touch', TSm[m], res='FVG tersentuh tapi dilewati (posisi/limit masih ada)', edge=f['edge']); return
        m_top = int(np.searchsorted(TSm, TS[bias['ext_idx']] + BS_TF * 60000, 'left'))
        a0 = min(max(bias['zin'], m_top), m)
        p0 = a0 + int(np.argmin(Lm[a0:m + 1]) if sup else np.argmax(Hm[a0:m + 1]))
        sw = m5_best_swing(sup, p0, m)
        if sw is None:
            st['m5_noswing'] += 1
        bias['tries'] = bias.get('tries', 0) + 1
        st['m5_touch'] += 1; st['fvgz_touch'] += 1
        c0 = max(int(np.searchsorted(TS, TSm[p0], 'right')) - 1, 0)
        trk = dict(sup=sup, c0=c0, T=m, p0=p0, p=p0, sw=sw, nP=0, hist=[(p0, sw)], lvl=float((Lm if sup else Hm)[p0]),
                   fvg=dict(edge=f['edge'], far=f['far'], edge0=f['edge0'], ts=f['ts']), fvg_hit=True, fvg_m=m, try_no=bias['tries'], fib=(None, None, None, 0, None),
                   trig='fvg', start='fvg', zone_at=z, zin=a0, zone_src=bias.get('zone_src'))
        TR('touch', TSm[m], res='FVG TERSENTUH -> TRACKER MSS MULAI', edge=f['edge'], far=f['far'], zone=z)

    def m5_start_trk(sup, c0, T):
        """Low H1 (kandidat c0) tersentuh di candle M5 ke-T. Ujung bawah M5 = low terendah M5 di dalam candle H1 c0; swing = high tertinggi (valid 1-1) dari ujung bawah itu sampai candle sentuh."""
        ms0 = int(np.searchsorted(TSm, TS[c0], 'left')); me0 = int(np.searchsorted(TSm, TS[c0] + BS_TF * 60000, 'left'))
        seg = Lm[ms0:me0] if sup else Hm[ms0:me0]
        p0 = ms0 + int(np.argmin(seg) if sup else np.argmax(seg))
        sw = m5_best_swing(sup, p0, T)
        if sw is None:
            st['m5_noswing'] += 1
        return dict(sup=sup, c0=c0, T=T, p0=p0, p=p0, sw=sw, nP=0, hist=[(p0, (sw if sw is not None else None))], lvl=float((Lm if sup else Hm)[p0]))

    def m5_step(m):
        """Satu candle M5 (indeks m) untuk tracker MSS. Urutan: batal? -> P baru (menembus P bawah) -> hitung ulang swing -> MSS (close menembus swing)?"""
        nonlocal trk, pos, pend
        k = trk; sup = k['sup']
        if (Hm[m] >= bias['ext']) if sup else (Lm[m] <= bias['ext']):                 # harga sampai titik tertinggi range: dicari ulang
            trk = None; bias['cand'] = None; bias['floor'] = None; st['m5_cancel_top'] += 1; TR('trk', TSm[m], res='tracker DIBATALKAN: harga sampai titik tertinggi/terendah range'); return
        if endbrk and ((Lm[m] <= bias['end']) if sup else (Hm[m] >= bias['end'])):                 # ujung bias tersentuh: bias akan berubah/kosong di akhir candle H1
            trk = None; bias['cand'] = None; st['m5_cancel_end'] += 1; return
        if k.get('wait'):                                                              # MSS-1 sudah terbentuk: tunggu ujung MSS-1 tersentuh
            if not ((Lm[m] <= k['uj_px']) if sup else (Hm[m] >= k['uj_px'])):
                return
            k['wait'] = False; k['T2'] = m; st['m5_wait_touch'] += 1
            k['p'] = k['uj_i']                                                         # P = ujung MSS-1
            k['sw'] = m5_best_swing(sup, k['m1'] - 1, m)                               # swing = high tertinggi dari awal break MSS-1 s/d ujung tersentuh
            k['sw2_0'] = k['sw']
        if k.get('fvg') is not None and not k['fvg_hit']:                                  # low sudah tersentuh: harus menyentuh FVG fresh dulu (dicek sebelum MSS di candle yang sama)
            if (Lm[m] <= k['fvg']['edge']) if sup else (Hm[m] >= k['fvg']['edge']):
                k['fvg_hit'] = True; k['fvg_m'] = m; st['fvg_touch'] += 1; TR('trk', TSm[m], res='FVG tersentuh', edge=k['fvg']['edge'])
        j = m - NM
        if j > k['p'] and _mf_swing_at(Lm if sup else Hm, j, NM, sup, k['p']):                # P baru (swing low 1-1) yang MENEMBUS P bawah sebelumnya
            if ((Lm[j] < Lm[k['p']]) if sup else (Hm[j] > Hm[k['p']])):
                nsw = m5_best_swing(sup, k['p'], j)
                k['p'] = j; k['nP'] += 1; st['m5_newp'] += 1
                if nsw is not None or BS_M5_STRICT_SW:                                 # strict: swing = swing struktur TERAKHIR saja (kosong kalau tidak ada swing valid di antara P)
                    k['sw'] = nsw
                k['hist'].append((j, k['sw']))
        if k.get('trig') == 'fvg' and k['sw'] is None and not BS_M5_STRICT_SW:         # belum ada swing: cari swing M5 pertama setelah P
            k['sw'] = m5_best_swing(sup, k['p'], m - NM + 1)
            if k['sw'] is not None:
                k['hist'][0] = (k['hist'][0][0], k['sw'])
        if k['sw'] is not None and (not BS_M5_STRICT_SW or k['nP'] >= BS_M5_MINSTRUCT) and ((Cm[m] > Hm[k['sw']]) if sup else (Cm[m] < Lm[k['sw']])):     # MSS: close M5 menembus swing
            if (k.get('fvg') is not None or k.get('need_fvg')) and not k['fvg_hit']:   # MSS keduluan sebelum menyentuh FVG: tidak valid (gugur), tunggu FVG disentuh
                st['fvg_mss_first'] += 1; TR('trk', TSm[m], res='GUGUR: MSS M5 terjadi sebelum FVG tersentuh', swing=float((Hm if sup else Lm)[k['sw']]), close=float(Cm[m]))
                bias['cand'] = None; bias['floor'] = float(k['lvl']); trk = None
                return
            if BS_M5_MSS2 and k.get('phase', 1) == 1:
                st['m5_mss1'] += 1
                uj_i = k['p'] + int(np.argmin(Lm[k['p']:m + 1]) if sup else np.argmax(Hm[k['p']:m + 1]))
                k.update(phase=2, wait=True, m1=m, uj_i=uj_i, uj_px=float((Lm if sup else Hm)[uj_i]), sw1=k['sw'], n1=len(k['hist']))
                return
            st['m5_mss'] += 1
            end_px = float(Lm[k['p']:m + 1].min()) if sup else float(Hm[k['p']:m + 1].max())
            ent = float(Cm[m]) if BS_M5_ENTRY == 'market' else float((Hm if sup else Lm)[k['sw']]); tp = float(bias['ext'])
            ref_px = end_px; ref_i = None; sl_basis = 'ujung MSS'
            if BS_M5_SLMODE != 'low_mss':
                ref_i = k['p'] + int(np.argmin(Lm[k['p']:m + 1]) if sup else np.argmax(Hm[k['p']:m + 1]))
                if BS_M5_SLREF == 'body':
                    ref_px = float(min(Om[ref_i], Cm[ref_i]) if sup else max(Om[ref_i], Cm[ref_i])); sl_basis = 'ujung body MSS'
            if BS_M5_SLMODE == 'low_mss':                                              # cari ke belakang dari candle break: low M5 kiri-NM kanan-NM terdekat (harus di bawah entry)
                for jj in range(m - NM, k['p'] - 1, -1):
                    if jj >= NM and _mf_swing_at(Lm if sup else Hm, jj, NM, sup, 0) and ((Lm[jj] < ent) if sup else (Hm[jj] > ent)):
                        ref_i = jj; ref_px = float((Lm if sup else Hm)[jj]); sl_basis = 'low M5'; break
            slp = ref_px * (1 - BS_M5_SLBUF / 100.0) if sup else ref_px * (1 + BS_M5_SLBUF / 100.0)
            ok = (tp > ent > slp) if sup else (tp < ent < slp)
            if ok and abs(tp - ent) / abs(ent - slp) < BS_M5_MINRR - 1e-12:               # RR rencana di bawah minimum: jangan trade
                ok = False; st['m5_rr_skip'] += 1
            TR('trk', TSm[m], res=('MSS M5 -> limit dipasang' if (ok and pos is None and pend is None) else 'MSS M5 tapi DIBUANG (RR/TP/SL tidak valid atau posisi masih ada)'), entry=ent, sl=float(slp), tp=tp)
            if ok and pos is None and pend is None:
                swp = k['sw']
                info = dict(strict_sw=BS_M5_STRICT_SW, start=k.get('start'), zone_src=(None if k.get('zone_src') is None else dict(prev_ts=int(TS[k['zone_src'][0]]), prev_px=float((H if k['sup'] else L)[k['zone_src'][0]]), p_ts=int(TS[k['zone_src'][1]]), p_px=float((H if k['sup'] else L)[k['zone_src'][1]]), sw_ts=int(TS[k['zone_src'][2]]), sw_px=float((L if k['sup'] else H)[k['zone_src'][2]]), ns=k['zone_src'][3], thr_px=k['zone_src'][4], thr_kind=k['zone_src'][5], plist=[(int(TS[i_]), float((H if k['sup'] else L)[i_])) for i_ in k['zone_src'][6]])), trig=k.get('trig', 'low'), zin_ts=(int(TSm[k['zin']]) if k.get('zin') is not None else None), zone_lo=bias['end'], zone_hi=(k['zone_at'] if 'zone_at' in k else bias.get('cand_zone')), dual=dual, from_live=((cur == live) if dual else True), live_dir=(None if (not dual or live is None) else ('Long' if live else 'Short')), bias_kind=bias['kind'], bias_end=bias['end'], cand_ts=int(TS[k['c0']]), cand_px=k['lvl'], p0_ts=int(TSm[k['p0']]), touch_ts=int(TSm[k['T']]),
                            p_ts=int(TSm[k['p']]), p_px=float((Lm if sup else Hm)[k['p']]), n_newp=k['nP'], sw_ts=int(TSm[swp]), sw_px=float((Hm if sup else Lm)[swp]),
                            sw0_ts=(int(TSm[k['hist'][0][1]]) if k['hist'][0][1] is not None else None), sw0_px=(float((Hm if sup else Lm)[k['hist'][0][1]]) if k['hist'][0][1] is not None else None),
                            mss_ts=int(TSm[m]), fill_ts=int(TSm[m]), try_no=k.get('try_no', 1), **(dict(fvg_edge=k['fvg']['edge'], fvg_far=k['fvg']['far'], fvg_edge0=k['fvg'].get('edge0'), fvg_ts=k['fvg']['ts'], fvg_hit_ts=int(TSm[k['fvg_m']])) if k.get('fvg') is not None else {}), fib_lo=k['fib'][0], fib_hi=k['fib'][1], fib_src_ts=(int(TS[k['fib'][2]]) if k['fib'][2] is not None else None), fib_n=k['fib'][3], fib_depth=k['fib'][4],
                            **(dict(mss1_ts=int(TSm[k['m1']]), sw1_ts=int(TSm[k['sw1']]), sw1_px=float((Hm if sup else Lm)[k['sw1']]), uj_ts=int(TSm[k['uj_i']]), uj_px=k['uj_px'], touch2_ts=int(TSm[k['T2']]), n_hist1=k['n1'],
                                     sw20_ts=(int(TSm[k['sw2_0']]) if k.get('sw2_0') is not None else None), sw20_px=(float((Hm if sup else Lm)[k['sw2_0']]) if k.get('sw2_0') is not None else None)) if k.get('phase') == 2 else {}), sl_basis=sl_basis, sl_ref_px=ref_px, sl_ref_ts=(int(TSm[ref_i]) if ref_i is not None else int(TSm[int(np.argmin(Lm[k['p']:m + 1]) if sup else int(np.argmax(Hm[k['p']:m + 1]))) + k['p']])),
                            hist=[(int(TSm[a_]), float((Lm if sup else Hm)[a_]), (int(TSm[b_]) if b_ is not None else None), (float((Hm if sup else Lm)[b_]) if b_ is not None else None)) for a_, b_ in k['hist']])
                rr_ = abs(tp - ent) / abs(ent - slp)
                if BS_M5_ENTRY == 'market':
                    pos = dict(sup=sup, t=m, m5=True, entry=ent, sl=float(slp), tp=tp, dist=abs(ent - slp), rr=rr_, info=info)
                    st['signal'] += 1; st['bs_fill'] += 1
                else:
                    info['set_ts'] = int(TSm[m])
                    pend = dict(sup=sup, t=m, m5=True, limit=ent, sl=float(slp), tp=tp, rr=rr_, info=info)
                    st['bs_setup'] += 1
            elif not (tp > ent > slp if sup else tp < ent < slp) or pos is not None or pend is not None:
                st['m5_mss_skip'] += 1
            bias['cand'] = None; bias['floor'] = float(k['lvl']); trk = None             # low berikutnya harus LEBIH BAWAH (Short: lebih atas) dari low yang tadi disentuh

    def d_step(t):
        nonlocal trk
        if (H[t] >= bias['ext']) if bias['sup'] else (L[t] <= bias['ext']):     # harga MENYENTUH titik tertinggi (Short: terendah) range -> pencarian low direset, cari low baru sesudah candle ini
            bias['ext'] = float(max(bias['ext'], H[t]) if bias['sup'] else min(bias['ext'], L[t])); bias['ext_idx'] = t; bias['cand'] = None; bias['floor'] = None; bias['touch'] = None; bias['fv'] = None; bias['zin'] = None
            st['bs_top_reset'] += 1
            trk = None
        if fvgz:
            fv_step(t)
        else:
            cand_step(t, True)

    def m5_body(t, m):
        """Semua candle M5 di dalam candle H1 ke-t: kelola posisi (SL dulu baru TP), mulai tracker saat low H1 tersentuh, jalankan MSS. Bias/kandidat yang dipakai = keadaan sampai close candle H1 sebelumnya (tanpa lookahead)."""
        nonlocal pos, trk, pend
        if pos is not None and pos.get('m5') and m > pos['t']:
            sup = pos['sup']
            if (Lm[m] <= pos['sl']) if sup else (Hm[m] >= pos['sl']):
                close_pos(pos, m, pos['sl'], 'SL'); pos = None
            elif (Hm[m] >= pos['tp']) if sup else (Lm[m] <= pos['tp']):
                close_pos(pos, m, pos['tp'], 'TP'); pos = None
        if pend is not None and pend.get('m5') and m > pend['t']:                  # limit: TP tersentuh dulu = batal, limit tersentuh = terisi
            sup = pend['sup']
            if (Hm[m] >= pend['tp']) if sup else (Lm[m] <= pend['tp']):
                pend = None; st['bs_cancel_tp'] += 1; TR('trk', TSm[m], res='limit BATAL: TP tersentuh sebelum limit terisi')
            elif (Lm[m] <= pend['limit']) if sup else (Hm[m] >= pend['limit']):
                info = dict(pend['info']); info['fill_ts'] = int(TSm[m])
                pos = dict(sup=sup, t=m, m5=True, entry=pend['limit'], sl=pend['sl'], tp=pend['tp'], dist=abs(pend['limit'] - pend['sl']), rr=pend['rr'], info=info)
                pend = None; st['bs_fill'] += 1; st['signal'] += 1
                if (Lm[m] <= pos['sl']) if sup else (Hm[m] >= pos['sl']):
                    close_pos(pos, m, pos['sl'], 'SL'); pos = None
        if bias is None:
            return
        if strict and pm is not None and not (dual and (cur != live or BS_DUAL_PM)):                                              # MSS lawan sudah terjadi lebih dulu (menunggu konfirmasi struktur): tidak boleh cari/entry baru; low yang tersentuh terpakai
            if trk is not None:
                trk = None; bias['cand'] = None; bias['floor'] = None; st['m5_cancel_pm'] += 1; TR('trk', TSm[m], res='tracker DIBATALKAN: MSS lawan terjadi lebih dulu')
            elif bias['cand'] is not None and bias['sup'] is not None:
                lv_ = (L if bias['sup'] else H)[bias['cand']]
                if (Lm[m] <= lv_) if bias['sup'] else (Hm[m] >= lv_):
                    bias['floor'] = float(lv_); bias['cand'] = None; st['pm_block'] += 1; TR('touch', TSm[m], lvl=float(lv_), res='dilewati: MSS lawan sudah terjadi (menunggu konfirmasi)')
            return
        if t < BS_WARMUP:                                                          # warm-up: belum boleh ada trade
            if bias['cand'] is not None and bias['sup'] is not None:
                lv_ = (L if bias['sup'] else H)[bias['cand']]
                if (Lm[m] <= lv_) if bias['sup'] else (Hm[m] >= lv_):
                    bias['floor'] = float(lv_); bias['cand'] = None; st['warm_skip'] += 1; TR('touch', TSm[m], lvl=float(lv_), res='dilewati: warm-up')
            return
        if fvgz:
            fvg_trigger(t, m)
        elif trk is None and bias['cand'] is not None and bias['sup'] is not None:
            sup = bias['sup']; c0 = bias['cand']; lvl = (L if sup else H)[c0]
            if (Lm[m] <= lvl) if sup else (Hm[m] >= lvl):
              if not fib_ok(float(lvl)):                                      # range melebar (struktur baru): low ini sudah di atas 50% range -> dilewati
                bias['floor'] = float(lvl); bias['cand'] = None; st['fib_skip_touch'] += 1; TR('touch', TSm[m], lvl=float(lvl), res='dilewati (Fibonacci)')
              elif pos is not None or pend is not None:                      # masih ada posisi/limit: low ini terpakai, cari yang lebih bawah
                bias['floor'] = float(lvl); bias['cand'] = None; st['m5_touch_busy'] += 1; TR('touch', TSm[m], lvl=float(lvl), res='dilewati (posisi/limit masih ada)')
              else:
                TR('touch', TSm[m], lvl=float(lvl), res='TRACKER MULAI', fvg=(None if bias.get('cand_fvg') is None else (bias['cand_fvg']['edge'], bias['cand_fvg']['far'], bias['cand_fvg']['ts'])))
                bias['tries'] = bias.get('tries', 0) + 1
                st['bs_sweep'] += 1; st['m5_touch'] += 1
                trk = m5_start_trk(sup, c0, m); trk['fvg'] = (bias.get('cand_fvg') if BS_FVG else None); trk['fvg_hit'] = False; trk['try_no'] = bias['tries']; trk['fib'] = ((fib_range() + (fib_depth(float(lvl)),)) if fib_range() is not None else (None, None, None, 0, None))
        if trk is not None:
            m5_step(m)

    def m5_loop(t):
        ms = int(np.searchsorted(TSm, TS[t], 'left')); me = int(np.searchsorted(TSm, TS[t] + BS_TF * 60000, 'left'))
        for m in range(ms, me):
            if dual and live is not None:
                for d_ in (live, not live):
                    ctx_load(d_); m5_body(t, m)
                ctx_load(live)
            else:
                m5_body(t, m)

    for t in range(n):
        if m5mode:
            m5_loop(t)
        # (a) posisi terbuka: SL dulu baru TP (konservatif)
        if pos is not None and not pos.get('m5') and t > pos['t']:
            sup = pos['sup']
            if (L[t] <= pos['sl']) if sup else (H[t] >= pos['sl']):
                close_pos(pos, t, pos['sl'], 'SL'); pos = None
            elif (H[t] >= pos['tp']) if sup else (L[t] <= pos['tp']):
                close_pos(pos, t, pos['tp'], 'TP'); pos = None
        # (a2) limit menunggu: TP tersentuh duluan = batal; kalau tidak dan limit tersentuh = terisi
        if pend is not None and not pend.get('m5') and t > pend['t']:
            sup = pend['sup']
            if (H[t] >= pend['tp']) if sup else (L[t] <= pend['tp']):
                pend = None; st['bs_cancel_tp'] += 1
            elif (L[t] <= pend['limit']) if sup else (H[t] >= pend['limit']):
                info = dict(pend['info']); info['fill_ts'] = int(TS[t])
                pos = dict(sup=sup, t=t, entry=pend['limit'], sl=pend['sl'], tp=pend['tp'], dist=abs(pend['limit'] - pend['sl']), rr=pend['rr'], info=info)
                pend = None; st['bs_fill'] += 1; st['signal'] += 1
                if (L[t] <= pos['sl']) if sup else (H[t] >= pos['sl']):           # terisi dan SL di candle yang sama
                    close_pos(pos, t, pos['sl'], 'SL'); pos = None
        # (b) ujung bias ter-break (wick menyentuh)
        if bias is not None and (endbrk or not m5mode) and t > bias['t'] and ((L[t] <= bias['end']) if bias['sup'] else (H[t] >= bias['end'])):
            if bias['kind'] == 'mss' and MF_SL_REV:
                seg = H[bias['p_idx']:t] if bias['sup'] else L[bias['p_idx']:t]
                far = float(seg.max() if bias['sup'] else seg.min())
                nsup = not bias['sup']; st['bs_flipback'] += 1
                set_bias(nsup, 'rev', far, (H[t] if nsup else L[t]), t, bias['p_idx'], t)
            else:
                bias = None; pm = None; st['bs_clear'] += 1
                if trk is not None:
                    trk = None; st['m5_cancel_bias'] += 1
                if pend is not None:
                    pend = None; st['bs_cancel_bias'] += 1
                ch = {True: new_chain(t), False: new_chain(t)}
        # (b2) MSS yang menunggu struktur: ujung MSS ter-break sebelum ada struktur searah -> gagal, bias tidak berubah
        if pm is not None and t > pm['t'] and ((L[t] <= pm['end']) if pm['sup'] else (H[t] >= pm['end'])):
            E(type='pm_fail', sup=pm['sup'], end=pm['end'], t=int(TS[t])); pm_f = pm; pm = None; st['bs_pm_fail'] += 1
            if strict:
                ch = {True: new_chain(t), False: new_chain(t)}
                if BS_PMFAIL_KEEP and pm_f.get('chain') is not None:             # rantai bias (yang menghasilkan MSS tadi) dipulihkan: P terakhir tetap; swing lama dikosongkan agar MSS butuh struktur baru (low/high baru melewati P)
                    rc_ = dict(pm_f['chain']); rc_['sw'] = None; rc_['sw_px'] = None
                    ch[pm_f['sup']] = rc_
                    st['pmfail_keep'] += 1
        # (c) rantai P / MSS -> bias
        sigs = []
        # strict: rantai yang jalan = bias Long -> rantai HIGH (sup=False) saja; bias Short -> rantai LOW saja; ada MSS menunggu konfirmasi -> hanya rantai searah MSS itu (hitung struktur, tanpa deteksi MSS); belum ada bias -> dua-duanya
        act_ch = ({not pm['sup']} if pm is not None else ({not bias['sup']} if bias is not None else {True, False})) if strict else {True, False}
        for sup in (True, False):
            if sup not in act_ch:
                continue
            c = ch[sup]; arr = L if sup else H; j = t - N
            if j >= 0 and _mf_swing_at(arr, j, N, sup, c['reset']):
                st['bs_p'] += 1
                if c['p'] is None:
                    c['p'] = j; c['first'] = j; c['hist'].append(int(j))
                else:
                    a_ = c['p']; body_ = MF_BODY and a_ != c['first'] and not BS_STRUCT_HIGHER
                    thr = (min(O[a_], C[a_]) if sup else max(O[a_], C[a_])) if body_ else arr[a_]
                    if ((arr[j] < thr) if BS_STRUCT_HIGHER else (arr[j] <= thr)) if sup else ((arr[j] > thr) if BS_STRUCT_HIGHER else (arr[j] >= thr)):
                        sa = H if sup else L
                        lo_, hi_ = (a_ + 1, j) if j - a_ > 1 else (a_, j + 1)
                        seg = sa[lo_:hi_]; k_ = int(np.argmax(seg) if sup else np.argmin(seg))
                        c['sw'] = lo_ + k_; c['sw_px'] = float(seg[k_]); c['prev'] = a_; c['p'] = j; c['ns'] += 1; c['hist'].append(int(j)); st['bs_struct'] += 1; c['touch_px'] = float(thr); c['touch_kind'] = 'body' if body_ else 'wick'
                        E(type='struktur', sup=sup, n=c['ns'], t=int(TS[t]), p_old=(int(TS[a_]), float(arr[a_])), p_new=(int(TS[j]), float(arr[j])), thr=float(thr), basis=('body' if body_ else 'wick'),
                          sw=(int(TS[c['sw']]), c['sw_px']), pm=(None if pm is None else pm['sup']), bias=(None if bias is None else bias['sup']))
            if c['sw'] is not None and c['ns'] >= MF_MIN_STRUCT and not (strict and pm is not None) and ((C[t] > c['sw_px']) if sup else (C[t] < c['sw_px'])):
                sigs.append(sup)
        if bias is not None:
            fib_update()
            if BS_ZONE and pm is None:                             # zona = swing struktur TERBARU dari rantai searah bias (saat MSS lawan menunggu, rantai itu sudah dipakai konfirmasi lawan: zona dibekukan)
                cc_ = ch[not bias['sup']]
                if cc_['sw'] is not None and cc_['ns'] >= 1 and bias.get('zone') != float(cc_['sw_px']):
                    zone_set(cc_['sw_px'], (int(cc_['prev']), int(cc_['p']), int(cc_['sw']), int(cc_['ns']), cc_.get('touch_px'), cc_.get('touch_kind'), tuple(cc_['hist'][-8:])))
        for sup in sigs:
            c = ch[sup]
            end = float(L[c['p']:t + 1].min()) if sup else float(H[c['p']:t + 1].max())
            seg = H[c['p']:t + 1] if sup else L[c['p']:t + 1]
            k_ = int(np.argmax(seg) if sup else np.argmin(seg))
            st['bs_mss'] += 1
            _act = ('searah' if (bias is not None and bias['sup'] == sup) else (('pm_diabaikan' if (pm is not None and pm['sup'] == sup) else ('pm_tunggu_ganti' if pm is not None else 'pm_tunggu')) if BS_CONFIRM > 0 else 'bias_langsung'))
            E(type='mss', sup=sup, t=int(TS[t]), close=float(C[t]), sw=(int(TS[c['sw']]), c['sw_px']), n=c['ns'], p_last=(int(TS[c['p']]), float((L if sup else H)[c['p']])), end=end,
              top=(int(TS[c['p'] + k_]), float(seg[k_])), action=_act, bias=(None if bias is None else bias['sup']), need=max(BS_CONFIRM, 1))
            if bias is not None and bias['sup'] == sup:
                # MSS searah dengan bias yang sudah ada: bias tetap, pencarian low/high, range dan limit TIDAK direset. Hanya ujung bias dipindah ke ujung MSS terbaru.
                bias['end'] = end; bias['kind'] = 'mss'; bias['p_idx'] = int(c['p']); bias['fv'] = None
                if (end < bias['fib100']) if sup else (end > bias['fib100']):
                    bias['fib100'] = end; bias['fib_src'] = None
                ch = {True: new_chain(t), False: new_chain(t)}
                st['bs_refresh'] += 1
                if pm is not None:                                             # MSS lawan yang menunggu struktur dibatalkan: bias masih sama
                    E(type='pm_cancel', sup=pm['sup'], t=int(TS[t])); pm = None; st['bs_pm_cancel'] += 1
            elif BS_CONFIRM > 0:
                if pm is not None and pm['sup'] == sup:                         # MSS searah dengan MSS yang sedang menunggu: diabaikan
                    ch[sup] = new_chain(t)
                else:                                                          # MSS lawan bias: bias BELUM berubah, tunggu struktur searah MSS
                    pm = dict(sup=sup, end=end, p_idx=int(c['p']), t=t, chain=c)
                    ch = {True: new_chain(t), False: new_chain(t)}
                    st['bs_pm'] += 1
            else:
                set_bias(sup, 'mss', end, float(seg[k_]), c['p'] + k_, c['p'], t)
            break
        # (c2) struktur searah MSS terbentuk (P2 menembus P awal sesudah MSS) -> bias berubah
        if pm is not None and ch[not pm['sup']]['ns'] >= max(BS_CONFIRM, 1):
            pseg = H[pm['p_idx']:t + 1] if pm['sup'] else L[pm['p_idx']:t + 1]
            pk = int(np.argmax(pseg) if pm['sup'] else np.argmin(pseg))
            st['bs_pm_ok'] += 1
            E(type='pm_ok', sup=pm['sup'], t=int(TS[t]), n=ch[not pm['sup']]['ns'])
            set_bias(pm['sup'], 'mss', pm['end'], float(pseg[pk]), pm['p_idx'] + pk, pm['p_idx'], t, keep=(ch[not pm['sup']] if strict else None))
        # (d) cari entry di dalam range bias (low terus dicari; low yang ter-break body gagal -> cari yang lebih bawah). Dual: dijalankan untuk bias live DAN bias lama.
        if dual and live is not None:
            for d_ in (live, not live):
                ctx_load(d_)
                if bias is not None:
                    if BS_ZONE and d_ != live and bias.get('oc') is not None:
                        old_chain_step(t)
                    d_step(t)
            ctx_load(live)
        elif bias is not None:
            d_step(t)
        if _BS_TRACE is not None and _BS_TRACE[0] <= TS[t] <= _BS_TRACE[1]:                    # debug: BS_TRACE=awal,akhir (ms epoch UTC)
            _BS_LOG.append(dict(t=int(TS[t]), o=float(O[t]), h=float(H[t]), l=float(L[t]), c=float(C[t]),
                                kind='h1', pm=(None if pm is None else ('L' if pm['sup'] else 'S')), trk=(None if trk is None else dict(lvl=trk['lvl'], T=int(TSm[trk['T']]), fvg_hit=trk.get('fvg_hit'))),
                                bias=(None if bias is None else (('L' if bias['sup'] else 'S') + ':' + bias['kind'])), end=(None if bias is None else bias['end']),
                                ext=(None if bias is None else bias['ext']), ext_ts=(None if bias is None else int(TS[bias['ext_idx']])),
                                cand=(None if bias is None or bias['cand'] is None else (int(TS[bias['cand']]), float((L if bias['sup'] else H)[bias['cand']]))),
                                floor=(None if bias is None else bias['floor']), pend=(None if pend is None else (pend['limit'], pend['sl'], pend['tp'])), pos=(pos is not None)))
    if dual:
        ctx_save()
        for d_ in (True, False):
            if S[d_]['pend'] is not None:
                st['bs_pend_end'] += 1
            if S[d_]['pos'] is not None:
                close_pos(S[d_]['pos'], len(Cm) - 1, float(Cm[-1]), None)
    else:
      if pend is not None:
        st['bs_pend_end'] += 1
      if pos is not None:
        if pos.get('m5'):
            close_pos(pos, len(Cm) - 1, float(Cm[-1]), None)
        else:
            px = float(C[n - 1]); close_pos(pos, n - 1, px, None)
    return out


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
    st = dict(fb_wickonly=0, fb_pair=0, fb_pair_noL=0, fb_sweep=0, fb_closebreak=0, fb_nosweep=0, fb_bos=0, fb_invalid=0, fb_trigger=0, fb_cancel=0, fb_nofill=0, no_bos=0, bos_gagal=0, tp_invalid=0, no_bo=0, expired=0, level=0, level_valid=0, breakout=0, no_mss1=0, mss1=0, no_touch=0, touch=0, no_mss2=0, signal=0, dup=0)
    cands = []
    r1_cache = {}; r2_cache = {}
    if NS_MODE == 'bias_sweep':
        ts_, o_, h_, l_, c_ = _tf_arrays(m5df, BS_TF)
        _ev = []
        _res = biassweep_signals(symbol, ts_, o_, h_, l_, c_, st, (TS5, m5df['open'].values.astype(float), H5, L5, C5), _ev)
        _STRUCT_EV[symbol] = dict(ev=_ev, first=int(ts_[0]), last=int(ts_[-1]) + BS_TF * 60000, n=len(ts_))
        return _res, st
    if NS_MODE == 'mss_flip':
        if MF_TF == 5:
            return mssflip_signals(symbol, TS5, H5, L5, C5, st, m5df['open'].values.astype(float)), st
        step = MF_TF * 60000; g = (TS5 // step)
        tf = m5df.assign(_g=g).groupby('_g').agg(ts=('ts', 'first'), open=('open', 'first'), high=('high', 'max'), low=('low', 'min'), close=('close', 'last'), n=('ts', 'count'))
        tf = tf[tf['n'] == MF_TF // 5].reset_index(drop=True)          # hanya candle TF yang lengkap
        tf['ts'] = (tf['ts'] // step) * step
        return mssflip_signals(symbol, tf['ts'].values.astype(np.int64), tf['high'].values.astype(float), tf['low'].values.astype(float),
                               tf['close'].values.astype(float), st, tf['open'].values.astype(float)), st
    if NS_MODE == 'fibo_bos':
        cands.extend(fibo_signals(symbol, TS5, H5, L5, C5, st, m5df['open'].values.astype(float)))
    if NS_MODE == 'mss_only':
        # M5 saja: cari MSS berurutan per arah; setelah MSS di candle t, pencarian MSS berikutnya (arah sama) mulai dari t
        for sup in (True, False):
            s = 0
            while s + 2 < n5:
                stop = min(n5, s + MSS_WINDOW)
                r = _ns_find_mss(sup, s, stop, H5, L5, C5)
                if r is None:
                    if stop >= n5:
                        break
                    s += max(1, MSS_WINDOW // 3); continue
                t, P = r[0], r[1]
                t_ent = t; bos_info = None
                if NS_BOS:
                    # jangan langsung entry: tunggu BOS. SH1 (swing ref MSS) tertembus SH2, SH2 tertembus SH3 = BOS. SL = swing low (Short: swing high) BOS
                    rb = _ns_find_bos(sup, s, t, P, r[2], None, min(n5, t + MSS_WINDOW), H5, L5)
                    if rb is None:
                        st['no_bos'] += 1; s = t; continue
                    if rb[0] == 'gagal':
                        st['bos_gagal'] += 1; s = max(rb[1], t + 1); continue
                    bos_info = rb[1]; t_ent = bos_info['conf']
                    if t_ent >= n5:
                        s = t; continue
                    entry = float(C5[t_ent]); sl = float(L5[bos_info['sl']] if sup else H5[bos_info['sl']])
                else:
                    entry = float(C5[t]); sl = float(L5[P] if sup else H5[P])
                dist = (entry - sl) if sup else (sl - entry)
                s = t
                if dist <= 0:
                    continue
                p_start = None
                if NS_TP == 'struct1':
                    tpv, p_start = tp_first_structure(sup, r[4], P, H5, L5)
                    if tpv is None or ((tpv <= entry) if sup else (tpv >= entry)):
                        st['tp_invalid'] += 1; continue
                    tp = tpv; rr_ = abs(tp - entry) / dist
                else:
                    tp = entry + RR * dist if sup else entry - RR * dist; rr_ = RR
                st['signal'] += 1
                cands.append(dict(symbol=symbol, sup=sup, d='Long' if sup else 'Short', mode='mss_only', p1=int(TS5[r[4]]), pstart=(int(TS5[p_start]) if p_start is not None else None), lvl=0.0, formed=None, bo=None, mss1=None,
                                  acuan=None, touch=None, mss=int(TS5[t]), bo_m5=None, bi_m5=None, ptime=int(TS5[P]), entry=entry, sl=sl, tp=tp,
                                  rr=rr_, dist=dist, t=t_ent, entry_ts=int(TS5[t_ent]),
                                  sh2=(int(TS5[bos_info['sh2']]) if bos_info else None), sh3=(int(TS5[bos_info['sh3']]) if bos_info else None),
                                  bos_conf=(int(TS5[bos_info['conf']]) if bos_info else None), sl_swing=(int(TS5[bos_info['sl']]) if bos_info else None)))
    for i in range(0, (n - 2) if NS_MODE not in ('mss_only', 'fibo_bos') else 0):
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
            k = None; t1 = None; acuan = float(lvl)
            if NS_MODE == 'touch':
                # level langsung jadi acuan: tersentuh di M5 -> langsung cari MSS -> entry
                if start >= n:
                    continue
                js = int(np.searchsorted(TS5, ts[start]))             # M5 pertama setelah level terkonfirmasi
                rest = (L5[js:] <= lvl) if sup else (H5[js:] >= lvl)
                tt = np.flatnonzero(rest)
                if len(tt) == 0:
                    st['no_touch'] += 1; continue
                jt = js + int(tt[0]); st['touch'] += 1
                if jt + 2 >= n5:
                    continue
                keyt = ('t', sup, jt)
                if keyt not in r2_cache:
                    r2_cache[keyt] = _ns_find_mss(sup, jt, n5, H5, L5, C5)
                r2 = r2_cache[keyt]
            else:
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
            mss_t = t; bo_i = None; bi_i = None; tp_far = None
            if NS_ENTRY == 'bo_bi':
                # tunggu ujung MSS (P) break-out (body M5 close menembus keluar), lalu break-in (close kembali ke dalam) maks NS_EXPIRE_MIN menit
                tip = float(L5[P] if sup else H5[P])
                kb = ('bb', sup, mss_t, P)
                if kb not in r2_cache:
                    bo_i = _first_close(sup, C5, mss_t + 1, tip, outside=True)
                    bi_i = None
                    if bo_i is not None:
                        lim = min(n5, bo_i + 1 + max(1, int(np.ceil(NS_EXPIRE_MIN / 5.0))))
                        seg = C5[bo_i + 1:lim]
                        w = np.flatnonzero(seg > tip) if sup else np.flatnonzero(seg < tip)
                        bi_i = (bo_i + 1 + int(w[0])) if len(w) else None
                    r2_cache[kb] = (bo_i, bi_i)
                bo_i, bi_i = r2_cache[kb]
                if bo_i is None:
                    st['no_bo'] += 1; continue
                if bi_i is None:
                    st['expired'] += 1; continue
                t = bi_i
                sl = float(L5[bo_i:bi_i + 1].min() if sup else H5[bo_i:bi_i + 1].max())   # pergerakan terjauh di luar MSS (break-out s/d break-in)
                tp_far = float(H5[mss_t:bo_i + 1].max() if sup else L5[mss_t:bo_i + 1].min())   # pergerakan terjauh dari MSS sebelum ujung MSS break-out
            else:
                sl = float(L5[P] if sup else H5[P])
            entry = float(C5[t])
            dist = (entry - sl) if sup else (sl - entry)
            if dist <= 0:
                continue
            p_start = None
            if NS_TP == 'struct1':
                tpv, p_start = tp_first_structure(sup, r2[4], P, H5, L5)
                if tpv is None or ((tpv <= entry) if sup else (tpv >= entry)):
                    st['tp_invalid'] += 1; continue
                tp = tpv; rr = abs(tp - entry) / dist
            elif NS_ENTRY == 'bo_bi' and NS_TP == 'far':
                tp = tp_far
                if (tp <= entry) if sup else (tp >= entry):
                    st['tp_invalid'] += 1; continue          # entry sudah di luar/di atas titik terjauh -> tidak ada ruang TP
                rr = abs(tp - entry) / dist
            else:
                tp = entry + RR * dist if sup else entry - RR * dist
                rr = RR
            st['signal'] += 1
            cands.append(dict(symbol=symbol, sup=sup, d='Long' if sup else 'Short', lvl=float(lvl), formed=int(ts[i + 1]),
                              bo=(int(ts[k]) if k is not None else None), mss1=(int(TS5[t1]) if t1 is not None else None), acuan=acuan, touch=int(TS5[jt]), mss=int(TS5[mss_t]),
                              bo_m5=(int(TS5[bo_i]) if bo_i is not None else None), bi_m5=(int(TS5[bi_i]) if bi_i is not None else None),
                              ptime=int(TS5[P]), entry=entry, sl=sl, tp=tp, rr=rr, dist=dist, t=t, entry_ts=int(TS5[t]), p1=int(TS5[r2[4]]), pstart=(int(TS5[p_start]) if p_start is not None else None)))
    cands.sort(key=lambda x: (x['t'], x['lvl'] or 0.0))
    seen = set(); uniq = []
    for cd in cands:
        key = (cd['d'], cd['t'])
        if key in seen:
            st['dup'] += 1; continue
        seen.add(key); uniq.append(cd)
    for cd in uniq:
        ex = cd.get('ex_override') or find_exit(cd['sup'], cd['t'], cd['sl'], cd['tp'], H5, L5)
        if ex is None:
            cd['exit_ts'] = None; cd['why'] = None; cd['exit_px'] = None
        else:
            cd['exit_ts'] = int(TS5[ex[0]]); cd['exit_px'] = ex[1]; cd['why'] = ex[2]
    return uniq, st

# ============================================================
# SIMULASI GABUNGAN (1 balance, semua koin)
# ============================================================
def _is_win(x):
    return (x['r'] > 0) if x.get('mode') in ('mss_flip', 'bias_sweep') else x['why'] == 'TP'


def simulate(cands):
    cands = sorted(cands, key=lambda x: (x['entry_ts'], x['symbol']))
    fee = FEE_ENTRY_PCT + FEE_EXIT_PCT
    heap = []; closed_pnl = 0.0; used = 0.0; n_open = 0; open_sd = {}
    trades = []; bl = dict(open_same=0, slot=0, margin=0, terbuka=0)
    for idx, cd in enumerate(cands):
        t0 = cd['entry_ts']
        while heap and heap[0][0] <= t0:
            _, _, pnl, margin, sd = heapq.heappop(heap)
            closed_pnl += pnl; used -= margin; n_open -= 1; open_sd[sd] = open_sd.get(sd, 1) - 1
        sd = (cd['symbol'], cd['d'])
        if ONE_POS_PER_DIR and open_sd.get(sd, 0) > 0:
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
            heapq.heappush(heap, (float('inf'), idx, 0.0, margin, sd)); used += margin; n_open += 1; open_sd[sd] = open_sd.get(sd, 0) + 1
            continue
        feeR = fee * cd['entry'] / cd['dist']
        gr = cd.get('gross_r')
        r = ((cd['rr'] if cd['why'] == 'TP' else -1.0) if gr is None else gr) - feeR
        pnl = r * risk
        tr = dict(cd); tr['r'] = r; tr['pnl'] = pnl; tr['bal_before'] = bal; tr['fee_r'] = feeR
        trades.append(tr)
        heapq.heappush(heap, (cd['exit_ts'], idx, pnl, margin, sd)); used += margin; n_open += 1; open_sd[sd] = open_sd.get(sd, 0) + 1
    run = INITIAL_BALANCE; pk = INITIAL_BALANCE; mdd = 0.0
    for tr in sorted(trades, key=lambda x: x['exit_ts']):
        run += tr['pnl']; tr['bal_after'] = run
        pk = max(pk, run); mdd = max(mdd, (pk - run) / pk * 100)
    trades.sort(key=lambda x: x['entry_ts'])
    nt = len(trades); nw = sum(1 for x in trades if _is_win(x)); tot_r = sum(x['r'] for x in trades)
    summ = dict(n_trades=nt, n_win=nw, n_loss=nt - nw, wr=(nw / nt * 100 if nt else 0.0), total_r=tot_r,
                avg_r=(tot_r / nt if nt else 0.0), avg_rr=(sum(x['rr'] for x in trades) / nt if nt else 0.0), fee_r=sum(x['fee_r'] for x in trades), gross_r=sum(x['r'] + x['fee_r'] for x in trades),
                avg_dist_pct=(sum(x['dist'] / x['entry'] for x in trades) / nt * 100 if nt else 0.0), final_balance=run, roi=(run / INITIAL_BALANCE - 1) * 100, mdd=mdd)
    return trades, summ, bl


def monthly_breakdown(trades, start=None):
    by = {}
    for tr in sorted(trades, key=lambda x: x['exit_ts']):
        by.setdefault(_wib(tr['exit_ts'])[:7], []).append(tr)
    rows = []; bal = INITIAL_BALANCE if start is None else start
    for mth, L in by.items():
        pr = sum(x['pnl'] for x in L); nw = sum(1 for x in L if _is_win(x))
        rows.append(dict(month=mth, start=bal, end=bal + pr, profit=pr, growth=(pr / bal * 100 if bal else 0.0),
                         n=len(L), wr=nw / len(L) * 100, total_r=sum(x['r'] for x in L)))
        bal += pr
    avg = sum(r['growth'] for r in rows) / len(rows) if rows else 0.0
    return rows, avg


def simulate_separate(cands, symbols=None):
    """Backtest TERPISAH per koin: tiap koin punya akun sendiri (modal INITIAL_BALANCE, risk 1% dari saldo koin itu, margin/slot/posisi searah dihitung per koin). Hasil gabungan = penjumlahan akun-akun terpisah itu."""
    by = {}
    for cd in cands:
        by.setdefault(cd['symbol'], []).append(cd)
    syms = list(symbols) if symbols else []
    for sy in by:
        if sy not in syms:
            syms.append(sy)
    trades = []; bl = dict(open_same=0, slot=0, margin=0, terbuka=0); res = []
    for sy in syms:
        t, sm, b = simulate(by.get(sy, []))
        mo, av = monthly_breakdown(t)
        res.append(dict(symbol=sy, summ=sm, monthly=mo, avg=av, bl=b)); trades.extend(t)
        for k_ in bl:
            bl[k_] += b[k_]
    trades.sort(key=lambda x: (x['entry_ts'], x['symbol']))
    nt = len(trades); nw = sum(1 for x in trades if _is_win(x)); tot_r = sum(x['r'] for x in trades); nc = max(len(syms), 1)
    fin = sum(r_['summ']['final_balance'] for r_ in res); modal = INITIAL_BALANCE * nc
    summ = dict(n_trades=nt, n_win=nw, n_loss=nt - nw, wr=(nw / nt * 100 if nt else 0.0), total_r=tot_r, avg_r=(tot_r / nt if nt else 0.0),
                avg_rr=(sum(x['rr'] for x in trades) / nt if nt else 0.0), fee_r=sum(x['fee_r'] for x in trades), gross_r=sum(x['r'] + x['fee_r'] for x in trades),
                avg_dist_pct=(sum(x['dist'] / x['entry'] for x in trades) / nt * 100 if nt else 0.0), final_balance=fin, roi=(fin / modal - 1) * 100,
                mdd=max([r_['summ']['mdd'] for r_ in res] + [0.0]), modal_total=modal, n_coins=nc)
    return trades, summ, bl, res


def per_symbol_breakdown(trades, coin_res=None):
    if coin_res is not None:
        rows = []
        for r_ in coin_res:
            sm = r_['summ']
            rows.append(dict(symbol=r_['symbol'], n=sm['n_trades'], tp=sm['n_win'], sl=sm['n_loss'], wr=sm['wr'], total_r=sm['total_r'], profit=sm['final_balance'] - INITIAL_BALANCE,
                             roi=sm['roi'], mdd=sm['mdd'], final=sm['final_balance'], fee_r=sm['fee_r'], gross_r=sm['gross_r'], avg_rr=sm['avg_rr']))
        rows.sort(key=lambda r: -r['total_r'])
        return rows
    by = {}
    for tr in trades:
        by.setdefault(tr['symbol'], []).append(tr)
    rows = []
    for sym, L in by.items():
        nw = sum(1 for x in L if _is_win(x))
        rows.append(dict(symbol=sym, n=len(L), tp=nw, sl=len(L) - nw, wr=nw / len(L) * 100,
                         total_r=sum(x['r'] for x in L), profit=sum(x['pnl'] for x in L)))
    rows.sort(key=lambda r: -r['total_r'])
    return rows

# ============================================================
# RUN
# ============================================================
def _run():
    global _phase, _trades, _summary, _funnel, _monthly, _avg_monthly_growth, _per_symbol, _coin_res
    try:
        _log_msg(f"🚀 Backtest {NS_MODE} — {len(SYMBOLS)} koin, {BACKTEST_START_DATE} s/d {BACKTEST_END_DATE}")
        alur = ((f"TF {BS_TF}m: struktur P -> MSS = bias -> low tersentuh -> MSS di M5" if BS_ENTRY == 'mss_m5' else f"TF {BS_TF}m: struktur P -> MSS = bias -> sweep + engulfing di range") if NS_MODE == 'bias_sweep' else "M5 saja: struktur P -> swing di-break (MSS) -> flip saat MSS lawan" if NS_MODE == 'mss_flip' else "M5 saja: BOS besar (P ditembus P baru, swing low di-sweep wick, P baru di-break) -> rantai P dari ujung bawah -> swing low P tersentuh" if NS_MODE == 'fibo_bos' else "M5 saja, tanpa level -> cari MSS" if NS_MODE == 'mss_only' else "level = acuan -> tersentuh M5 -> MSS" if NS_MODE == 'touch' else
                "break-out body -> MSS pertama (acuan) -> acuan tersentuh -> MSS kedua")
        _log_msg(f"   Mode {NS_MODE}: {'' if NS_MODE in ('mss_only', 'fibo_bos', 'mss_flip', 'bias_sweep') else f'level awal H1 (tanpa FVG, filter ujung wick {NS_LV_N} kiri-kanan) -> '}{alur} -> {_entry_desc()}. "
                 f"Risk {RISK_PCT*100:.1f}%/trade, leverage {LEVERAGE:g}x, slot {'tanpa batas' if MAX_CONCURRENT == float('inf') else int(MAX_CONCURRENT)}.")
        all_c = []; tot = {}; done_syms = []
        for symbol in SYMBOLS:
            _log_msg(f"📊 {symbol}: fetch M5...")
            df = fetch_bybit_m5(symbol)
            if df is None or df.empty:
                _log_msg(f"   ⚠ {symbol}: data kosong, skip."); continue
            cands, st = process_coin(symbol, df)
            all_c.extend(cands); done_syms.append(symbol)
            for k, v in st.items():
                tot[k] = tot.get(k, 0) + v
            if NS_MODE == 'bias_sweep' and BS_ENTRY == 'mss_m5':
                _log_msg(f"   ✅ {symbol}: {len(df):,} candle M5, bias {st['bs_bias']} (balik {st['bs_flipback']}, kosong {st['bs_clear']}), low/high tersentuh {st['m5_touch']}, P baru M5 {st['m5_newp']}, MSS M5 {st['m5_mss']} (batal: top {st['m5_cancel_top']}, ujung bias {st['m5_cancel_end']}, bias berubah {st['m5_cancel_bias']}) -> {len(cands)} trade.")
            elif NS_MODE == 'bias_sweep':
                _log_msg(f"   ✅ {symbol}: {len(df):,} candle M5, bias {st['bs_bias']} (balik {st['bs_flipback']}, kosong {st['bs_clear']}), sweep {st['bs_sweep']}, engulfing {st['bs_engulf']}, limit {st['bs_setup']} (batal TP {st['bs_cancel_tp']}, batal bias {st['bs_cancel_bias']}, terisi {st['bs_fill']}) -> {len(cands)} trade.")
            elif NS_MODE == 'mss_flip':
                _log_msg(f"   ✅ {symbol}: {len(df):,} candle M5, P valid {st['mf_p']}, struktur {st['mf_struct']}, MSS {st['mf_mss']} (flip {st['mf_flip']}, kena SL {st['mf_sl']}, entry balik setelah SL {st['mf_rev']}, searah diabaikan {st['mf_same']}) -> {len(cands)} entry.")
            else:
              _log_msg(f"   ✅ {symbol}: {len(df):,} candle M5, {st['level']} level ({st['level_valid']} lolos filter), break-out {st['breakout']}, MSS1 {st['mss1']}, "
                       f"tersentuh {st['touch']}, sinyal {st['signal']} (kembar {st['dup']}) -> {len(cands)} kandidat entry.")
        if SEPARATE_COINS:
            _log_msg(f"🧮 Simulasi TERPISAH per koin ({len(all_c)} kandidat, modal ${INITIAL_BALANCE:g} per koin)...")
            trades, summ, bl, coin_res = simulate_separate(all_c, done_syms)
            monthly, avg = monthly_breakdown(trades, start=summ['modal_total'])
            per_sym = per_symbol_breakdown(trades, coin_res)
        else:
            _log_msg(f"🧮 Simulasi gabungan ({len(all_c)} kandidat)...")
            trades, summ, bl = simulate(all_c); coin_res = []
            monthly, avg = monthly_breakdown(trades)
            per_sym = per_symbol_breakdown(trades)
        funnel = dict(tot); funnel.update(bl)
        with _lock:
            _trades[:] = trades; _summary.clear(); _summary.update(summ); _funnel.clear(); _funnel.update(funnel)
            _monthly[:] = monthly; _avg_monthly_growth = avg; _per_symbol[:] = per_sym; _coin_res = coin_res
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
def _wibs(ts_ms):
    if ts_ms is None:
        return '-'
    dt = datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc) + timedelta(hours=7)
    return dt.strftime('%d %b %H:%M')


def _bsm_block(k, tr):
    g = lambda v: f"{v:.8g}"
    long_ = tr['d'] == 'Long'
    held = (tr['exit_idx'] - tr['t']) * 5
    why = {'SL': 'SL kena', 'TP': 'TP kena'}.get(tr['why'], tr['why'])
    lo_hi = ('low', 'high') if long_ else ('high', 'low')
    kind = ('MSS + struktur searah' if BS_CONFIRM > 0 else 'MSS') if tr['bias_kind'] == 'mss' else 'balik setelah ujung MSS ter-break'
    o = [f"Trade : {k}", f"Coin : {tr['symbol']}", f"Dir : {tr['d']}", f"Hasil bersih : {tr['r']:+.2f}R", f"Hasil kotor : {tr['gross_r']:+.2f}R", f"Fee : -{tr['fee_r']:.2f}R",
         f"Exit oleh : {why}", f"Bias H1 : {tr['d']} ({kind})", *(([f"Ujung struktur terakhir : {g(tr['zone_src']['sw_px'])}, {_wib(tr['zone_src']['sw_ts'])[5:]} (swing {'low' if tr['d'] == 'Long' else 'high'} struktur ke-{tr['zone_src']['ns']} = batas {'atas' if tr['d'] == 'Long' else 'bawah'} zona)"]
          + [f"P{tr['zone_src']['ns'] + 1 - (len(tr['zone_src']['plist']) - 1 - q_)} : {g(px_)}, {_wib(ts_)[5:]}" for q_, (ts_, px_) in enumerate(tr['zone_src']['plist'][-BS_TXT_NP:], start=len(tr['zone_src']['plist']) - len(tr['zone_src']['plist'][-BS_TXT_NP:]))]
          + ([f"Syarat struktur ke-{tr['zone_src']['ns']} : P{tr['zone_src']['ns'] + 1} {'harus melewati wick' if tr['zone_src']['thr_kind'] != 'body' else 'menyentuh ujung body'} P{tr['zone_src']['ns']} = {g(tr['zone_src']['thr_px'])}"] if tr['zone_src'].get('thr_px') is not None else []))
         if (BS_ZONE and tr.get('zone_src')) else []), *([f"Zona low (ujung bawah swing struktur terbaru s/d ujung MSS) : {tr['zone_lo']:.8g} - {tr['zone_hi']:.8g}" if tr['d'] == 'Long' else f"Zona high (ujung atas swing struktur terbaru s/d ujung MSS) : {tr['zone_hi']:.8g} - {tr['zone_lo']:.8g}"] if (BS_ZONE and tr.get('zone_hi') is not None) else []), *([f"Bias live saat MSS M5 : {tr['live_dir']} ({'trade dari bias LIVE' if tr.get('from_live') else 'trade dari bias LAMA ' + tr['d'] + ', bias live sudah ' + str(tr['live_dir'])})"] if tr.get('dual') and tr.get('live_dir') else []), (f"Ujung bias (acuan, tidak mengakhiri bias) : {g(tr['bias_end'])}" if not BS_M5_ENDBREAK else f"Ujung bias (invalidasi) : {g(tr['bias_end'])}"), f"Percobaan ke- (dalam bias yang sama) : {tr.get('try_no', 1)}",
         *([f"Fibonacci H1 : 100% = {g(tr['fib_lo'])} ({'ujung swing struktur' + str(tr.get('fib_n', 0)) + ', ' + _wib(tr['fib_src_ts']) if tr.get('fib_src_ts') else 'ujung bias'}) | 0% = {g(tr['fib_hi'])} (titik {'tertinggi' if long_ else 'terendah'}) | {BS_FIB_DEPTH * 100:g}% = {g(tr['fib_hi'] + BS_FIB_DEPTH * (tr['fib_lo'] - tr['fib_hi']))}", f"Kedalaman low yang disentuh : {tr['fib_depth'] * 100:.0f}% range"] if tr.get('fib_lo') is not None and tr.get('fib_depth') is not None else []),
         *([f"1. Masuk zona (candle M5 pertama) : {_wib(tr['zin_ts'])}" if tr.get('zin_ts') else "1. Zona : tanpa batas (BS_ZONE=0 atau belum ada struktur)",
            f"2. Ujung {'bawah' if long_ else 'atas'} M5 awal (P, {lo_hi[0]} terdalam sejak masuk zona) : {_wib(tr['p0_ts'])} @ {g(tr['cand_px'])}",
            f"3. FVG H1 tersentuh (M5) : {_wib(tr.get('fvg_hit_ts') or tr['touch_ts'])}", f"   MSS dicari sejak : {_wib(tr['touch_ts'])} ({'pertama kali masuk zona' if tr.get('start') == 'zona' else 'FVG tersentuh'})"] if tr.get('trig') == 'fvg' else
           [f"1. {lo_hi[0].capitalize()} H1 (candle) : {_wib(tr['cand_ts'])} @ {g(tr['cand_px'])}",
            f"2. Ujung {'bawah' if long_ else 'atas'} M5 awal (P) : {_wib(tr['p0_ts'])}",
            f"3. {lo_hi[0].capitalize()} H1 tersentuh (M5) : {_wib(tr['touch_ts'])}"]),
         *([f"   FVG H1{'' if tr.get('trig') == 'fvg' else ' (' + ('di bawah' if long_ else 'di atas') + ' ' + lo_hi[0] + ')'} : {('sisa gap' if (BS_FVG_GAP and tr.get('fvg_edge0') is not None) else ('zona fresh' if not BS_FVG_GAP else 'zona'))} {g(min(tr['fvg_edge'], tr['fvg_far']))} - {g(max(tr['fvg_edge'], tr['fvg_far']))}" + (f" (gap asli {g(min(tr['fvg_edge0'], tr['fvg_far']))} - {g(max(tr['fvg_edge0'], tr['fvg_far']))}, {'sudah terisi sebagian' if abs(tr['fvg_edge0'] - tr['fvg_edge']) > 1e-12 else 'belum terisi'})" if (BS_FVG_GAP and tr.get('fvg_edge0') is not None) else "") + f" (candle tengah FVG {_wib(tr['fvg_ts'])})", f"   FVG tersentuh (M5), sebelum MSS : {_wib(tr['fvg_hit_ts'])}"] if tr.get('fvg_edge') is not None else []),
         f"4. Swing {lo_hi[1]} awal (P awal s/d sentuh){' - tidak dipakai untuk MSS' if tr.get('strict_sw') else ''} : " + (f"{_wib(tr['sw0_ts'])} @ {g(tr['sw0_px'])}" if tr.get('sw0_ts') else 'belum ada')]
    _n1 = tr.get('n_hist1'); _m = 'MSS-2' if _n1 is not None else 'MSS'
    def _m1_lines():
        return [f"   MSS-1 (close M5 menembus swing {g(tr['sw1_px'])}) : {_wib(tr['mss1_ts'])} (tidak entry, tunggu ujung MSS-1)", f"   Ujung MSS-1 : {_wib(tr['uj_ts'])} @ {g(tr['uj_px'])}",
                f"   Ujung MSS-1 tersentuh : {_wib(tr['touch2_ts'])}", f"   Swing MSS-2 awal ({lo_hi[1]} {'tertinggi' if long_ else 'terendah'} dari break MSS-1 s/d ujung tersentuh) : " + (f"{_wib(tr['sw20_ts'])} @ {g(tr['sw20_px'])}" if tr.get('sw20_ts') else 'belum ada')]
    _done = False
    for i_, (pt, pp, st_, sp) in enumerate(tr['hist'][1:], 1):
        if _n1 is not None and i_ == _n1 and not _done:
            o += _m1_lines(); _done = True
        o.append(f"   Struktur {'bearish' if long_ else 'bullish'} {i_} : P baru {_wib(pt)} @ {g(pp)} -> swing {_wib(st_)} @ {g(sp)}" if st_ else f"   Struktur {'bearish' if long_ else 'bullish'} {i_} : P baru {_wib(pt)} @ {g(pp)} -> swing tidak valid" + (", MSS belum bisa (tidak ada swing di antara P sebelumnya dan P ini)" if tr.get('strict_sw') else ", pakai swing sebelumnya"))
    if _n1 is not None and not _done:
        o += _m1_lines()
    o += [f"5. Swing yang di-break ({_m}) : {_wib(tr['sw_ts'])} @ {g(tr['sw_px'])}" + (f" (swing struktur ke-{tr['n_newp']}: di antara P sebelumnya dan P terakhir)" if tr.get('strict_sw') else ""), f"   P (ujung MSS) : {_wib(tr['p_ts'])} @ {g(tr['p_px'])} (P baru ke-{tr['n_newp']})",
          f"6. {_m} (close M5 menembus swing) : {_wib(tr['mss_ts'])}",
          *([f"Limit dipasang (setelah close MSS) : {_wib(tr['set_ts'])}", f"Limit terisi (candle M5) : {_wib(tr['fill_ts'])}", f"Entry (limit di swing yang di-break) : {g(tr['entry'])}"] if BS_M5_ENTRY != 'market' else [f"Entry (market, close MSS) : {g(tr['entry'])}"]), f"SL acuan ({tr.get('sl_basis', 'ujung MSS')}) : {_wib(tr['sl_ref_ts'])} @ {g(tr['sl_ref_px'])}", f"SL (acuan{' + ' + format(BS_M5_SLBUF, 'g') + '%' if BS_M5_SLBUF else ''}) : {g(tr['sl'])}", f"TP ({'titik tertinggi' if long_ else 'titik terendah'} range) : {g(tr['tp'])}",
          f"RR rencana : 1:{tr['rr']:.2f}", f"Jarak SL : {tr['dist'] / tr['entry'] * 100:.2f}%",
          f"Exit waktu : {_wib(tr['exit_ts'])}", f"Exit harga : {g(tr['exit_px'])}", f"Lama posisi : {held // 60}j {held % 60}m",
          f"Balance setelah : ${tr['bal_after']:.2f}", ""]
    return o


def _bs_block(k, tr):
    g = lambda v: f"{v:.8g}"
    long_ = tr['d'] == 'Long'
    held = (tr['exit_idx'] - tr['t']) * BS_TF
    why = {'SL': 'SL kena', 'TP': 'TP kena'}.get(tr['why'], tr['why'])
    low_hi = ('low', 'high') if long_ else ('high', 'low')
    kind = ('MSS + struktur searah' if BS_CONFIRM > 0 else 'MSS') if tr['bias_kind'] == 'mss' else 'balik setelah ujung MSS ter-break'
    return [f"Trade : {k}", f"Coin : {tr['symbol']}", f"Dir : {tr['d']}", f"Hasil bersih : {tr['r']:+.2f}R", f"Hasil kotor : {tr['gross_r']:+.2f}R", f"Fee : -{tr['fee_r']:.2f}R",
            f"Exit oleh : {why}", f"Bias : {tr['d']} ({kind})", f"Ujung bias (invalidasi) : {g(tr['bias_end'])}",
            f"{low_hi[0].capitalize()} yang di-sweep : {_wib(tr['cand_ts'])} @ {g(tr['cand_px'])}",
            f"Candle sweep : {_wib(tr['sw_ts'])} (low {g(tr['sw_lo'])}, high {g(tr['sw_hi'])})",
            f"Candle engulfing : {_wib(tr['eng_ts'])} (open {g(tr['eng_o'])}, close {g(tr['eng_c'])})",
            f"Limit dipasang (setelah close candle) : {_wib(tr['set_ts'])}", f"Limit terisi (candle) : {_wib(tr['fill_ts'])}",
            f"Entry (50% body engulfing) : {g(tr['entry'])}", f"SL ({'ujung wick candle engulfing' if BS_SL == 'eng' else 'ujung wick candle sweep' if BS_SL == 'wick' else '50% range candle sweep'}) : {g(tr['sl'])}", f"TP ({'titik tertinggi' if long_ else 'titik terendah'} range) : {g(tr['tp'])}",
            f"RR rencana : 1:{tr['rr']:.2f}", f"Jarak SL : {tr['dist'] / tr['entry'] * 100:.2f}%",
            f"Exit waktu : {_wib(tr['exit_ts'])}", f"Exit harga : {g(tr['exit_px'])}", f"Lama posisi : {held // 60}j {held % 60}m",
            f"Balance setelah : ${tr['bal_after']:.2f}", ""]


def _flip_block(k, tr):
    g = lambda v: f"{v:.8g}"
    long_ = tr['d'] == 'Long'
    pk, sk = ('swing low', 'swing high') if long_ else ('swing high', 'swing low')
    why = {'SL': 'SL kena', 'FLIP': 'MSS lawan (flip)'}.get(tr['why'], tr['why'])
    held = (tr['exit_idx'] - tr['t']) * MF_TF
    head = [f"Trade : {k}", f"Coin : {tr['symbol']}", f"Dir : {tr['d']}", f"Hasil bersih : {tr['r']:+.2f}R", f"Hasil kotor : {tr['gross_r']:+.2f}R", f"Fee : -{tr['fee_r']:.2f}R",
            f"Exit oleh : {why}"]
    if tr.get('kind') == 'rev':
        mid = [f"Entry oleh : break ujung MSS (SL trade sebelumnya, masuk {_wib(tr['from_ts'])})", f"Level ujung MSS yang di-break : {g(tr['brk_level'])}",
               f"Pergerakan {'tertinggi' if not long_ else 'terendah'} sebelum break (SL) : {g(tr['ext_px'])} @ {_wib(tr['ext_ts'])}"]
    else:
        mid = [f"Entry oleh : MSS", f"Jumlah struktur sebelum MSS : {tr['ns']}",
               f"P awal rantai ({pk}) : {_wib(tr['p_first_ts'])}",
               f"P lama ({pk}) : {_wib(tr['p_prev_ts'])}",
               f"P baru = ujung MSS ({pk}) : {_wib(tr['p_ts'])} @ {g(tr['p_px'])}",
               f"Struktur terakhir menyentuh ujung {tr['touch_kind']} P lama : {g(tr['touch_px'])}",
               f"Swing yang di-break ({sk}) : {_wib(tr['sw_ts'])} @ {g(tr['sw_px'])}",
               f"MSS (close menembus swing) : {_wib(tr['mss_ts'])}"]
    return head + mid + [f"Entry market : {g(tr['entry'])}", f"SL : {g(tr['sl'])}", f"Jarak SL : {tr['dist'] / tr['entry'] * 100:.2f}%",
            f"Exit waktu : {_wib(tr['exit_ts'])}", f"Exit harga : {g(tr['exit_px'])}", f"Lama posisi : {held // 60}j {held % 60}m",
            f"Balance setelah : ${tr['bal_after']:.2f}", ""]


def _fibo_block(k, tr):
    fb = tr['fb']; long_ = tr['d'] == 'Long'
    ph, pl = ('swing high', 'swing low') if long_ else ('swing low', 'swing high')
    ud = ('atas', 'bawah') if long_ else ('bawah', 'atas')
    g = lambda v: f"{v:.8g}"
    o = [f"TRADE {k} | {tr['d']} | {tr['why']} {tr['r']:+.2f}R | {tr['symbol']}",
         f"Catatan arah : {tr['d']} -> P = {ph}, swing low/high pemicu = {pl} (waktu WIB)", "",
         "1. P LAMA DAN P BARU",
         f"   P lama ({ph}) : {_wibs(fb['p_old'])} @ {g(fb['p_old_px']) if fb['p_old_px'] is not None else '-'}",
         f"   P baru ({ph}, menembus P lama ke {ud[0]}) : {_wibs(fb['p_new'])} @ {g(fb['p_new_px'])}",
         (f"   P lama di-break BODY : {_wibs(fb['brk_ts'])}, close {g(fb['brk_close'])}" if fb.get('brk_ts') is not None else "   P lama di-break BODY : -"),
         f"   {pl.capitalize()} di antara keduanya (L) : {g(fb['L_sweep'])} ({_wibs(fb['L_sw_ts'])})", "",
         f"2. {pl.upper()} DI-SWEEP (WICK)",
         f"   Candle sweep : {_wibs(fb['sweep_ts'])}",
         f"   Wick menyentuh : {g(fb['sweep_px'])} (L = {g(fb['L_sweep'])})",
         f"   Close candle sweep : {g(fb['sweep_close'])} (tidak menembus L, jadi hanya sweep)", "",
         "3. P BARU DI-BREAK = BOS BESAR TERBENTUK",
         f"   Candle break : {_wibs(fb['bos_ts'])}, close {g(fb['bos_close'])} (menembus P baru {g(fb['p_new_px'])})",
         f"   Ujung bawah BOS besar (100%) : {g(fb['bottom_px'])} ({_wibs(fb['bottom_ts'])})", "",
         "4. RANTAI P BARU DARI UJUNG BAWAH"]
    ch = fb['chain']
    for i_, (ts_, px_) in enumerate(ch, 1):
        o.append(f"   P{i_}' : {_wibs(ts_)} @ {g(px_)}" + ("  <- P terakhir" if i_ == len(ch) else ""))
    o += [f"   {pl.capitalize()} pemicu (di antara 2 P terakhir) : {g(fb['L_trig'])} (terbentuk {_wibs(fb['L_trig_ts'])})", "",
          "5. PEMICU",
          f"   {pl.capitalize()} pemicu tersentuh : {_wibs(fb['trig_ts'])} (harga {g(fb['trig_px'])})", "",
          "6. FIBONACCI",
          f"   Ujung atas 0% : {g(fb['top_px'])} ({_wibs(fb['top_ts'])})",
          f"   Ujung bawah 100% : {g(fb['bottom_px'])} ({_wibs(fb['bottom_ts'])})",
          f"   Range : {g(fb['range'])}",
          f"   Entry limit {FB_ENTRY_DEPTH*100:.1f}% : {g(tr['entry'])}",
          f"   SL 100% : {g(tr['sl'])}",
          (f"   TP (ujung body atas BOS besar) : {g(tr['tp'])} ({_wibs(fb['tp_ts'])})" if fb.get('tp_ts') is not None else
           f"   TP (-{FB_TP_EXT*100:.0f}% di luar 0%) : {g(tr['tp'])}"),
          f"   RR target : 1:{tr['rr']:.2f}", "",
          "7. HASIL",
          f"   Limit terfill : {_wibs(fb['fill_ts'])}",
          f"   Exit : {tr['why']} pada {_wibs(tr['exit_ts'])}",
          f"   Hasil : {tr['r']:+.2f}R",
          f"   Balance setelah : ${tr['bal_after']:.2f}", ""]
    return o


def _struct_txt(only=None):
    """TXT struktur H1 (tanpa trade): urutan struktur (P ditembus P baru), MSS long/short, dan pembalikan arah bias. Satu blok per kejadian, satu field per baris."""
    syms = [only] if only else list(_STRUCT_EV)
    o = [f"STRUKTUR H1 (TF {BS_TF}m) - cara bot menemukan struktur, MSS, dan pembalikan arah. Tanpa trade.", f"Waktu = WIB, candle H1 ditulis jam BUKA-nya. Swing N={BS_N} kiri-kanan. P baru harus menyentuh ujung {'body' if MF_BODY else 'wick'} P sebelumnya (P2 dst).",
         f"Bias berubah hanya kalau ada MSS lalu diikuti minimal {max(BS_CONFIRM, 1)} struktur searah MSS (BS_CONFIRM={BS_CONFIRM}).", ""]
    for sy in syms:
        d = _STRUCT_EV.get(sy)
        if not d:
            continue
        ev = d['ev']; tl = lambda e: 'LOW' if e['sup'] else 'HIGH'
        n_ml = sum(1 for e in ev if e['type'] == 'mss' and e['sup']); n_ms = sum(1 for e in ev if e['type'] == 'mss' and not e['sup'])
        biases = [e for e in ev if e['type'] == 'bias']; n_rev = sum(1 for e in biases if e['prev'] is not None and e['prev'] != e['sup'])
        o += ["=" * 60, f"COIN : {sy}", f"Data H1 : {_wib(d['first'])} s/d {_wib(d['last'])} ({d['n']} candle H1)", f"Total struktur low (menuju mss_long) : {sum(1 for e in ev if e['type'] == 'struktur' and e['sup'])}",
              f"Total struktur high (menuju mss_short) : {sum(1 for e in ev if e['type'] == 'struktur' and not e['sup'])}", f"Total mss_long : {n_ml}", f"Total mss_short : {n_ms}",
              f"Bias dimulai/berubah : {len(biases)} (pembalikan arah: {n_rev})", "", "ALUR BIAS (urut waktu)"]
        for e in biases:
            pv = 'awal' if e['prev'] is None else ('Long' if e['prev'] else 'Short')
            o.append(f"   {_wib(e['t'])} | {pv} -> {'Long' if e['sup'] else 'Short'}" + (" (PEMBALIKAN)" if e['prev'] is not None and e['prev'] != e['sup'] else ""))
        o += ["", "KEJADIAN (urut waktu)", ""]
        for i_, e in enumerate(ev, 1):
            ty = e['type']
            if ty == 'struktur':
                o += [f"#{i_} STRUKTUR{e['n']} ({tl(e)}, menuju {'mss_long' if e['sup'] else 'mss_short'})", f"Terkonfirmasi (candle H1) : {_wib(e['t'])}",
                      f"P yang ditembus (P{e['n']}) : {_wib(e['p_old'][0])} @ {e['p_old'][1]:.8g}", f"P penembus (P{e['n'] + 1}) : {_wib(e['p_new'][0])} @ {e['p_new'][1]:.8g}",
                      f"Syarat tembus (ujung {e['basis']} P{e['n']}) : {e['thr']:.8g}", f"Swing yang harus di-break untuk MSS : {_wib(e['sw'][0])} @ {e['sw'][1]:.8g}"]
                if e['pm'] is not None and e['pm'] == (not e['sup']):
                    o.append(f"Catatan : struktur searah mss_{'long' if e['pm'] else 'short'} yang sedang menunggu konfirmasi bias")
                o.append("")
            elif ty == 'mss':
                ln = 'long' if e['sup'] else 'short'; bb = 'belum ada' if e['bias'] is None else ('Long' if e['bias'] else 'Short')
                act = {'searah': f"MSS searah bias ({bb}): bias tetap, ujung bias dipindah ke ujung MSS terbaru", 'pm_tunggu': f"MSS lawan bias ({bb}): bias BELUM berubah, menunggu {e['need']} struktur searah mss_{ln}",
                       'pm_tunggu_ganti': f"MSS lawan bias ({bb}): menggantikan MSS lain yang menunggu, menunggu {e['need']} struktur searah mss_{ln}", 'pm_diabaikan': f"MSS searah MSS yang sedang menunggu: diabaikan", 'bias_langsung': f"bias langsung berubah menjadi {ln.capitalize()}"}[e['action']]
                o += [f"#{i_} MSS_{ln.upper()}", f"Terjadi (candle H1 yang close-nya menembus) : {_wib(e['t'])} close {e['close']:.8g}", f"Swing yang di-break : {_wib(e['sw'][0])} @ {e['sw'][1]:.8g}", f"Jumlah struktur sebelum MSS : {e['n']}",
                      f"P terakhir ({'ujung bawah' if e['sup'] else 'ujung atas'}) : {_wib(e['p_last'][0])} @ {e['p_last'][1]:.8g}", f"Ujung MSS : {e['end']:.8g}", f"Titik {'tertinggi' if e['sup'] else 'terendah'} dari P terakhir sampai MSS : {_wib(e['top'][0])} @ {e['top'][1]:.8g}",
                      f"Bias sebelum : {bb}", f"Aksi bot : {act}", ""]
            elif ty == 'pm_ok':
                o += [f"#{i_} KONFIRMASI STRUKTUR SEARAH mss_{'long' if e['sup'] else 'short'}", f"Waktu : {_wib(e['t'])}", f"Jumlah struktur searah : {e['n']}", ""]
            elif ty == 'bias':
                pv = 'awal (belum ada)' if e['prev'] is None else ('Long' if e['prev'] else 'Short')
                o += [f"#{i_} BIAS {'LONG' if e['sup'] else 'SHORT'}" + (" - PEMBALIKAN ARAH" if e['prev'] is not None and e['prev'] != e['sup'] else ""), f"Waktu : {_wib(e['t'])}", f"Bias sebelum : {pv}", f"Ujung bias : {e['end']:.8g}",
                      f"Titik {'tertinggi' if e['sup'] else 'terendah'} range : {_wib(e['ext_ts'])} @ {e['ext']:.8g}", ""]
            elif ty == 'pm_fail':
                o += [f"#{i_} MSS_{'LONG' if e['sup'] else 'SHORT'} GAGAL", f"Waktu : {_wib(e['t'])}", f"Alasan : ujung MSS ({e['end']:.8g}) ter-break sebelum ada struktur searah; bias tidak berubah", ""]
            elif ty == 'pm_cancel':
                o += [f"#{i_} MSS menunggu DIBATALKAN (muncul MSS searah bias)", f"Waktu : {_wib(e['t'])}", ""]
    return '\n'.join(o).encode('utf-8')


def _trades_txt():
    with _lock:
        trades = list(_trades); phase = _phase
    if not trades:
        return ('Belum ada trade (backtest masih berjalan atau tidak ada sinyal).\n' if phase != 'done' else 'Tidak ada trade.\n').encode('utf-8')
    out = []
    for k, tr in enumerate(trades, 1):
        if tr.get('mode') == 'bias_sweep':
            out += (_bsm_block(k, tr) if tr.get('bs_m5') else _bs_block(k, tr)); continue
        if tr.get('mode') == 'mss_flip':
            out += _flip_block(k, tr); continue
        if tr.get('mode') == 'fibo_bos':
            out += _fibo_block(k, tr); continue
        if tr.get('mode') == 'mss_only':
            mid = ([f"P pertama (P1) : {_wib(tr['p1'])}", f"Awal struktur (P-1) : {_wib(tr['pstart'])}"] if tr.get('pstart') is not None else []) + \
                  [f"P MSS (ujung MSS) : {_wib(tr['ptime'])}", f"MSS{'' if tr.get('bos_conf') else ' (entry)'} : {_wib(tr['mss'])}"] + \
                  ([f"SH2 (menembus SH1) : {_wib(tr['sh2'])}", f"SH3 (menembus SH2) : {_wib(tr['sh3'])}", f"Swing BOS (SL) : {_wib(tr['sl_swing'])}",
                    f"BOS terkonfirmasi (entry) : {_wib(tr['bos_conf'])}"] if tr.get('bos_conf') else [])
        elif tr['bo'] is None:
            mid = [f"Level (acuan) : {tr['acuan']:.8g}", f"Level terbentuk : {_wib(tr['formed'])}", f"Level tersentuh M5 : {_wib(tr['touch'])}",
                   f"P MSS (ujung MSS) : {_wib(tr['ptime'])}", f"MSS (entry) : {_wib(tr['mss'])}"]
        else:
            mid = [f"Level : {tr['lvl']:.8g}", f"Level terbentuk : {_wib(tr['formed'])}", f"Break-out H1 : {_wib(tr['bo'])}",
                   f"MSS pertama : {_wib(tr['mss1'])}", f"Acuan : {tr['acuan']:.8g}", f"Acuan tersentuh : {_wib(tr['touch'])}",
                   f"P MSS kedua : {_wib(tr['ptime'])}", f"MSS kedua (entry) : {_wib(tr['mss'])}"]
        if tr.get('bo_m5') is not None:
            mid = [x.replace(' (entry)', '') for x in mid] + [f"Break-out ujung MSS : {_wib(tr['bo_m5'])}", f"Break-in ujung MSS (entry) : {_wib(tr['bi_m5'])}"]
        out += [f"Trade : {k}", f"Coin : {tr['symbol']}", f"Dir : {tr['d']}", f"Hasil : {tr['why']} {tr['r']:+.2f}R"] + mid + [
                f"Entry : {tr['entry']:.8g}", f"SL : {tr['sl']:.8g}", f"TP : {tr['tp']:.8g}", f"RR target : 1:{tr['rr']:.2f}",
                f"Exit waktu : {_wib(tr['exit_ts'])}", f"Balance setelah : ${tr['bal_after']:.2f}", ""]
    return '\n'.join(out).encode('utf-8')


def _funnel_lines(f):
    if NS_MODE == 'bias_sweep' and BS_ENTRY == 'mss_m5':
        return [f"P valid H1 : {f.get('bs_p',0)}", f"Struktur H1 : {f.get('bs_struct',0)}", f"MSS H1 (semua) : {f.get('bs_mss',0)}", f"Bias berubah/ditetapkan : {f.get('bs_bias',0)}",
                f"Bias balik karena ujung MSS ter-break : {f.get('bs_flipback',0)}", f"Bias dikosongkan : {f.get('bs_clear',0)}", f"Pencarian direset (harga menyentuh titik tertinggi/terendah range) : {f.get('bs_top_reset',0)}",
                f"Low/high H1 tersentuh di M5 : {f.get('m5_touch',0)}", f"P baru M5 (P bawah ditembus, swing dihitung ulang) : {f.get('m5_newp',0)}", f"Sentuhan tanpa swing awal valid : {f.get('m5_noswing',0)}",
                f"Batal: harga sampai titik tertinggi/terendah range : {f.get('m5_cancel_top',0)}", f"Batal: ujung bias tersentuh : {f.get('m5_cancel_end',0)}", f"Low tersentuh saat posisi/limit masih ada (dilewati, cari low lebih bawah) : {f.get('m5_touch_busy',0)}", f"Batal: bias berubah : {f.get('m5_cancel_bias',0)}",
                f"Low dibuang: tidak ada FVG fresh {'di bawah' if True else ''} low (bukan kandidat) : {f.get('fvg_skip_cand',0)}", f"FVG dalam zona: MSS dicari sejak pertama kali masuk zona : {f.get('fvgz_first',0)} | FVG tersentuh : {f.get('fvgz_touch',0)} (MSS keduluan sebelum FVG = tidak valid : {f.get('fvg_mss_first',0)}) | gagal (MSS kena SL, tunggu FVG lain) : {f.get('fvgz_sl',0)} | dilewati (posisi/limit masih ada) : {f.get('fvgz_busy',0)}", f"Low dibuang: di luar zona struktur terbaru : {f.get('zone_skip_cand',0)} (kandidat lama dibuang karena zona berubah : {f.get('zone_drop',0)})", f"FVG tersentuh setelah low tersentuh : {f.get('fvg_touch',0)}", f"Gugur: MSS M5 terjadi sebelum FVG tersentuh : {f.get('fvg_mss_first',0)}", f"Batal: MSS lawan terjadi lebih dulu (tracker M5) : {f.get('m5_cancel_pm',0)}", f"Low tersentuh saat MSS lawan menunggu konfirmasi (dilewati) : {f.get('pm_block',0)}", f"Low tersentuh saat warm-up ({BS_WARMUP} candle H1 pertama, tidak trade) : {f.get('warm_skip',0)}", f"Low tersentuh tapi di atas {BS_FIB_DEPTH * 100:g}% range Fibonacci (dilewati) : {f.get('fib_skip_touch',0)}", f"MSS-1 M5 terbentuk (tunggu ujung MSS-1) : {f.get('m5_mss1',0)}", f"Ujung MSS-1 tersentuh (cari MSS-2) : {f.get('m5_wait_touch',0)}", f"MSS M5 final terbentuk : {f.get('m5_mss',0)}", f"Limit dipasang : {f.get('bs_setup',0)}", f"Limit batal (TP tersentuh dulu) : {f.get('bs_cancel_tp',0)}", f"Limit belum terisi di akhir data : {f.get('bs_pend_end',0)}", f"MSS dibuang: RR rencana di bawah 1:{BS_M5_MINRR:g} (tidak trade) : {f.get('m5_rr_skip',0)}", f"MSS dibuang (TP/SL tidak valid atau posisi masih terbuka) : {f.get('m5_mss_skip',0)}", f"Entry market (jadi posisi) : {f.get('bs_fill',0)}"]
    if NS_MODE == 'bias_sweep':
        return [f"P valid : {f.get('bs_p',0)}", f"Struktur : {f.get('bs_struct',0)}", f"MSS (semua) : {f.get('bs_mss',0)}", f"MSS menunggu struktur searah (bias belum berubah) : {f.get('bs_pm',0)}", f"  jadi bias setelah ada struktur searah : {f.get('bs_pm_ok',0)}", f"  gagal, ujung MSS ter-break sebelum ada struktur : {f.get('bs_pm_fail',0)}", f"  dibatalkan MSS searah bias : {f.get('bs_pm_cancel',0)}", f"Bias berubah/ditetapkan : {f.get('bs_bias',0)}", f"MSS searah bias (bias tetap, hanya ujung bias dipindah) : {f.get('bs_refresh',0)}",
                f"Bias balik karena ujung MSS ter-break : {f.get('bs_flipback',0)}", f"Bias dikosongkan (ujung bias balik ter-break) : {f.get('bs_clear',0)}",
                f"Pencarian direset (harga menyentuh titik tertinggi/terendah range) : {f.get('bs_top_reset',0)}", f"Low/high gagal (close/body menembus = terbreak, bukan sweep) : {f.get('bs_cand_fail',0)}", f"Candle pertama menyentuh low/high, tidak terbreak (sweep wick) : {f.get('bs_sweep',0)}", f"Low gagal (candle sesudah sentuhan tidak engulfing) : {f.get('bs_eng_fail',0)}", f"  di antaranya close sudah menembus tapi wick engulfing melebihi wick candle sweep : {f.get('bs_eng_wick',0)}", f"Sweep + engulfing : {f.get('bs_engulf',0)}", f"Limit dipasang : {f.get('bs_setup',0)}",
                f"Limit batal (TP tersentuh dulu) : {f.get('bs_cancel_tp',0)}", f"Limit batal (bias berubah) : {f.get('bs_cancel_bias',0)}", f"Limit belum terisi di akhir data : {f.get('bs_pend_end',0)}", f"Limit terisi (jadi posisi) : {f.get('bs_fill',0)}"]
    if NS_MODE == 'mss_flip':
        return [f"P valid (swing {MF_N} kiri-kanan) : {f.get('mf_p',0)}", f"Struktur (P baru menembus P lama) : {f.get('mf_struct',0)}", f"MSS terbentuk : {f.get('mf_mss',0)}",
                f"Entry (MSS jadi posisi) : {f.get('signal',0)}", f"Posisi ditutup flip (MSS lawan) : {f.get('mf_flip',0)}", f"Posisi kena SL : {f.get('mf_sl',0)}",
                f"MSS searah saat posisi terbuka (diabaikan) : {f.get('mf_same',0)}", f"Entry lawan arah setelah SL (break ujung MSS) : {f.get('mf_rev',0)}", f"MSS dibuang (jarak SL nol) : {f.get('mf_nodist',0)}"]
    if NS_MODE == 'fibo_bos':
        return [f"P lama cuma dilewati wick, tidak di-break body (dibuang) : {f.get('fb_wickonly',0)}", f"Pasangan P (P di-break body P baru, swing low valid) : {f.get('fb_pair',0)}", f"Pasangan tanpa swing low valid : {f.get('fb_pair_noL',0)}",
                f"Swing low di-sweep wick : {f.get('fb_sweep',0)}", f"Swing low di-break body (batal) : {f.get('fb_closebreak',0)}", f"P di-break tanpa sweep (batal) : {f.get('fb_nosweep',0)}",
                f"BOS besar terbentuk : {f.get('fb_bos',0)}", f"BOS besar batal (ujung bawah diambil sebelum pemicu) : {f.get('fb_invalid',0)}",
                f"Swing low P tersentuh (pemicu) : {f.get('fb_trigger',0)}", f"Limit batal (TP tercapai sebelum terfill) : {f.get('fb_cancel',0)}",
                f"Limit tidak terfill sampai akhir data : {f.get('fb_nofill',0)}", f"Limit terfill (sinyal entry) : {f.get('signal',0)}"]
    if NS_MODE == 'mss_only':
        if NS_BOS:
            return [f"MSS tanpa BOS sampai akhir jendela : {f.get('no_bos',0)}", f"MSS gagal (ujung MSS tertembus sebelum BOS) : {f.get('bos_gagal',0)}",
                    f"Sinyal entry (BOS terbentuk) : {f.get('signal',0)}"]
        return [f"Sinyal MSS (entry langsung) : {f.get('signal',0)}"]
    base = [f"Level H1 awal (pola c1/c2) : {f.get('level',0)}", f"Level lolos filter {NS_LV_N} kiri-kanan : {f.get('level_valid',0)}"]
    if NS_MODE == 'touch':
        return base + [f"Level tersentuh M5 : {f.get('touch',0)}", f"Level tak pernah tersentuh : {f.get('no_touch',0)}",
                       f"Tanpa MSS setelah tersentuh : {f.get('no_mss2',0)}", f"Sinyal entry (MSS) : {f.get('signal',0)}"]
    return base + [f"Break-out : {f.get('breakout',0)}", f"Tanpa MSS pertama : {f.get('no_mss1',0)}",
                   f"MSS pertama (acuan) : {f.get('mss1',0)}", f"Acuan tak pernah tersentuh : {f.get('no_touch',0)}",
                   f"Acuan tersentuh : {f.get('touch',0)}", f"Tanpa MSS kedua : {f.get('no_mss2',0)}", f"Sinyal entry (MSS kedua) : {f.get('signal',0)}"]


def _ringkasan_txt():
    with _lock:
        s = dict(_summary); f = dict(_funnel); mo = list(_monthly); avg = _avg_monthly_growth; ps = list(_per_symbol); phase = _phase; cres = list(_coin_res)
    if phase != 'done':
        return f'Backtest belum selesai (status: {phase}).\n'.encode('utf-8')
    o = [f"RINGKASAN BACKTEST {NS_MODE}", f"Periode : {BACKTEST_START_DATE} s/d {BACKTEST_END_DATE}", f"Koin : {len(SYMBOLS)}", *([f"Mode akun : TERPISAH per koin, modal ${INITIAL_BALANCE:g} masing-masing (total modal ${s.get('modal_total', 0):.0f}); angka di bawah = penjumlahan semua koin, Max drawdown = terburuk di antara koin"] if SEPARATE_COINS else []),
         f"Total trade : {s['n_trades']}", f"Menang / Kalah : {s['n_win']} / {s['n_loss']}", f"Win rate : {s['wr']:.1f}%",
         f"Total R : {s['total_r']:.2f}", f"Rata-rata R : {s['avg_r']:.2f}", (f"Total R kotor (sebelum fee) : {s.get('gross_r',0):.2f}" if NS_MODE in ('mss_flip', 'bias_sweep') else f"Rata-rata RR target : 1:{s.get('avg_rr',0):.2f}"), (f"Total fee : -{s.get('fee_r',0):.2f}R" if NS_MODE in ('mss_flip', 'bias_sweep') else ""), (f"Rata-rata jarak SL : {s.get('avg_dist_pct',0):.2f}% dari entry" if NS_MODE in ('mss_flip', 'bias_sweep') else ""), f"Balance awal : ${s.get('modal_total', INITIAL_BALANCE) if SEPARATE_COINS else INITIAL_BALANCE:.2f}" + (" (total semua koin)" if SEPARATE_COINS else ""),
         f"Balance akhir : ${s['final_balance']:.2f}", f"ROI : {s['roi']:+.1f}%", f"Max drawdown : {s['mdd']:.1f}%",
         f"Rata-rata growth per bulan : {avg:+.2f}%", "", "FUNNEL",
         ] + _funnel_lines(f) + [
         ] + ([] if NS_MODE in ('fibo_bos', 'mss_flip', 'bias_sweep') else [f"Dibuang: TP tidak valid (di sisi salah dari entry) : {f.get('tp_invalid',0)}"] if NS_MODE == 'mss_only' else [f"Ujung MSS tak pernah break-out : {f.get('no_bo',0)}", f"Kadaluarsa (tak break-in dlm {NS_EXPIRE_MIN} menit) : {f.get('expired',0)}", f"Dibuang: entry sudah lewat titik TP terjauh : {f.get('tp_invalid',0)}"]) + [
         f"Sinyal kembar dilewati : {f.get('dup',0)}", f"Dilewati posisi searah masih terbuka : {f.get('open_same',0)}",
         f"Dilewati batas slot : {f.get('slot',0)}", f"Dilewati margin kurang : {f.get('margin',0)}",
         f"Posisi belum selesai di akhir data : {f.get('terbuka',0)}", "", "PER BULAN (basis waktu exit, WIB" + ("; gabungan semua koin, balance = total semua akun)" if SEPARATE_COINS else ")")]
    for m in mo:
        o += [f"Bulan : {m['month']}", f"Trade : {m['n']}", f"Win rate : {m['wr']:.1f}%", f"Total R : {m['total_r']:.2f}",
              f"Balance awal : ${m['start']:.2f}", f"Balance akhir : ${m['end']:.2f}", f"Growth : {m['growth']:+.2f}%", ""]
    if SEPARATE_COINS and cres:
        o += [f"BACKTEST TERPISAH PER KOIN (urut total R, modal ${INITIAL_BALANCE:g} masing-masing)", ""]
        cm = {r_['symbol']: r_ for r_ in cres}
        for r in ps:
            c_ = cm[r['symbol']]; sm = c_['summ']
            o += [f"Coin : {r['symbol']}", f"Modal awal : ${INITIAL_BALANCE:g}", f"Trade : {sm['n_trades']}", f"Menang / Kalah : {sm['n_win']} / {sm['n_loss']}", f"Win rate : {sm['wr']:.1f}%",
                  f"Total R : {sm['total_r']:.2f}", f"Total R kotor (sebelum fee) : {sm['gross_r']:.2f}", f"Total fee : -{sm['fee_r']:.2f}R", f"Rata-rata RR rencana : 1:{sm['avg_rr']:.2f}",
                  f"Balance akhir : ${sm['final_balance']:.2f}", f"ROI : {sm['roi']:+.1f}%", f"Max drawdown : {sm['mdd']:.1f}%", f"Rata-rata growth per bulan : {c_['avg']:+.2f}%",
                  f"Dilewati batas slot / margin / searah : {c_['bl']['slot']} / {c_['bl']['margin']} / {c_['bl']['open_same']}"]
            for m in c_['monthly']:
                o += [f"   Bulan {m['month']} : {m['n']} trade, WR {m['wr']:.0f}%, R {m['total_r']:+.2f}, balance ${m['start']:.2f} -> ${m['end']:.2f} ({m['growth']:+.2f}%)"]
            o += [""]
        return '\n'.join(o).encode('utf-8')
    o += ["PER KOIN (urut total R)"]
    for r in ps:
        o += [f"Coin : {r['symbol']}", f"Trade : {r['n']}", f"Menang / Kalah : {r['tp']} / {r['sl']}", f"Win rate : {r['wr']:.1f}%",
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
    body = [f"<h2>Backtest {NS_MODE}</h2><p>{st_txt} — {len(SYMBOLS)} koin, {BACKTEST_START_DATE} s/d {BACKTEST_END_DATE}</p>"
            + ((f"<div class='note'>Mode <b>bias_sweep</b> (TF {BS_TF}m): struktur P → <b>MSS</b> = bias → low tersentuh → <b>MSS di M5</b> → " if BS_ENTRY == 'mss_m5' else f"<div class='note'>Mode <b>bias_sweep</b> (TF {BS_TF}m): struktur P → <b>MSS</b> = bias → sweep + engulfing di range → limit 50% body → ") if NS_MODE == 'bias_sweep' else "<div class='note'>Mode <b>mss_flip</b> (M5 saja): struktur P → <b>MSS</b> → " if NS_MODE == 'mss_flip' else
               "<div class='note'>Mode <b>mss_only</b>: murni M5, tanpa level H1 → cari <b>MSS</b> → " if NS_MODE == 'mss_only' else
               "<div class='note'>Mode <b>fibo_bos</b> (M5 saja): " if NS_MODE == 'fibo_bos' else
               f"<div class='note'>Level awal H1 (tanpa FVG, ujung wick {NS_LV_N} kiri-kanan) = <b>acuan</b> → tersentuh di M5 → cari <b>MSS</b> → "
               if NS_MODE == 'touch' else
               f"<div class='note'>Level awal H1 (tanpa FVG, ujung wick {NS_LV_N} kiri-kanan) → break-out body → <b>MSS pertama</b> (acuan) → acuan tersentuh → <b>MSS kedua</b> → ")
            + f"{_entry_desc()}. Risk {RISK_PCT*100:.1f}%/trade (compounding), leverage {LEVERAGE:g}x. {'Backtest TERPISAH per koin, modal masing-masing.' if SEPARATE_COINS else 'Akun gabungan.'}</div>"]
    if phase == 'done' and s:
        cls = 'pos' if s['total_r'] >= 0 else 'neg'
        body.append(f"<div class='cards'><div class='c'><span>Trade</span><b>{s['n_trades']}</b></div>"
                    f"<div class='c'><span>Win rate</span><b>{s['wr']:.1f}%</b></div>"
                    f"<div class='c'><span>Total R</span><b class='{cls}'>{s['total_r']:+.2f}</b></div>"
                    f"<div class='c'><span>ROI</span><b class='{cls}'>{s['roi']:+.1f}%</b></div>"
                    f"<div class='c'><span>Balance</span><b>${s['final_balance']:.2f}</b></div>"
                    f"<div class='c'><span>Max DD</span><b>{s['mdd']:.1f}%</b></div></div>")
        body.append(f"<p><a href='/trades.txt' download='trades_{NS_MODE}.txt'>⬇️ Download trades.txt</a> &nbsp; <a href='/ringkasan.txt' download='ringkasan_{NS_MODE}.txt'>⬇️ Download ringkasan.txt</a> &nbsp; <a href='/struktur.txt' download='struktur_h1_{NS_MODE}.txt'>⬇️ Download struktur H1</a></p><p class='small'><a href='/trades.txt?view=1'>👁 lihat trades</a> &nbsp; <a href='/ringkasan.txt?view=1'>👁 lihat ringkasan</a> &nbsp; <a href='/struktur.txt?view=1'>👁 lihat struktur H1</a> &nbsp; <a href='/logs'>📜 logs</a></p>")
        if NS_MODE == 'bias_sweep' and BS_ENTRY == 'mss_m5':
            chain = f"MSS H1 {f.get('bs_mss',0)} → bias {f.get('bs_bias',0)} (balik {f.get('bs_flipback',0)}) → low tersentuh {f.get('m5_touch',0)} → MSS M5 {f.get('m5_mss',0)} → entry {f.get('bs_fill',0)} (batal: top {f.get('m5_cancel_top',0)}, ujung bias {f.get('m5_cancel_end',0)}, bias berubah {f.get('m5_cancel_bias',0)})"
        elif NS_MODE == 'bias_sweep':
            chain = f"MSS {f.get('bs_mss',0)} → bias {f.get('bs_bias',0)} (balik {f.get('bs_flipback',0)}) → sweep {f.get('bs_sweep',0)} → engulfing {f.get('bs_engulf',0)} → limit {f.get('bs_setup',0)} (batal TP {f.get('bs_cancel_tp',0)}) → terisi {f.get('bs_fill',0)}"
        elif NS_MODE == 'mss_flip':
            chain = f"P valid {f.get('mf_p',0)} → struktur {f.get('mf_struct',0)} → MSS {f.get('mf_mss',0)} → entry {f.get('signal',0)} (flip {f.get('mf_flip',0)}, SL {f.get('mf_sl',0)}, searah diabaikan {f.get('mf_same',0)})"
        elif NS_MODE == 'fibo_bos':
            chain = f"BOS besar {f.get('fb_bos',0)} → batal {f.get('fb_invalid',0)}, pemicu {f.get('fb_trigger',0)} → limit batal {f.get('fb_cancel',0)}, tidak fill {f.get('fb_nofill',0)} → terfill {f.get('signal',0)}"
        elif NS_MODE == 'mss_only':
            chain = (f"MSS tanpa BOS {f.get('no_bos',0)}, gagal {f.get('bos_gagal',0)} → sinyal BOS {f.get('signal',0)}" if NS_BOS else f"Sinyal MSS M5 {f.get('signal',0)}")
        elif NS_MODE == 'touch':
            chain = f"Level {f.get('level',0)} → lolos filter {f.get('level_valid',0)} → tersentuh M5 {f.get('touch',0)} → sinyal MSS {f.get('signal',0)}"
        else:
            chain = (f"Level {f.get('level',0)} → lolos filter {f.get('level_valid',0)} → break-out {f.get('breakout',0)} → MSS pertama {f.get('mss1',0)} → "
                     f"acuan tersentuh {f.get('touch',0)} → sinyal MSS kedua {f.get('signal',0)}")
        body.append("<h3>Funnel</h3><p class='small'>" + chain +
                    f" [no break-out {f.get('no_bo',0)}, kadaluarsa {f.get('expired',0)}, TP tak valid {f.get('tp_invalid',0)}] (kembar {f.get('dup',0)}, posisi searah terbuka {f.get('open_same',0)}, slot {f.get('slot',0)}, margin {f.get('margin',0)}).</p>")
        body.append(f"<h3>Pertumbuhan per Bulan <small>(rata-rata {avg:+.2f}%/bulan)</small></h3><table><tr><th>Bulan</th><th>Trade</th><th>WR</th><th>R</th><th>Awal</th><th>Akhir</th><th>Growth</th></tr>")
        for m in mo:
            c_ = 'pos' if m['profit'] >= 0 else 'neg'
            body.append(f"<tr><td>{m['month']}</td><td>{m['n']}</td><td>{m['wr']:.0f}%</td><td class='{c_}'>{m['total_r']:+.2f}</td><td>${m['start']:.2f}</td><td>${m['end']:.2f}</td><td class='{c_}'>{m['growth']:+.2f}%</td></tr>")
        body.append("</table>")
        if SEPARATE_COINS and ps and 'roi' in ps[0]:
            body.append(f"<h3>Backtest terpisah per koin (modal ${INITIAL_BALANCE:g} masing-masing)</h3><table><tr><th>Koin</th><th>Trade</th><th>Menang/Kalah</th><th>WR</th><th>R</th><th>Saldo akhir</th><th>ROI</th><th>Max DD</th></tr>")
            for r in ps:
                c_ = 'pos' if r['total_r'] >= 0 else 'neg'
                body.append(f"<tr><td>{r['symbol']}</td><td>{r['n']}</td><td>{r['tp']}/{r['sl']}</td><td>{r['wr']:.0f}%</td><td class='{c_}'>{r['total_r']:+.2f}</td><td class='{c_}'>${r['final']:.2f}</td><td class='{c_}'>{r['roi']:+.1f}%</td><td>{r['mdd']:.1f}%</td></tr>")
        else:
            body.append("<h3>Per Koin</h3><table><tr><th>Koin</th><th>Trade</th><th>Menang/Kalah</th><th>WR</th><th>R</th><th>Profit</th></tr>")
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
    html = f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>{refresh}<title>Backtest {NS_MODE}</title><style>{css}</style></head><body>{''.join(body)}</body></html>"
    return html.encode('utf-8')

# ============================================================
# HTTP HANDLER + ENTRY POINT
# ============================================================
class _Handler(BaseHTTPRequestHandler):
    def _send(self, body, ctype, filename=None):
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        if filename:                                                              # paksa DOWNLOAD (bukan dibuka di browser)
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path); path = u.path; view = 'view=1' in (u.query or '')
        if path == '/trades.txt':                                                  # default = download; /trades.txt?view=1 = lihat di browser
            return self._send(_trades_txt(), 'text/plain; charset=utf-8', None if view else f'trades_{NS_MODE}.txt')
        if path == '/struktur.txt':                                                 # struktur H1 (tanpa trade); ?coin=FARTCOINUSDT untuk satu koin
            cn = [q.split('=', 1)[1] for q in (u.query or '').split('&') if q.startswith('coin=')]
            return self._send(_struct_txt(cn[0] if cn else None), 'text/plain; charset=utf-8', None if view else f'struktur_h1_{NS_MODE}.txt')
        if path == '/ringkasan.txt':
            return self._send(_ringkasan_txt(), 'text/plain; charset=utf-8', None if view else f'ringkasan_{NS_MODE}.txt')
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
