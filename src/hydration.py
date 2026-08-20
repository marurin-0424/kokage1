"""
WBGT → 熱ストレス積分 → 必要水分量(mL) の推定モデル

［重要］本モデルは「摂取指示」ではなく「持参量の目安」を出すためのもの。
子どもの水分補給について、環境省・日本スポーツ協会はいずれも
「のどの渇きに応じた自由飲水」を推奨している。
"""
from dataclasses import dataclass
from typing import List, Literal, Optional
import math

# ─────────────────────────────────────────────────────────────
# 定数と出典
# ─────────────────────────────────────────────────────────────

# 日陰補正
#   ［事実］[R-06] 環境省「まちなかの暑さ対策ガイドライン 令和4年度部分改訂版」p.5
#     「樹木の陰に入ると、頭上からの日射と足元からの赤外放射が大幅に減り、
#      日向にくらべ暑さ指数(WBGT)が２程度…低くなる場合があります」
#   ★［推測］原文は「樹木の陰」の実測値。こかげはこれを建物・高架の影にも当てている。
#     建物の影は遮蔽率が高い（樹冠は日射の75〜95%）一方、壁面からの再放射があり
#     蒸散もないので、ネットでは過大評価（＝日陰を良く見積もりすぎ）の可能性が高い。
#     建物影のWBGT低減値を示した公的資料は見つかっていない（data-sources.md §10-3）
DELTA_WBGT_SHADE = -2.0

# 子どもの高さ（50cm）補正
#   ［事実］[R-07] 環境省 熱中症予防情報サイト「生活の場における暑さ指数について」
#     「50cmの高さでは大人を想定した高さ150cmに比べ、暑さ指数は平均して0.1〜0.3℃
#      高くなります。風が弱く、日射が強いときには2℃程度高くなった事例もありました」
#   ★［推測］0.1〜0.3 は「平均」、2℃は「事例（最大級）」で、同じ軸の両端ではない。
#     さらに原文の条件は「風が弱く かつ 日射が強い」の AND だが、sun_frac は
#     日射しか見ていない（風速を含まない）。ΔH の f 適用は再設計の余地あり
DELTA_WBGT_CHILD_NORMAL = 0.3
DELTA_WBGT_CHILD_HARSH  = 2.0   # 日射強・風弱

# ［事実］[R-09c] 厚生労働省「生活活動のメッツ表」（国立健康・栄養研究所 改訂版メッツ表の改変版・2026年1月版）
#   ★ 2026-08-17 訂正：出典は [R-09]（国立健康・栄養研究所版）ではありません。
#     下の逐語は同版に1件も存在せず、厚労省の改変版 [R-09c] にあります（data-sources.md §10-3）。
#     値そのものは変わりません。
#   ★ 2024年に改訂第2版 [R-09b] が出ており、座位（静かに）は 1.3→1.0 に変わっている。
#     ただし厚労省ルート（身体活動・運動ガイド2023／健康日本21システム）は2012年版のまま。
#     歩行2.0・立位1.8・軽く遊ぶ2.8・遊び5.8 は変更なし
METS = {
    "walk_slow":   2.0,  # ゆっくりした歩行（平地、非常に遅い＝53m/分未満）
    "walk_normal": 3.0,  # 普通歩行（平地、67m/分）
    "stand":       1.8,  # 立位（会話、電話、読書）
    "sit":         1.3,  # 座位（静かに）
    "transit":     1.3,  # バス・電車の座位
    # ★子ども本人の活動。移動中と遊んでいる時では強度が全く違う
    "play_active": 5.8,  # こどもと遊ぶ（歩く/走る、活発に）
    "play_light":  2.8,  # こども・動物と遊ぶ（立位、軽度）
    # ★ 2026-08-17 追加。[R-09c] 厚労省「生活活動のメッツ表」3メッツ未満の欄
    #   「子どもと遊ぶ（座位、軽度）2.2」。それまで「座って遊ぶ」に sit=1.3
    #   （＝座位・静かに＝何もしていない座位）を当てていた（mets_sweep.py）
    "play_sit":    2.2,  # 子どもと遊ぶ（座位、軽度）
}

