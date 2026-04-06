# napari-roi-tracker

napari 上で動く multi-track ROI FRAP 解析プラグインです。元の `ROI_track_v2.py` を、GitHub 上で保守しやすい plugin package 形式へ分解した雛形です。

## 主な機能

- 複数トラック対応
- main ROI / reference ROI / background ROI の分離
- ROI 補間
- 背景補正
- double normalization
- full scale normalization
- CSV 保存
- 完全復元セッション保存 / 読込
- napari 上での ROI mask 追従表示

## レイヤー命名ルール

- main ROI: 任意の Points layer 名
- reference ROI: `Ref_` + main ROI layer 名
- background ROI: GUI 上で明示選択

例:
- `Cell1`
- `Ref_Cell1`
- `BG`

## インストール

開発用:

```bash
cd napari-roi-tracker
pip install -e .
```

通常:

```bash
pip install .
```

## napari での起動

```bash
napari
```

Plugins メニューから `Napari ROI Tracker` の各 widget を開きます。

## 開発の進め方

```bash
git init
git add .
git commit -m "Initial napari plugin scaffold"
```

GitHub に作った空リポジトリへ接続:

```bash
git branch -M main
git remote add origin https://github.com/<your-name>/napari-roi-tracker.git
git push -u origin main
```

## ディレクトリ構成

```text
napari-roi-tracker/
├── pyproject.toml
├── README.md
├── LICENSE
└── src/
    └── napari_roi_tracker/
        ├── __init__.py
        ├── _core.py
        ├── _dock.py
        ├── _state.py
        ├── _widgets.py
        └── napari.yaml
```

## 次に入れるとよい改善

- bleach frame 自動検出
- polygon ROI 対応
- fitting curve の追加
- test 導入
- icon / sample data / CI
