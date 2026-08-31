# -*- coding: utf-8 -*-
"""屋内施設の開館時間を書き出す（2026-08-22 新設・tasks.md C47）

★ なぜ要るか
  「どこで遊びたいですか？」に「屋内」を足すと、**開いているか分からない施設を薦める**ことになる。
  こかげは「開館時間が入っていない」ことを提言の柱（roadmap ★4）にしているので、
  自分の画面でその穴を隠すわけにいかない。
  → **分かるものは時間を出し、分からないものは「データがありません」と書く。**

★ 出どころは2つ。新しいデータは取らない。すでに使っている2件から拾う。
  ・東京都福祉局「赤ちゃん・ふらっと一覧」（CC BY 4.0）… 施設利用可能日／施設利用可能時間
  ・豊島区「公共施設一覧」（CC BY 2.1 日本）      … 利用可能曜日／開始時間／終了時間

★ 実見（2026-08-22）
  屋内候補はユニーク名 66 件。**開館時間が分かるのは 29 件（44%）だけ**で、37 件は不明。
  公共施設一覧558件のうち時間が入っている28件は **24が保育園・3が幼稚園**で、
  こかげが薦める区民ひろば・図書館・子どもスキップには **1件しか無い**（北大塚すくすくルーム）。

出力: pages/b2/facility_hours.json
"""
import csv, io, json, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))   # kokage/

AF = os.path.join(ROOT, 'data', 'tokyo-fukushi', 'akachanflat_ichiran_R80617.csv')
PF = os.path.join(ROOT, 'data', 'toshima-ku', 'r5_public_facility.csv')
BUNDLE = os.path.join(ROOT, 'data', 'tokyo-3d-map', 'derived', 'out', 'kokage_graph.json')
OUT = os.path.join(ROOT, 'pages', 'b2', 'facility_hours.json')

# ★ 出典の表示に使う。「データ側の基準日」と「私たちが確認した日」を分けて持つ。
SRC = {
    'af': dict(name='東京都福祉局「赤ちゃん・ふらっと一覧」',
               ver='令和8年6月17日現在', lic='CC BY 4.0'),
    'pf': dict(name='豊島区「公共施設一覧」',
               ver='r5_public_facility.csv', lic='CC BY 2.1 日本'),
}
CHECKED = os.environ.get('KOKAGE_HOURS_CHECKED') or datetime.date.today().isoformat()


def read(path):
    raw = open(path, 'rb').read()
    for enc in ('utf-8-sig', 'cp932', 'utf-8'):
        try:
            return list(csv.reader(io.StringIO(raw.decode(enc))))
        except UnicodeDecodeError:
            continue
    raise RuntimeError('文字コードが判定できません：%s' % path)


def tidy(s):
    """改行やスペースを1行に畳む（『月～金\n土』のような値が入っている）"""
    return ' '.join(str(s).split())


def main():
    names = sorted({p['name'] for p in json.load(open(BUNDLE, encoding='utf-8'))['parks'] if p['indoor']})

    hours = {}

    # 1) 赤ちゃん・ふらっと（豊島区ぶんだけ）
    for x in read(AF)[1:]:
        if len(x) < 8 or x[1].strip() != '豊島区':
            continue
        nm, day, hr = x[2].strip(), tidy(x[6]), tidy(x[7])
        if nm in names and hr:
            hours[nm] = dict(day=day, hours=hr, src='af')

    # 2) 公共施設一覧（赤ちゃん・ふらっとに無いものだけ補う）
    for x in read(PF)[1:]:
        if len(x) < 20:
            continue
        nm = x[4].strip()
        s, e = x[17].strip(), x[18].strip()
        if nm in names and (s or e) and nm not in hours:
            hours[nm] = dict(day=tidy(x[16]), hours=('%s～%s' % (s, e)).strip('～'), src='pf')

    unknown = [n for n in names if n not in hours]
    out = dict(
        checked=CHECKED,
        sources=SRC,
        hours=hours,
        note='開館時間が分かるものだけ入れています。無い施設は「データがありません」と表示してください。',
    )
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print('屋内候補（ユニーク名） %d 件' % len(names))
    print('  開館時間が分かる  %d 件（赤ちゃん・ふらっと %d ／公共施設一覧 %d）'
          % (len(hours),
             sum(1 for v in hours.values() if v['src'] == 'af'),
             sum(1 for v in hours.values() if v['src'] == 'pf')))
    print('  分からない       %d 件（%.0f%%）' % (len(unknown), len(unknown) / len(names) * 100))
    print('  確認日 %s' % CHECKED)
    print('  -> %s（%.1f KB）' % (OUT, os.path.getsize(OUT) / 1024))
    print('\n★ 分からない施設の例：%s' % '／'.join(unknown[:8]))


if __name__ == '__main__':
    main()