# 区分と行動指針
#   ［事実］[R-01] 日本スポーツ協会「熱中症予防運動指針」第6版 p.15（＝運動指針。31が中止線）
#   ［事実］[R-02] 日本生気象学会「日常生活における熱中症予防指針 Ver.4」p.3（＝日常生活指針）
#   ★ 環境省が作った指針ではない。環境省は [R-08] p.46 表3-1 に転載しているだけ
#   ★ 区分名は2系統が混ざっている：「危険」は R-02、「ほぼ安全」は R-01 にしかない
#   休憩間隔：15分＝[R-01] p.41「暑熱環境下での運動時は15〜20分ごとに150〜250ml」
#             30分＝[R-01] p.15「激しい運動では、30分おきくらいに休憩をとる」
#   ★［推測］45分・60分は出典がない。R-01 p.15 の 21〜25「運動の合間に積極的に
#     水分・塩分を補給する」／21未満「適宜水分・塩分の補給は必要」には間隔の記載がなく、
#     30分から等差で埋めた仮定
WBGT_LEVELS = [
    (31.0, "危険",     "運動は原則中止。特に子どもの場合には中止すべき", None),
    (28.0, "厳重警戒", "激しい運動は中止。10〜20分おきに休憩と水分・塩分補給", 15),
    (25.0, "警戒",     "積極的に休憩。30分おきくらいに休憩", 30),
    (21.0, "注意",     "運動の合間に積極的に水分・塩分補給", 45),   # ［推測］出典なし
    (0.0,  "ほぼ安全", "適宜水分・塩分の補給は必要", 60),            # ［推測］出典なし
]

# 屋内の実効WBGT（定数）★ 2026-08-13：屋外WBGT−5.0 から変更
#   ［事実］[R-20] 建築物環境衛生管理基準／事務所衛生基準規則 第5条：
#     温度 18〜28℃・相対湿度 40〜70%。室内・日射なしなら WBGT = 0.7×湿球 + 0.3×黒球
#     （黒球≒気温）なので、包絡線の最悪端 28℃/70% が WBGT 25.0℃。
#     ＝ 空調が効いている屋内のWBGTは原理的にこれを超えない
#   ★ 上端を採っている。実運用（26〜27℃・湿度55〜60%）なら 21.5〜22.9℃ で、
#     モデルは屋内を2〜3℃暑めに見積もる。［推測］屋内を涼しく見せる方が危険
#     （[R-02] p.12：熱中症の約4割は住宅で発生・総務省消防庁2021）なので安全側へ倒した
#   ★ 旧 base − 5.0 は、屋外31以上で 26℃超＝法定上限を超える値を出していた
#   ★ 残る穴：これは「空調が効いている」前提。空調の有無はどのオープンデータにもない
WBGT_INDOOR = 25.0

# ─── ここから下は［推測］＝丸山の仮定。公的な裏付けはない ───

# 基準発汗率の錨（アンカー）
#   ［事実］[R-03] p.9 職場における熱中症防止のためのガイドライン（基発0318第1号・令和8年3月18日）
#     暑熱下の作業で「20〜30分ごと」に「カップ1〜2杯程度」
#     ★ 旧「職場における熱中症予防対策マニュアル」[R-04] も同文言だが、
#       旧要綱は2026-03-18に廃止され R-03 に統合された
#   ［推測］カップ1杯≒180mL も、この状況を「成人60kg・METs3.0・WBGT28」と読むのも仮定
#     → 中央値 270mL / 25分 = 10.8 mL/分
SR_REF_ML_PER_MIN = 10.8
BW_REF_KG   = 60.0
METS_REF    = 3.0
WBGT_REF    = 28.0

