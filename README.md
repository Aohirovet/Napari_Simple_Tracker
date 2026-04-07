# napari-roi-tracker

napari 上で動く ROI tracking / FRAP analysis plugin です。現在は `npe2` plugin として、`Simple_Tracker`、`Simple_FRAP_analysis`、`Load Session` の 3 entrypoint を提供しています。

## Plugin Entrypoints

- `Simple_Tracker`
  - ROI tracking
  - fluorescence intensity graph
  - CSV export
- `Simple_FRAP_analysis`
  - main ROI / reference ROI / background ROI を使った FRAP 解析
  - background correction
  - double normalization
  - full scale normalization
  - CSV export
- `Load Session`
  - 保存済み session の復元
  - plugin 上では session 保存も利用可能

## 主な機能

- 複数トラック対応
- main ROI / reference ROI / background ROI の分離
- ROI 補間
- Simple tracking
- 背景補正
- double normalization
- full scale normalization
- CSV 保存
- session 保存 / 読込
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

Plugins メニューから `Napari ROI Tracker` を開き、以下の widget を使います。

- `Simple_Tracker`
- `Simple_FRAP_analysis`
- `Load Session`

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