# WBGT感度β：WBGT 1℃あたり発汗が何割増えるか
#   ［事実］[R-05] ISO 7243:2017 附属書A 表A.1（＝JIS Z 8504:2021、＝厚労省 [R-03] 表1-1 の元）
#     代謝率 115 / 180 / 300 / 415 / 520 W（体表面積1.8m²前提）に対し
#     暑熱順化者のWBGT基準値 33 / 30 / 28 / 26 / 25 ℃
#   ［推測］1 met = 58.2 W/m²（ASHRAE 55）×1.8m² = 104.8 W で MET に直すと
#     1.10 / 1.72 / 2.86 / 3.96 / 4.96 MET。5点の回帰の傾きは −1.97 ℃/MET
#     → METs_ref=3 で 1 MET 増 = +33% なので β = 0.333/1.97 ≒ 0.169
#   ★ MET の定義で答えが動く。モデルが使う [R-09] メッツ表は ACSM 定義
#     （3.5 mL O2/kg/min ≒ 85 W）で、ASHRAE 定義（104.8 W）とは25%違う。
#     対応づけを変えると β = 0.169（ASHRAE）/ 0.20（区分0を座位1.3 MET で校正）
#     / 0.29（ISO の歩行速度の例で対応づけ）と散らばる。
#   ★ 0.165 は妥当範囲 0.17〜0.29 の「下端」であり、安全側ではない。
#     β が低いほど暑い日の推定が小さく出る（WBGT31 で係数 1.495 vs β=0.29 なら 1.87）
BETA_PER_DEG = 0.165

# 体表面積スケーリング：発汗は体重ではなく体表面積に比例する
#   ［事実］[R-01] p.23「子どもの体表面積は体重比にすれば大人より広くなります」（倍率の記載はない）
#   ［推測］簡易的に BW^(2/3) で近似する
BSA_EXPONENT = 2.0 / 3.0

# 小児の汗腺未発達による補正
#   ［事実］[R-01] p.23「子どもの発汗機能は未発達で、大人より発汗量が少なく、その差は
#           多くの汗を必要とする条件ほど顕著になります」「子どもは決して『汗っかき』ではありません」
#   ［推測］したがって体表面積按分は過大評価になりうる。
#           ただし持参量は安全側に倒すべきなので、既定は 1.0（補正しない）。
K_CHILD = 1.0

# 持参量への変換：こぼす・飲み残す分
#   ［推測］完全に設計上の仮定
K_CARRY = 1.2

# 出力の幅
BAND = 0.25   # ［推測］±25%。点推定は精度を誤認させるため

# 持参量の下限
#   ［推測］計算値が小さくても、最低限は持たせる。給水スポット依存は危険
MIN_CARRY_ML = 200


@dataclass
class Segment:
    """経路の1区間"""
    label: str
    minutes: float
    mode: Literal["walk_slow", "walk_normal", "stand", "sit", "transit"]
    sunlit: bool                 # True=日向 / False=日陰
    harsh: bool = False          # 日射が強く風が弱いか（アメダスの日照・風速から判定）
    indoor: bool = False         # 屋内（冷房下）


@dataclass
class Result:
    wbgt_base: float
    level: str
    advice: str
    rest_interval_min: Optional[int]
    go_outside: bool
    heat_load: float             # 熱ストレス積分（METs·℃·分 相当の無次元量）
    intake_ml: float             # 推定摂取必要量
    carry_ml: float              # 持参量（点推定）
    carry_low: int               # 持参量の下限（50mL刻み）
    carry_high: int              # 持参量の上限（50mL刻み）
    sun_minutes: float
    shade_minutes: float
    breakdown: list


def wbgt_level(wbgt: float):
    for thr, name, advice, rest in WBGT_LEVELS:
        if wbgt >= thr:
            return name, advice, rest
    return WBGT_LEVELS[-1][1], WBGT_LEVELS[-1][2], WBGT_LEVELS[-1][3]


def effective_wbgt(base: float, seg: Segment, sun_frac: float = 1.0) -> float:
    """区間の実効WBGT（子どもの高さでの値）

    sun_frac : 直達日射の割合 0.0〜1.0（1.0＝快晴、0.0＝完全な曇天/雨）
        ［推測］曇天では影ができないので、日陰補正も子ども高さの日射補正も効かない。
        WBGT 自体は雲を織り込んでいる（黒球温度が下がる）ので base は触らず、
        「日陰であることの得」だけを sun_frac で線形に縮める。
        sun_frac=0 なら日向と日陰の差が消え、経路の日陰最適化が自動的に無効化される。
    """
    if seg.indoor:
        # ★ 2026-08-13：base − 5.0（無出典）から、ビル管法由来の定数 25.0 に変更。
        #   屋外の暑さには連動しない（空調はサーモスタットで決まるため、物理的にこちらが正しい）
        return WBGT_INDOOR
    f = min(max(sun_frac, 0.0), 1.0)
    w = base
    w += 0.0 if seg.sunlit else DELTA_WBGT_SHADE * f
    child = DELTA_WBGT_CHILD_HARSH if (seg.sunlit and seg.harsh) else DELTA_WBGT_CHILD_NORMAL
    # 子ども高さの上振れ（+2.0）は「日射が強いとき」の値なので、これも f で縮める。
    # 下限は通常時の +0.3（照り返し以外の要因が残るため）［推測］
    w += DELTA_WBGT_CHILD_NORMAL + (child - DELTA_WBGT_CHILD_NORMAL) * f
    return w


def sweat_rate(wbgt_eff: float, mets: float, bw_kg: float) -> float:
    """単位時間あたりの推定発汗率 (mL/分)

    SR = SR_ref × (METs/METs_ref) × (BW/BW_ref)^(2/3) × k_child
         × (1 + β × (WBGT_eff − WBGT_ref))
    """
    scale_body = (bw_kg / BW_REF_KG) ** BSA_EXPONENT
    scale_act  = mets / METS_REF
    scale_env  = 1.0 + BETA_PER_DEG * (wbgt_eff - WBGT_REF)
    scale_env  = max(scale_env, 0.2)   # 下限。涼しくても発汗はゼロにならない
    return SR_REF_ML_PER_MIN * scale_act * scale_body * K_CHILD * scale_env


def estimate(wbgt_base: float, segments: List[Segment], bw_kg: float,
             refill_ml: float = 0.0) -> Result:
    """
    wbgt_base : 環境省WBGT API の値（最寄り観測地点。大人1.5m・日向相当）
    segments  : 経路の区間リスト
    bw_kg     : 子どもの体重
    refill_ml : 途中の給水スポットで補給できる量
    """
    level, advice, rest = wbgt_level(wbgt_base)
    go = wbgt_base < 31.0

    intake = 0.0
    load   = 0.0
    sun = shade = 0.0
    rows = []
    for s in segments:
        w = effective_wbgt(wbgt_base, s)
        m = METS[s.mode]
        sr = sweat_rate(w, m, bw_kg)
        ml = sr * s.minutes
        intake += ml
        load   += m * max(0.0, w - 21.0) * s.minutes   # 熱ストレス積分（参考値）
        if not s.indoor:
            if s.sunlit: sun += s.minutes
            else:        shade += s.minutes
        rows.append({
            "区間": s.label, "分": s.minutes, "モード": s.mode,
            "日向": "日向" if s.sunlit and not s.indoor else ("屋内" if s.indoor else "日陰"),
            "実効WBGT": round(w, 1), "METs": m,
            "発汗率mL/分": round(sr, 2), "小計mL": round(ml, 0),
        })

    carry = max(MIN_CARRY_ML, intake * K_CARRY - refill_ml)
    lo = int(math.floor(carry * (1 - BAND) / 50.0) * 50)
    hi = int(math.ceil (carry * (1 + BAND) / 50.0) * 50)

    return Result(wbgt_base, level, advice, rest, go, load,
                  intake, carry, lo, hi, sun, shade, rows)
