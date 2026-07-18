"""
Calibration Framework Dashboard
================================
Plotly Dash ベースのインタラクティブダッシュボード。
Cursor なしでブラウザから使える。

起動方法:
    cd 09_calibration_framework/dashboard
    pip install -r requirements.txt
    python app.py
    → http://localhost:8051 を開く

タブ構成:
    1. Overview          - モデル比較・補正前後 MAE・評価サマリー
    2. Bin Explorer      - カメラ位置 × ビン構造の可視化（インタラクティブ）
    3. Linear Model      - 局所線形モデルの R² ヒートマップ・係数
    4. Grid Search       - ハイパーパラメータ探索結果
    5. Bin Reference     - ビン定義・カバレッジ
    6. Raw Data          - 生 MAE の多項式フィット
    7. Angle Timeseries  - GT / MP / 補正後の時系列（v1/v2/v3）
    8. Error · MC        - カメラマップ + フレーム×cosφ / |MC_n|
    9. MA Noise          - 歩行直交ノイズ ε の移動平均除去
"""

import json
import os
import sys
from pathlib import Path

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback_context, dcc, html
from dash.exceptions import PreventUpdate

# ── パス設定 ───────────────────────────────────────────────────────────────
DASHBOARD_DIR = Path(__file__).resolve().parent
FRAMEWORK_DIR = DASHBOARD_DIR.parent
REPO_ROOT = FRAMEWORK_DIR.parent
sys.path.insert(0, str(FRAMEWORK_DIR))

OUTPUTS = FRAMEWORK_DIR / "outputs"
BIAS_TABLES = OUTPUTS / "bias_tables"
RESULTS = OUTPUTS / "results"

# ── データ読み込み ──────────────────────────────────────────────────────────
print("Loading data...")

from src.data_loader import load_angle_mae_all_layers
from src.features import apply_all_bins

df_all = load_angle_mae_all_layers()
df_all = apply_all_bins(df_all, n_azimuth=8)

df_m2 = pd.read_csv(BIAS_TABLES / "model2_joint_bias.csv")
df_m3 = pd.read_csv(BIAS_TABLES / "model3_height_bias.csv")
df_m4 = pd.read_csv(BIAS_TABLES / "model4_viewbin_az8.csv")
beta_global = json.loads((BIAS_TABLES / "model5_linear_global.json").read_text())

df_eval = pd.read_csv(RESULTS / "evaluation_results_az8.csv")
df_gs = pd.read_csv(RESULTS / "grid_search_results.csv")
df_cov = pd.read_csv(RESULTS / "bin_coverage_az8.csv")
df_local = pd.read_csv(RESULTS / "local_linear_fits_az8.csv")

JOINTS = ["L_Shoulder", "R_Shoulder", "L_Elbow", "R_Elbow",
          "L_Hip", "R_Hip", "L_Knee", "R_Knee"]
LAYERS = ["Y=0.5", "Y=1.0", "Y=1.5", "Y=2.0"]
AZ_LABELS = ["N (0°)", "NE (45°)", "E (90°)", "SE (135°)",
             "S (180°)", "SW (225°)", "W (270°)", "NW (315°)"]
BIN_COLORS = px.colors.qualitative.Set2[:8]

# 角度時系列（scripts/batch_angle_timeseries.py の出力）
ANGLE_TS_BASE = FRAMEWORK_DIR / "scripts" / "output"
ANGLE_TS_VERSIONS = [v.name for v in sorted(ANGLE_TS_BASE.glob("v*")) if v.is_dir()]

# Error · MC（02_mediapipe_v2/run_error_mc_analysis.py の出力・案 B）
ERROR_MC_DIR = REPO_ROOT / "02_mediapipe_v2" / "error_mc_analysis" / "results"
ERROR_MC_FRAME_CSV = ERROR_MC_DIR / "error_mc_frame_joint.csv"
ERROR_MC_CAM_CSV = ERROR_MC_DIR / "error_mc_by_camera_joint.csv"
ERROR_MC_JOINTS = [
    "LEFT_SHOULDER", "RIGHT_SHOULDER",
    "LEFT_ELBOW", "RIGHT_ELBOW",
    "LEFT_WRIST", "RIGHT_WRIST",
    "LEFT_KNEE", "RIGHT_KNEE",
    "LEFT_ANKLE", "RIGHT_ANKLE",
]
_df_emc_frame = None
_df_emc_meta = None


def _load_emc_meta() -> pd.DataFrame:
    """カメラ位置メタ（軽量）。なければフレーム CSV から一意化。"""
    global _df_emc_meta
    if _df_emc_meta is not None:
        return _df_emc_meta
    if ERROR_MC_CAM_CSV.exists():
        m = pd.read_csv(ERROR_MC_CAM_CSV)
        _df_emc_meta = (
            m.groupby(
                ["folder_name", "camera_x", "camera_y", "camera_z",
                 "height_label", "azimuth_bin", "azimuth_label"],
                as_index=False,
            )
            .size()
            .drop(columns=["size"])
        )
    elif ERROR_MC_FRAME_CSV.exists():
        print("  Loading Error.MC meta from frame CSV (slow once)...")
        cols = ["folder_name", "camera_x", "camera_y", "camera_z",
                "height_label", "azimuth_bin", "azimuth_label"]
        m = pd.read_csv(ERROR_MC_FRAME_CSV, usecols=cols)
        _df_emc_meta = m.drop_duplicates("folder_name")
    else:
        _df_emc_meta = pd.DataFrame(
            columns=["folder_name", "camera_x", "camera_y", "camera_z",
                     "height_label", "azimuth_bin", "azimuth_label"]
        )
    return _df_emc_meta


def get_emc_frame() -> pd.DataFrame:
    """フレーム×関節の詳細（初回のみロード）。"""
    global _df_emc_frame
    if _df_emc_frame is not None:
        return _df_emc_frame
    if not ERROR_MC_FRAME_CSV.exists():
        _df_emc_frame = pd.DataFrame()
        return _df_emc_frame
    print(f"  Loading Error.MC frame data: {ERROR_MC_FRAME_CSV.name} ...")
    cols = [
        "folder_name", "frame_id", "joint", "height_label",
        "error_dot_mc", "cos_phi", "abs_cos_phi", "Error_norm",
        "MC_norm", "scale",
    ]
    _df_emc_frame = pd.read_csv(ERROR_MC_FRAME_CSV, usecols=cols)
    print(f"  Error.MC rows: {len(_df_emc_frame)}")
    return _df_emc_frame


df_emc_meta = _load_emc_meta()
print(f"  error_mc cameras: {len(df_emc_meta)}")

# MA Noise（02_mediapipe_v2/run_ma_noise_rejection.py）
MA_NOISE_DIR = REPO_ROOT / "02_mediapipe_v2" / "ma_noise_rejection" / "results"
MA_NOISE_FRAME_CSV = MA_NOISE_DIR / "ma_noise_frame_joint.csv"
MA_NOISE_CAM_CSV = MA_NOISE_DIR / "ma_noise_by_camera_joint.csv"
_df_ma_frame = None
_df_ma_meta = None


def _load_ma_meta() -> pd.DataFrame:
    global _df_ma_meta
    if _df_ma_meta is not None:
        return _df_ma_meta
    if MA_NOISE_CAM_CSV.exists():
        m = pd.read_csv(MA_NOISE_CAM_CSV)
        _df_ma_meta = (
            m.groupby(
                ["folder_name", "camera_x", "camera_y", "camera_z",
                 "height_label", "azimuth_bin", "azimuth_label"],
                as_index=False,
            )
            .size()
            .drop(columns=["size"])
        )
    else:
        _df_ma_meta = pd.DataFrame(
            columns=["folder_name", "camera_x", "camera_y", "camera_z",
                     "height_label", "azimuth_bin", "azimuth_label"]
        )
    return _df_ma_meta


def get_ma_frame() -> pd.DataFrame:
    global _df_ma_frame
    if _df_ma_frame is not None:
        return _df_ma_frame
    if not MA_NOISE_FRAME_CSV.exists():
        _df_ma_frame = pd.DataFrame()
        return _df_ma_frame
    print(f"  Loading MA Noise frame data: {MA_NOISE_FRAME_CSV.name} ...")
    cols = [
        "folder_name", "frame_id", "joint", "height_label",
        "eps_norm", "eps_bar_norm", "resid_norm", "threshold", "sigma",
        "keep", "E_norm",
    ]
    _df_ma_frame = pd.read_csv(MA_NOISE_FRAME_CSV, usecols=cols)
    print(f"  MA Noise rows: {len(_df_ma_frame)}")
    return _df_ma_frame


df_ma_meta = _load_ma_meta()
print(f"  ma_noise cameras: {len(df_ma_meta)}")


def list_angle_ts_cameras(version: str) -> list[str]:
    """指定バージョンのカメラフォルダ名一覧（なければフラット CSV から推定）。"""
    root = ANGLE_TS_BASE / version
    if not root.exists():
        return []
    cams = sorted(d.name for d in root.glob("CapturedFrames_*") if d.is_dir())
    if cams:
        return cams
    # v1 フラット配置フォールバック
    names = set()
    for p in root.glob("angle_timeseries_*_CapturedFrames_*.csv"):
        # angle_timeseries_<joint>_<safe>.csv → カメラ復元は困難なので folder_name 列は使わず
        # safe 名のままドロップダウンに出す
        stem = p.stem
        # angle_timeseries_L_Elbow_CapturedFrames_40_10_00
        parts = stem.split("_", 3)  # joint may contain underscore; take after joint
        # safer: strip known prefix + joint
        for j in JOINTS:
            pref = f"angle_timeseries_{j}_"
            if stem.startswith(pref):
                names.add(stem[len(pref):])
                break
    return sorted(names)


def load_angle_timeseries(camera_name: str, joint: str, version: str = "v3"):
    """一括生成済み CSV（frame, gt, mp, corr）を読む。無ければ None。"""
    safe = camera_name.replace(".", "").replace("-", "m")
    # camera_name がすでに safe 形式の場合もある
    candidates = [
        ANGLE_TS_BASE / version / camera_name / f"angle_timeseries_{joint}_{safe}.csv",
        ANGLE_TS_BASE / version / camera_name / f"angle_timeseries_{joint}_{camera_name}.csv",
        ANGLE_TS_BASE / version / f"angle_timeseries_{joint}_{safe}.csv",
        ANGLE_TS_BASE / version / f"angle_timeseries_{joint}_{camera_name}.csv",
    ]
    # カメラフォルダ内の glob フォールバック
    cam_dir = ANGLE_TS_BASE / version / camera_name
    path = next((p for p in candidates if p.exists()), None)
    if path is None and cam_dir.exists():
        matches = list(cam_dir.glob(f"angle_timeseries_{joint}_*.csv"))
        path = matches[0] if matches else None
    if path is None:
        return None
    return pd.read_csv(path)


print(f"  all_data: {len(df_all)} rows  eval: {len(df_eval)} rows  m4: {len(df_m4)} rows")
print(f"  angle_ts versions: {ANGLE_TS_VERSIONS}")

# ── アプリ初期化 ────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="Calibration Framework Dashboard",
)

# ─────────────────────────────────────────────────────────────────────────────
# Helper: カードラッパー
# ─────────────────────────────────────────────────────────────────────────────
def card(title, body, style=None):
    return dbc.Card([
        dbc.CardHeader(title, style={"fontWeight": "600", "fontSize": "0.9rem"}),
        dbc.CardBody(body, style={"padding": "0.75rem"}),
    ], style=style or {}, className="mb-3")


def stat_card(value, label, color="primary"):
    return dbc.Card([
        dbc.CardBody([
            html.H3(str(value), className=f"text-{color} mb-0", style={"fontWeight": "700"}),
            html.Small(label, className="text-muted"),
        ], className="text-center py-2")
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Tab 1: Overview
# ─────────────────────────────────────────────────────────────────────────────
def build_overview_tab():
    # データ分割カラム
    models_known = df_eval[df_eval["split"] == "known_view"].groupby("model")["improvement_pct"].mean().reset_index()
    models_unk = df_eval[df_eval["split"] == "unknown_view"].groupby("model")["improvement_pct"].mean().reset_index()
    models_known.columns = ["model", "known"]
    models_unk.columns = ["model", "unknown"]
    models_merged = models_known.merge(models_unk, on="model")
    models_merged["gen_drop"] = models_merged["known"] - models_merged["unknown"]

    fig_model_cmp = go.Figure()
    fig_model_cmp.add_bar(
        x=models_merged["model"], y=models_merged["known"].clip(upper=120),
        name="Known-view", marker_color="#2196F3"
    )
    fig_model_cmp.add_bar(
        x=models_merged["model"], y=models_merged["unknown"].clip(upper=120),
        name="Unknown-view (Y=2.0)", marker_color="#FF9800"
    )
    fig_model_cmp.update_layout(
        barmode="group", height=320, margin=dict(t=10, b=80, l=40, r=10),
        yaxis_title="Improvement Rate (%)",
        xaxis_tickangle=-20, legend=dict(orientation="h", y=-0.3),
        annotations=[dict(
            x=0.5, y=1.02, xref="paper", yref="paper",
            text="* Model 2/5 は unsigned MAE 使用のため 100% 超 = 過補正",
            showarrow=False, font=dict(size=10, color="gray"), xanchor="center"
        )]
    )

    # per-layer MAE
    layer_raw = df_all.groupby("height_label")[JOINTS].mean().mean(axis=1).reset_index()
    layer_raw.columns = ["layer", "raw_mae"]
    layer_raw["order"] = layer_raw["layer"].map({"Y=0.5": 0, "Y=1.0": 1, "Y=1.5": 2, "Y=2.0": 3})
    layer_raw = layer_raw.sort_values("order")

    # Model 4 補正後 MAE (test split の evaluation data より proxy)
    m4_known = df_eval[(df_eval["model"] == "Model4_ViewBin") & (df_eval["split"] == "known_view")]
    m4_avg_imp = m4_known["improvement_pct"].mean() / 100

    layer_raw["m4_est"] = layer_raw["raw_mae"] * (1 - m4_avg_imp)

    fig_layer = go.Figure()
    fig_layer.add_bar(x=layer_raw["layer"], y=layer_raw["raw_mae"],
                      name="Raw MAE (°)", marker_color="#EF5350")
    fig_layer.add_bar(x=layer_raw["layer"], y=layer_raw["m4_est"],
                      name="Model 4 (est.)", marker_color="#66BB6A")
    fig_layer.update_layout(
        barmode="group", height=280, margin=dict(t=10, b=40, l=40, r=10),
        yaxis_title="Joint Angle MAE (°)", xaxis_title="Camera Height Layer",
        legend=dict(orientation="h", y=-0.25)
    )

    # Model 4 per-joint improvement table
    m4_j = df_eval[df_eval["model"] == "Model4_ViewBin"].copy()
    m4_pivot = m4_j.pivot_table(values="improvement_pct", index="joint", columns="split").reset_index()
    m4_pivot.columns = ["joint", "known_view", "unknown_view"]
    m4_pivot["gen_drop"] = (m4_pivot["known_view"] - m4_pivot["unknown_view"]).round(2)
    m4_pivot = m4_pivot.round(2)

    tbl_rows = [
        html.Tr([html.Td(r["joint"]), html.Td(f'{r["known_view"]:.1f}%'),
                 html.Td(f'{r["unknown_view"]:.1f}%'),
                 html.Td(f'{r["gen_drop"]:+.2f} pp',
                         style={"color": "#E53935" if r["gen_drop"] > 1 else "#43A047"})
                 ])
        for _, r in m4_pivot.iterrows()
    ]

    return dbc.Container([
        dbc.Row([
            dbc.Col(stat_card("576", "Total samples"), width=3),
            dbc.Col(stat_card("4 layers", "Y = 0.5–2.0 m"), width=3),
            dbc.Col(stat_card("8 joints", "L/R Shoulder, Elbow, Hip, Knee"), width=3),
            dbc.Col(stat_card("0.718", "Local linear R² mean", "success"), width=3),
        ], className="mb-3"),

        dbc.Alert(
            "Model 2/5 は unsigned MAE を bias として使用しているため改善率 100% 超は過補正。"
            "Model 3/4 の値が実際の効果を示します。"
            " → detailed_results.csv (符号付き誤差) 生成後に再実行で解消。",
            color="warning", dismissable=True, className="mb-3"
        ),

        dbc.Row([
            dbc.Col(card("全モデル比較 — 平均改善率 (8関節平均, clip at 120%)",
                         dcc.Graph(figure=fig_model_cmp, config={"displayModeBar": False})),
                    width=7),
            dbc.Col(card("Per-layer MAE: Raw vs Model 4",
                         dcc.Graph(figure=fig_layer, config={"displayModeBar": False})),
                    width=5),
        ]),

        dbc.Row([
            dbc.Col(card("Model 4 — Per-joint Improvement Rate (%)",
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th("Joint"), html.Th("Known-view"), html.Th("Unknown-view (Y=2.0)"), html.Th("Gen. Drop")
                    ])),
                    html.Tbody(tbl_rows)
                ], striped=True, hover=True, size="sm", responsive=True)
            ), width=6),
            dbc.Col(card("Grid Search Top-5 Configuration",
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th(c) for c in ["n_az", "n_dist", "min_s", "e_calib", "e_val", "gap", "n_bins", "score"]
                    ])),
                    html.Tbody([
                        html.Tr([
                            html.Td(str(r["n_azimuth"])), html.Td(str(r["n_distance"])),
                            html.Td(str(r["min_samples"])), html.Td(f'{r["e_calib"]:.2f}'),
                            html.Td(f'{r["e_val"]:.2f}'), html.Td(f'{r["gen_gap"]:.3f}'),
                            html.Td(str(r["n_bins"])),
                            html.Td(f'{r["score"]:.2f}',
                                    style={"fontWeight": "700",
                                           "color": "#1565C0" if i == 0 else "inherit"}),
                        ], style={"background": "#E3F2FD" if i == 0 else "inherit"})
                        for i, (_, r) in enumerate(df_gs.head(5).iterrows())
                    ])
                ], striped=True, hover=True, size="sm", responsive=True)
            ), width=6),
        ]),
    ], fluid=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 2: Bin Explorer
# ─────────────────────────────────────────────────────────────────────────────
def build_bin_explorer_tab():
    return dbc.Container([
        dbc.Row([
            # コントロール列
            dbc.Col([
                card("フィルタ", [
                    dbc.Label("カメラ高さ層", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="be-layer",
                        options=[{"label": l, "value": l} for l in LAYERS],
                        value="Y=0.5", clearable=False, className="mb-3"
                    ),
                    dbc.Label("方位角ビン (0=N, 時計回り)", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="be-azbin",
                        options=[{"label": f"Bin {i}: {AZ_LABELS[i]}", "value": i} for i in range(8)],
                        value=0, clearable=False, className="mb-3"
                    ),
                    dbc.Label("表示関節", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="be-joint",
                        options=[{"label": j, "value": j} for j in JOINTS],
                        value="L_Shoulder", clearable=False, className="mb-3"
                    ),
                ]),
                card("選択ビンの統計", html.Div(id="be-bin-stats")),
            ], width=3),

            # メインビジュアル列
            dbc.Col([
                dbc.Row([
                    dbc.Col(card("カメラ位置マップ (XZ平面) — 色: 方位角ビン",
                                 dcc.Graph(id="be-camera-map",
                                           style={"height": "420px"},
                                           config={"displayModeBar": False})),
                            width=6),
                    dbc.Col(card("ビン別バイアス — 選択層 × 全方位角 (選択関節)",
                                 dcc.Graph(id="be-az-bias-bar",
                                           style={"height": "420px"},
                                           config={"displayModeBar": False})),
                            width=6),
                ]),
                dbc.Row([
                    dbc.Col(card("Joint × Azimuth バイアスヒートマップ (選択高さ層)",
                                 dcc.Graph(id="be-heatmap",
                                           style={"height": "380px"},
                                           config={"displayModeBar": True})),
                            width=6),
                    dbc.Col(card("選択ビン: 高さ層別バイアス推移 (全関節)",
                                 dcc.Graph(id="be-height-trend",
                                           style={"height": "380px"},
                                           config={"displayModeBar": False})),
                            width=6),
                ]),
            ], width=9),
        ]),
    ], fluid=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 3: Linear Model
# ─────────────────────────────────────────────────────────────────────────────

_LINEAR_THEORY_CARD = dbc.Accordion([
    dbc.AccordionItem(
        title="📐 局所線形性とは？ — 仮説・評価手順・チャートの読み方",
        children=[
            dbc.Row([
                # 仮説
                dbc.Col([
                    html.H6("① 仮説", className="fw-bold text-primary"),
                    html.P(
                        "各視点ビン内では、MediaPipe の推定誤差 e = x_mp − x_gt が、"
                        "カメラパラメータ（高さ Y・距離 D・方位角 φ）の線形関数で近似できる。",
                        className="small mb-1",
                    ),
                    dbc.Badge("e ≈ β₀ + β₁Y + β₂D + β₃sin φ + β₄cos φ + β₅ε",
                              color="secondary", className="font-monospace mb-2"),
                    html.P(
                        "これを「局所線形性仮説」と呼ぶ。"
                        "全視点を一括でモデル化（グローバルモデル）すると非線形な誤差構造を捉えきれないが、"
                        "ビンに分割することで各領域を線形に近似できる、という前提に基づく。",
                        className="small text-muted",
                    ),
                ], width=4),
                # 評価手順
                dbc.Col([
                    html.H6("② 評価の手順（実装との対応）", className="fw-bold text-success"),
                    html.Ol([
                        html.Li([html.Strong("データをビンに分割"), " — 方位角ビン × 高さビンで視点空間を離散化"],
                                className="small mb-1"),
                        html.Li([html.Strong("OLS 回帰（per bin × per joint）"), " — ",
                                 html.Code("phase_a/linear_estimator.py: fit_local_linear_models()"),
                                 " で β 係数を推定"],
                                className="small mb-1"),
                        html.Li([html.Strong("R² 算出"), " — 残差平方和 / 全変動から決定係数を計算。",
                                 "R² → 1 ならビン内で線形近似が成立"],
                                className="small mb-1"),
                        html.Li([html.Strong("局所 vs グローバル比較"), " — 同じビンのデータを全視点一括モデルで予測した場合と比較し、"
                                 "局所モデルの優位性を検証"],
                                className="small mb-1"),
                    ]),
                ], width=4),
                # チャートの読み方
                dbc.Col([
                    html.H6("③ 各チャートの見方", className="fw-bold text-warning"),
                    dbc.Table([
                        html.Tbody([
                            html.Tr([
                                html.Td(html.Strong("R² 棒グラフ"), className="small"),
                                html.Td("全ビン平均の R²（エラーバー=min/max）。"
                                        "関節ごとに線形近似の難易度が異なることを示す。", className="small"),
                            ]),
                            html.Tr([
                                html.Td(html.Strong("R² ヒートマップ"), className="small"),
                                html.Td("height × azimuth ビンでの R² 分布。"
                                        "赤いセルは線形近似が不十分なビン（サンプル不足 or 非線形領域）。", className="small"),
                            ]),
                            html.Tr([
                                html.Td(html.Strong("グローバル β"), className="small"),
                                html.Td("全視点一括で推定した係数。正 = その視点変化で誤差が増加。"
                                        "局所モデルでは各ビンごとに異なる β を持つ。", className="small"),
                            ]),
                            html.Tr([
                                html.Td(html.Strong("局所 vs グローバル散布図"), className="small"),
                                html.Td("X 軸=ビン内サンプル数、Y 軸=局所 R²。"
                                        "R² > グローバル基準線 → 局所モデルが有効。"
                                        "サンプル数が少ないビンは R² が不安定（要注意）。", className="small"),
                            ]),
                        ])
                    ], bordered=True, size="sm"),
                ], width=4),
            ]),
        ],
    )
], start_collapsed=True, className="mb-3")


def build_linear_tab():
    return dbc.Container([
        dbc.Row(dbc.Col(_LINEAR_THEORY_CARD)),
        dbc.Row([
            dbc.Col([
                card("表示関節を選択", [
                    dcc.Dropdown(
                        id="lm-joint",
                        options=[{"label": j, "value": j} for j in JOINTS],
                        value="L_Shoulder", clearable=False
                    )
                ])
            ], width=3),
            dbc.Col([
                card("R² 全関節 × ビン統計  ─  局所線形モデルのフィット品質（全ビン平均 ± min/max）",
                     dcc.Graph(id="lm-r2-bar", style={"height": "280px"},
                               config={"displayModeBar": False}))
            ], width=9),
        ]),
        dbc.Row([
            dbc.Col(card(
                "局所線形 R² ヒートマップ  ─  height_bin × azimuth_bin ごとのフィット品質"
                "（緑=線形近似有効、赤=不十分）",
                dcc.Graph(id="lm-r2-heatmap", style={"height": "360px"},
                          config={"displayModeBar": True})),
                    width=6),
            dbc.Col(card(
                "Model 5 グローバル β 係数  ─  全視点一括回帰の係数（正=誤差増加方向）",
                dcc.Graph(id="lm-beta-bar", style={"height": "360px"},
                          config={"displayModeBar": False})),
                    width=6),
        ]),
        dbc.Row([
            dbc.Col(card(
                "局所 vs グローバル R² 比較  ─  各ビンの局所 R²（X=サンプル数）。"
                "点が基準線より上 → 局所モデルが有効",
                dcc.Graph(id="lm-local-scatter", style={"height": "340px"},
                          config={"displayModeBar": True})),
                    width=12),
        ]),
    ], fluid=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 4: Grid Search
# ─────────────────────────────────────────────────────────────────────────────
def build_gridsearch_tab():
    return dbc.Container([
        dbc.Row([
            dbc.Col(card("スコア分布 (n_azimuth 別・円サイズ = n_bins)",
                         dcc.Graph(id="gs-scatter", style={"height": "400px"},
                                   config={"displayModeBar": True})),
                    width=7),
            dbc.Col(card("e_val vs gen_gap (n_azimuth 別)",
                         dcc.Graph(id="gs-gap-scatter", style={"height": "400px"},
                                   config={"displayModeBar": True})),
                    width=5),
        ]),
        dbc.Row([
            dbc.Col(card("全設定テーブル (クリックでソート)",
                dbc.Table([
                    html.Thead(html.Tr([html.Th(c) for c in
                        ["n_az", "n_dist", "min_s", "reg", "e_calib", "e_val",
                         "gen_gap", "n_bins", "n_small", "score"]])),
                    html.Tbody([
                        html.Tr([
                            html.Td(str(r["n_azimuth"])), html.Td(str(r["n_distance"])),
                            html.Td(str(r["min_samples"])), html.Td(f'{r["regularize"]:.1f}'),
                            html.Td(f'{r["e_calib"]:.3f}'), html.Td(f'{r["e_val"]:.3f}'),
                            html.Td(f'{r["gen_gap"]:.3f}'), html.Td(str(r["n_bins"])),
                            html.Td(str(r["n_small_bins"])),
                            html.Td(f'{r["score"]:.3f}',
                                    style={"fontWeight": "700",
                                           "color": "#1565C0" if r["score"] == df_gs["score"].min() else "inherit"}),
                        ])
                        for _, r in df_gs.iterrows()
                    ])
                ], striped=True, hover=True, size="sm", responsive=True)
            ), width=12),
        ]),
    ], fluid=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 5: Bin Reference
# ─────────────────────────────────────────────────────────────────────────────
def build_bin_reference_tab():
    """全ビン種別の詳細一覧タブ"""

    # ── 方位角ビン詳細 ──
    az_rows = []
    for i in range(8):
        center = i * 45
        lo = center - 22.5 if center > 0 else 337.5
        hi = center + 22.5
        # df_m4 から全層・全関節の平均バイアス
        sub = df_m4[df_m4["azimuth_bin"] == i]
        avg_bias = sub["bias_mean"].mean() if len(sub) else float("nan")
        avg_w    = sub["reliability_weight"].mean() if len(sub) else float("nan")
        n_total  = int(sub["n"].sum()) if len(sub) else 0
        az_rows.append(html.Tr([
            html.Td(html.Span(f"Bin {i}", style={"background": BIN_COLORS[i],
                                                   "color": "#fff", "padding": "2px 8px",
                                                   "borderRadius": "4px", "fontWeight": "600"})),
            html.Td(AZ_LABELS[i]),
            html.Td(f"{center}°"),
            html.Td(f"{lo:.1f}° – {hi:.1f}°"),
            html.Td(f"{avg_bias:.1f}°" if not np.isnan(avg_bias) else "—"),
            html.Td(f"{avg_w:.3f}" if not np.isnan(avg_w) else "—"),
            html.Td(str(n_total)),
        ]))

    # ── 高さビン詳細 ──
    h_rows = []
    for i, layer in enumerate(LAYERS):
        sub_h = df_m4[df_m4["height_label"] == layer]
        sub_raw = df_all[df_all["height_label"] == layer]
        avg_bias = sub_h["bias_mean"].mean() if len(sub_h) else float("nan")
        avg_raw  = sub_raw[JOINTS].values.mean() if len(sub_raw) else float("nan")
        n_cam    = len(sub_raw) if len(sub_raw) else 0
        h_rows.append(html.Tr([
            html.Td(html.Strong(f"Bin {i}")),
            html.Td(layer),
            html.Td(f"{float(layer.split('=')[1]):.1f} m"),
            html.Td(f"{avg_raw:.2f}°" if not np.isnan(avg_raw) else "—"),
            html.Td(f"{avg_bias:.2f}°" if not np.isnan(avg_bias) else "—"),
            html.Td(str(n_cam)),
        ]))

    # ── ビンごとのカバレッジ詳細テーブル ──
    cov_rows = []
    for _, r in df_cov.iterrows():
        layer = LAYERS[int(r["height_bin"])] if int(r["height_bin"]) < len(LAYERS) else str(r["height_bin"])
        cov_rows.append(html.Tr([
            html.Td(f"h{int(r['height_bin'])}_az{int(r['azimuth_bin'])}"),
            html.Td(layer),
            html.Td(AZ_LABELS[int(r["azimuth_bin"])]),
            html.Td(str(int(r["n_calib"]))),
            html.Td(str(int(r["n_test"]))),
            html.Td(
                dbc.Badge("Covered", color="success") if r["covered_by_test"]
                else dbc.Badge("Not in test", color="secondary")
            ),
        ]))

    # ── アズムースビン可視化 (compass-style bar) ──
    az_bias_by_bin = (
        df_m4.groupby("azimuth_bin")["bias_mean"].mean().reindex(range(8)).fillna(0)
    )
    fig_az_compass = go.Figure(go.Barpolar(
        r=az_bias_by_bin.values.tolist(),
        theta=[i * 45 for i in range(8)],
        width=[45] * 8,
        marker_color=BIN_COLORS,
        hovertemplate=[
            f"<b>{AZ_LABELS[i]}</b><br>avg bias={az_bias_by_bin[i]:.1f}°<extra></extra>"
            for i in range(8)
        ],
    ))
    fig_az_compass.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, az_bias_by_bin.max() * 1.2]),
            angularaxis=dict(
                tickmode="array",
                tickvals=[i * 45 for i in range(8)],
                ticktext=[f"{AZ_LABELS[i]}<br>({i*45}°)" for i in range(8)],
                direction="clockwise",
                rotation=90,
            ),
        ),
        height=380,
        margin=dict(t=20, b=20, l=60, r=60),
        showlegend=False,
        title=dict(text="方位角ビン別 平均バイアス (全関節・全高さ層)", font=dict(size=12)),
    )

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H5("方位角ビン (Azimuth Bins)", className="text-primary mb-2"),
                html.P(
                    "カメラの水平方向を 8 等分。atan2(camera_x, camera_z) で計算した方位角を"
                    " [0°, 360°) に変換後、45° 幅で割り当て。Bin 0 = 北 (N) = 0°。",
                    className="text-muted small mb-2"
                ),
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th("Bin"), html.Th("方向"), html.Th("中心角"),
                        html.Th("範囲"), html.Th("平均バイアス"), html.Th("平均 w"), html.Th("n (calib)"),
                    ])),
                    html.Tbody(az_rows),
                ], striped=True, hover=True, size="sm", responsive=True),
            ], width=7),
            dbc.Col([
                dcc.Graph(figure=fig_az_compass, config={"displayModeBar": False}),
            ], width=5),
        ], className="mb-4"),

        dbc.Row([
            dbc.Col([
                html.H5("高さビン (Height Bins)", className="text-primary mb-2"),
                html.P(
                    "camera_y (Unity ワールド座標の Y 値) を 4 段階に分類。"
                    "Y=2.0 は Height Hold-out テストセット専用 (unknown-view 評価)。",
                    className="text-muted small mb-2"
                ),
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th("Bin"), html.Th("ラベル"), html.Th("カメラ高さ"),
                        html.Th("Raw MAE"), html.Th("Model 4 バイアス"), html.Th("n cameras"),
                    ])),
                    html.Tbody(h_rows),
                ], striped=True, hover=True, size="sm", responsive=True),
            ], width=6),
            dbc.Col([
                html.H5("距離ビン (Distance Bins)", className="text-primary mb-2"),
                html.P(
                    "distance = √(camera_x² + camera_z²)。デフォルト n_distance=1"
                    " で全距離を 1 ビンにまとめる (Grid Search 最適設定)。",
                    className="text-muted small mb-2"
                ),
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th("設定"), html.Th("内容"),
                    ])),
                    html.Tbody([
                        html.Tr([html.Td("n_distance=1 (最適)"), html.Td("全距離 3.0–8.5 m を 1 ビン")]),
                        html.Tr([html.Td("n_distance=2"), html.Td("短距離 / 長距離の 2 分割")]),
                        html.Tr([html.Td("距離範囲"), html.Td("3.0 m (最近) – 8.49 m (最遠)")]),
                        html.Tr([html.Td("Grid Search score"), html.Td("n_dist=1 の方がペナルティ低い")]),
                    ]),
                ], striped=True, size="sm", responsive=True),
                html.H5("全ビンキー (height_bin × azimuth_bin)", className="text-primary mb-2 mt-3"),
                html.P("n_azimuth=8 の場合、合計 4 × 8 = 32 ビン。", className="text-muted small mb-2"),
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th("Bin Key"), html.Th("Height"), html.Th("Azimuth"),
                        html.Th("n_calib"), html.Th("n_test"), html.Th("Coverage"),
                    ])),
                    html.Tbody(cov_rows),
                ], striped=True, hover=True, size="sm", responsive=True,
                   style={"maxHeight": "300px", "overflowY": "auto", "display": "block"}),
            ], width=6),
        ]),
    ], fluid=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 6: Raw Data (生データ・線形性チェック)
# ─────────────────────────────────────────────────────────────────────────────
def build_raw_data_tab():
    """補正なし生データを特徴量別にプロットして線形性を視覚確認するタブ。"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Alert([
                    html.Strong("中央分割フィット: "),
                    "補正なし生 MAE を各特徴量に対してプロット。x 軸の中央値で左右に分割し、"
                    "それぞれに 2次（二次曲線）・4次（四次曲線）を独立フィット。"
                    "凡例の R² を比べることで左右の非対称性や曲線次数の適合度を確認できます。"
                    "  🟠 左-2次  🔴 左-4次  🔵 右-2次  🟢 右-4次",
                ], color="info", className="mb-3 py-2"),
            ], width=12),
        ]),
        dbc.Row([
            dbc.Col(card("表示関節", [
                dcc.Dropdown(
                    id="rd-joint",
                    options=[{"label": j, "value": j} for j in JOINTS],
                    value="L_Shoulder", clearable=False,
                ),
            ]), width=3),
            dbc.Col(card("表示高さ層（複数選択可）", [
                dcc.Dropdown(
                    id="rd-layers",
                    options=[{"label": l, "value": l} for l in LAYERS],
                    value=LAYERS,
                    multi=True, clearable=False,
                ),
            ]), width=5),
            dbc.Col(card("サンプリング", [
                dcc.RadioItems(
                    id="rd-sample",
                    options=[
                        {"label": "全データ", "value": "all"},
                        {"label": "ランダム 50%", "value": "half"},
                        {"label": "ランダム 25%", "value": "quarter"},
                    ],
                    value="all",
                    labelStyle={"marginRight": "12px"},
                    inputStyle={"marginRight": "4px"},
                ),
            ]), width=4),
        ]),
        dbc.Row([
            dbc.Col(card(
                "生 MAE vs 方位角 (azimuth_deg)  ─  中央分割 × 2次・4次フィット",
                dcc.Graph(id="rd-az", style={"height": "360px"},
                          config={"displayModeBar": True}),
            ), width=6),
            dbc.Col(card(
                "生 MAE vs 水平距離 (distance)  ─  中央分割 × 2次・4次フィット",
                dcc.Graph(id="rd-dist", style={"height": "360px"},
                          config={"displayModeBar": True}),
            ), width=6),
        ]),
        dbc.Row([
            dbc.Col(card(
                "生 MAE vs カメラ高さ (camera_y)  ─  中央分割 × 2次・4次フィット",
                dcc.Graph(id="rd-height", style={"height": "360px"},
                          config={"displayModeBar": True}),
            ), width=6),
            dbc.Col(card(
                "生 MAE vs 仰角 (elevation_deg)  ─  中央分割 × 2次・4次フィット",
                dcc.Graph(id="rd-elev", style={"height": "360px"},
                          config={"displayModeBar": True}),
            ), width=6),
        ]),
        dbc.Row([
            dbc.Col(card(
                "生 MAE vs sin(方位角)  ─  中央分割 × 2次・4次フィット",
                dcc.Graph(id="rd-sinaz", style={"height": "360px"},
                          config={"displayModeBar": True}),
            ), width=6),
            dbc.Col(card(
                "生 MAE vs cos(方位角)  ─  中央分割 × 2次・4次フィット",
                dcc.Graph(id="rd-cosaz", style={"height": "360px"},
                          config={"displayModeBar": True}),
            ), width=6),
        ]),
    ], fluid=True)


def _poly_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    return float(1 - ss_res / (ss_tot + 1e-12))


# 左右それぞれの色設定
_SIDE_STYLES = {
    "left": {
        2: dict(color="darkorange",   fill="rgba(255,140,0,0.09)",  dash="dash"),
        4: dict(color="tomato",       fill="rgba(255,80,60,0.09)",  dash="dot"),
    },
    "right": {
        2: dict(color="steelblue",    fill="rgba(70,130,180,0.09)", dash="dash"),
        4: dict(color="mediumseagreen", fill="rgba(60,179,113,0.09)", dash="dot"),
    },
}
_SIDE_LABEL = {"left": "左半", "right": "右半"}


def _add_split_poly_fit(fig: go.Figure, x_v: np.ndarray, y_v: np.ndarray,
                        x_line: np.ndarray, degree: int, side: str) -> None:
    """左または右半分のデータに多項式フィット線 + 95% 信頼帯を追加するヘルパー。"""
    if len(x_v) <= degree + 1:
        return

    style = _SIDE_STYLES[side][degree]
    coeffs = np.polyfit(x_v, y_v, degree)
    y_fit = np.polyval(coeffs, x_line)
    y_pred_data = np.polyval(coeffs, x_v)
    residuals = y_v - y_pred_data
    r2 = _poly_r2(y_v, y_pred_data)

    se = residuals.std(ddof=min(degree + 1, len(x_v) - 1))
    ci = np.full_like(x_line, 1.96 * se)

    # 95% 信頼帯
    fig.add_trace(go.Scatter(
        x=np.concatenate([x_line, x_line[::-1]]),
        y=np.concatenate([y_fit + ci, (y_fit - ci)[::-1]]),
        fill="toself", fillcolor=style["fill"],
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))

    side_jp = _SIDE_LABEL[side]
    label = f"{side_jp} {degree}次  R²={r2:.3f}"
    fig.add_trace(go.Scatter(
        x=x_line, y=y_fit,
        mode="lines",
        name=label,
        line=dict(color=style["color"], width=2.2, dash=style["dash"]),
        hovertemplate=(
            f"<b>{label}</b><br>x: %{{x:.2f}}<br>predicted: %{{y:.2f}}°<extra></extra>"
        ),
    ))


def _make_raw_scatter(sub: pd.DataFrame, x_col: str, joint: str,
                      x_label: str) -> go.Figure:
    """生データ散布図 + 中央分割 × 2次・4次多項式フィットを生成するヘルパー。"""
    layer_colors = {
        "Y=0.5": "#636EFA", "Y=1.0": "#EF553B",
        "Y=1.5": "#00CC96", "Y=2.0": "#AB63FA",
    }

    fig = go.Figure()

    # 高さ層別に散布点をプロット
    for layer in LAYERS:
        grp = sub[sub["height_label"] == layer]
        if grp.empty:
            continue
        fig.add_trace(go.Scatter(
            x=grp[x_col], y=grp[joint],
            mode="markers",
            name=layer,
            marker=dict(
                color=layer_colors.get(layer, "#888"),
                size=7, opacity=0.55,
                line=dict(width=0.5, color="white"),
            ),
            hovertemplate=(
                f"<b>{layer}</b><br>"
                f"{x_label}: %{{x:.2f}}<br>"
                f"MAE ({joint}): %{{y:.2f}}°<extra></extra>"
            ),
        ))

    # 全データを取得し中央で左右分割
    x_vals = sub[x_col].to_numpy(dtype=float)
    y_vals = sub[joint].to_numpy(dtype=float)
    valid = np.isfinite(x_vals) & np.isfinite(y_vals)
    x_v, y_v = x_vals[valid], y_vals[valid]

    if len(x_v) < 10:
        fig.update_layout(
            xaxis_title=x_label,
            yaxis_title=f"角度 MAE ({joint}) [°]",
            plot_bgcolor="white",
            margin=dict(t=10, b=40, l=50, r=10),
        )
        return fig

    x_mid = (x_v.min() + x_v.max()) / 2.0

    left_mask  = x_v <  x_mid
    right_mask = x_v >= x_mid
    x_left,  y_left  = x_v[left_mask],  y_v[left_mask]
    x_right, y_right = x_v[right_mask], y_v[right_mask]

    # 左右それぞれのフィット用 x 軸
    x_line_left  = np.linspace(x_v.min(), x_mid,        150)
    x_line_right = np.linspace(x_mid,     x_v.max(),    150)

    for degree in (2, 4):
        _add_split_poly_fit(fig, x_left,  y_left,  x_line_left,  degree, "left")
        _add_split_poly_fit(fig, x_right, y_right, x_line_right, degree, "right")

    # 分割位置に垂直破線を追加
    fig.add_vline(
        x=x_mid, line_dash="dot", line_color="gray", line_width=1.5,
        annotation_text=f"中央 {x_mid:.1f}",
        annotation_position="top right",
        annotation_font=dict(size=10, color="gray"),
    )

    fig.update_layout(
        xaxis_title=x_label,
        yaxis_title=f"角度 MAE ({joint}) [°]",
        plot_bgcolor="white",
        margin=dict(t=10, b=50, l=50, r=10),
        legend=dict(orientation="h", y=-0.38, font=dict(size=11)),
        hovermode="closest",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#eee")
    fig.update_yaxes(showgrid=True, gridcolor="#eee", rangemode="tozero")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Tab 7: Angle Timeseries (GT / MP / 補正後)
# ─────────────────────────────────────────────────────────────────────────────
def build_angle_ts_tab():
    default_ver = "v3" if "v3" in ANGLE_TS_VERSIONS else (
        ANGLE_TS_VERSIONS[-1] if ANGLE_TS_VERSIONS else "v3"
    )
    cams = list_angle_ts_cameras(default_ver)
    default_cam = "CapturedFrames_0.0_1.0_3.0"
    if default_cam not in cams and cams:
        default_cam = cams[0]

    return dbc.Container([
        dbc.Row([
            dbc.Col(dbc.Alert([
                html.Strong("Angle Timeseries: "),
                "マップ上のカメラをクリックして選択。"
                " 緑〜色付き = 時系列データあり / 灰色 = なし。"
                " 星マーク = 選択中。v3 は横軸 0–120 固定。",
            ], color="info", className="mb-3 py-2"), width=12),
        ]),
        dbc.Row([
            # 左: フィルタ + カメラマップ
            dbc.Col([
                card("フィルタ", [
                    dbc.Label("データセット", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="ats-version",
                        options=[{"label": v, "value": v} for v in ANGLE_TS_VERSIONS] or
                                [{"label": "v3", "value": "v3"}],
                        value=default_ver, clearable=False, className="mb-2",
                    ),
                    dbc.Label("カメラ高さ層", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="ats-layer",
                        options=[{"label": l, "value": l} for l in LAYERS],
                        value="Y=1.0", clearable=False, className="mb-2",
                    ),
                    dbc.Label("関節", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="ats-joint",
                        options=[{"label": j, "value": j} for j in JOINTS],
                        value="L_Knee", clearable=False, className="mb-2",
                    ),
                    dbc.Label("カメラ（詳細）", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="ats-camera",
                        options=[{"label": c, "value": c} for c in cams],
                        value=default_cam if cams else None,
                        clearable=False, searchable=True,
                    ),
                    html.Div(id="ats-status", className="small text-muted mt-2"),
                ]),
                card(
                    "カメラ位置マップ (XZ平面) — 色: 方位角ビン / クリックで選択",
                    [
                        dcc.Graph(
                            id="ats-camera-map",
                            style={"height": "420px"},
                            config={"displayModeBar": False},
                        ),
                        html.Div([
                            html.Span("● データあり（方位角ビン色）",
                                      style={"marginRight": "12px", "fontSize": "0.8rem"}),
                            html.Span("○ データなし",
                                      style={"marginRight": "12px", "fontSize": "0.8rem",
                                             "color": "#bbb"}),
                            html.Span("★ 選択中",
                                      style={"marginRight": "12px", "fontSize": "0.8rem",
                                             "color": "#f1c40f"}),
                            html.Span("✕ Origin",
                                      style={"fontSize": "0.8rem", "color": "#c0392b"}),
                        ], className="text-center mt-1"),
                    ],
                ),
            ], width=5),
            # 右: 時系列グラフ
            dbc.Col(card(
                "GT / MediaPipe / Corrected",
                dcc.Graph(id="ats-graph", style={"height": "680px"},
                          config={"displayModeBar": True}),
            ), width=7),
        ]),
    ], fluid=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 8: Error · MC（フレーム×内積）
# ─────────────────────────────────────────────────────────────────────────────
def build_error_mc_tab():
    meta = df_emc_meta
    has_data = not meta.empty
    default_layer = "Y=1.0"
    layer_cams = []
    if has_data:
        layer_cams = sorted(
            meta.loc[meta["height_label"] == default_layer, "folder_name"].unique()
        )
    default_cam = "CapturedFrames_3.0_1.0_0.0"
    if default_cam not in layer_cams and layer_cams:
        default_cam = layer_cams[0]

    alert = (
        "マップでカメラを選択。横軸=Frame / 縦軸=cos φ "
        "（Error·MC / (|Error||MC|)）。0 に近いほど視線と誤差が直交。"
        " 案 B（腰相対 + Y反転 + スケール）。"
        if has_data else
        "データなし。先に "
        "python 02_mediapipe_v2/run_error_mc_analysis.py を実行してください。"
    )

    return dbc.Container([
        dbc.Row([
            dbc.Col(dbc.Alert([
                html.Strong("Error · MC: "),
                alert,
            ], color="info" if has_data else "warning", className="mb-3 py-2"), width=12),
        ]),
        dbc.Row([
            dbc.Col([
                card("フィルタ", [
                    dbc.Label("カメラ高さ層", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="emc-layer",
                        options=[{"label": l, "value": l} for l in LAYERS],
                        value=default_layer, clearable=False, className="mb-2",
                    ),
                    dbc.Label("関節", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="emc-joint",
                        options=[{"label": j, "value": j} for j in ERROR_MC_JOINTS],
                        value="LEFT_KNEE", clearable=False, className="mb-2",
                    ),
                    dbc.Label("縦軸", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="emc-metric",
                        options=[
                            {"label": "cos φ（正規化内積）", "value": "cos_phi"},
                            {"label": "|cos φ|", "value": "abs_cos_phi"},
                            {"label": "Error · MC（生内積）", "value": "error_dot_mc"},
                        ],
                        value="cos_phi", clearable=False, className="mb-2",
                    ),
                    dbc.Label("カメラ（詳細）", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="emc-camera",
                        options=[{"label": c, "value": c} for c in layer_cams],
                        value=default_cam if layer_cams else None,
                        clearable=False, searchable=True,
                    ),
                    html.Div(id="emc-status", className="small text-muted mt-2"),
                ]),
                card(
                    "カメラ位置マップ (XZ平面) — 色: 方位角ビン / クリックで選択",
                    [
                        dcc.Graph(
                            id="emc-camera-map",
                            style={"height": "420px"},
                            config={"displayModeBar": False},
                        ),
                        html.Div([
                            html.Span("● Error·MC データあり",
                                      style={"marginRight": "12px", "fontSize": "0.8rem"}),
                            html.Span("○ なし",
                                      style={"marginRight": "12px", "fontSize": "0.8rem",
                                             "color": "#bbb"}),
                            html.Span("★ 選択中",
                                      style={"marginRight": "12px", "fontSize": "0.8rem",
                                             "color": "#f1c40f"}),
                            html.Span("✕ Origin",
                                      style={"fontSize": "0.8rem", "color": "#c0392b"}),
                        ], className="text-center mt-1"),
                    ],
                ),
            ], width=5),
            dbc.Col(card(
                "Frame × cos φ（左軸） / |MC_n|=|C−GT_n|（右軸・関節ごと）",
                dcc.Graph(id="emc-graph", style={"height": "680px"},
                          config={"displayModeBar": True}),
            ), width=7),
        ]),
    ], fluid=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 9: MA Noise Rejection
# ─────────────────────────────────────────────────────────────────────────────
def build_ma_noise_tab():
    meta = df_ma_meta
    has_data = not meta.empty
    default_layer = "Y=1.0"
    layer_cams = []
    if has_data:
        layer_cams = sorted(
            meta.loc[meta["height_label"] == default_layer, "folder_name"].unique()
        )
    default_cam = "CapturedFrames_3.0_1.0_0.0"
    if default_cam not in layer_cams and layer_cams:
        default_cam = layer_cams[0]

    alert = (
        "マップでカメラ選択。横軸=Frame / 縦軸=||ε||（歩行方向に直交する誤差）。"
        " 緑破線=移動平均、灰点線=Kσ閾値、赤点=排除フレーム。"
        if has_data else
        "データなし。 python 02_mediapipe_v2/run_ma_noise_rejection.py を実行してください。"
    )

    return dbc.Container([
        dbc.Row([
            dbc.Col(dbc.Alert([
                html.Strong("MA Noise: "),
                alert,
            ], color="info" if has_data else "warning", className="mb-3 py-2"), width=12),
        ]),
        dbc.Row([
            dbc.Col([
                card("フィルタ", [
                    dbc.Label("カメラ高さ層", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="ma-layer",
                        options=[{"label": l, "value": l} for l in LAYERS],
                        value=default_layer, clearable=False, className="mb-2",
                    ),
                    dbc.Label("関節", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="ma-joint",
                        options=[{"label": j, "value": j} for j in ERROR_MC_JOINTS],
                        value="LEFT_KNEE", clearable=False, className="mb-2",
                    ),
                    dbc.Label("カメラ（詳細）", style={"fontWeight": "600"}),
                    dcc.Dropdown(
                        id="ma-camera",
                        options=[{"label": c, "value": c} for c in layer_cams],
                        value=default_cam if layer_cams else None,
                        clearable=False, searchable=True,
                    ),
                    html.Div(id="ma-status", className="small text-muted mt-2"),
                ]),
                card(
                    "カメラ位置マップ (XZ平面) — クリックで選択",
                    [
                        dcc.Graph(
                            id="ma-camera-map",
                            style={"height": "420px"},
                            config={"displayModeBar": False},
                        ),
                    ],
                ),
            ], width=5),
            dbc.Col(card(
                "Frame × ||ε||  （MA + threshold + rejected）",
                dcc.Graph(id="ma-graph", style={"height": "680px"},
                          config={"displayModeBar": True}),
            ), width=7),
        ]),
    ], fluid=True)


# ─────────────────────────────────────────────────────────────────────────────
# レイアウト
# ─────────────────────────────────────────────────────────────────────────────
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H4("Calibration Framework Dashboard",
                    className="text-primary mb-0",
                    style={"fontWeight": "700"}),
            html.Small("MediaPipe Pose — Bias · Angle TS · Error·MC · MA Noise",
                       className="text-muted"),
        ], className="py-3")
    ]),

    dbc.Tabs([
        dbc.Tab(build_overview_tab(),     label="Overview",          tab_id="tab-overview"),
        dbc.Tab(build_bin_explorer_tab(), label="Bin Explorer",      tab_id="tab-bin"),
        dbc.Tab(build_linear_tab(),       label="Linear Model",      tab_id="tab-linear"),
        dbc.Tab(build_gridsearch_tab(),   label="Grid Search",       tab_id="tab-gs"),
        dbc.Tab(build_bin_reference_tab(), label="Bin Reference",    tab_id="tab-ref"),
        dbc.Tab(build_raw_data_tab(),     label="Raw Data",          tab_id="tab-raw"),
        dbc.Tab(build_angle_ts_tab(),     label="Angle Timeseries",  tab_id="tab-ats"),
        dbc.Tab(build_error_mc_tab(),     label="Error · MC",        tab_id="tab-emc"),
        dbc.Tab(build_ma_noise_tab(),     label="MA Noise",          tab_id="tab-ma"),
    ], id="main-tabs", active_tab="tab-overview"),

], fluid=True)


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks: Bin Explorer
# ─────────────────────────────────────────────────────────────────────────────


@app.callback(
    Output("be-camera-map", "figure"),
    Input("be-layer", "value"),
    Input("be-azbin", "value"),
)
def update_camera_map(layer, selected_az):
    sub = df_all[df_all["height_label"] == layer].copy()
    sub["az_label"] = sub["azimuth_bin"].apply(lambda b: AZ_LABELS[b])

    fig = go.Figure()
    for az_bin in range(8):
        grp = sub[sub["azimuth_bin"] == az_bin]
        if grp.empty:
            continue
        is_selected = (az_bin == selected_az)
        fig.add_trace(go.Scatter(
            x=grp["camera_x"], y=grp["camera_z"],
            mode="markers",
            name=f"Bin {az_bin}: {AZ_LABELS[az_bin]}",
            marker=dict(
                size=16 if is_selected else 10,
                color=BIN_COLORS[az_bin],
                symbol="star" if is_selected else "circle",
                line=dict(width=2 if is_selected else 0, color="black"),
                opacity=1.0 if is_selected else 0.55,
            ),
            text=[
                f"({r.camera_x:.1f}, {r.camera_z:.1f})<br>az={r.azimuth_deg:.1f}°<br>d={r.distance:.2f}m<br>Bin {az_bin}"
                for _, r in grp.iterrows()
            ],
            hovertemplate="%{text}<extra></extra>",
        ))

    # 原点（ボット位置）
    fig.add_trace(go.Scatter(
        x=[0], y=[0], mode="markers",
        marker=dict(size=18, color="red", symbol="x", line=dict(width=3, color="darkred")),
        name="Origin (bot)", hovertemplate="<b>Bot / Origin</b><extra></extra>",
    ))

    fig.update_layout(
        height=400, margin=dict(t=10, b=10, l=40, r=10),
        xaxis=dict(title="Camera X (m)", range=[-7, 7], dtick=1, gridcolor="#eee"),
        yaxis=dict(title="Camera Z (m)", range=[-7, 7], dtick=1, gridcolor="#eee",
                   scaleanchor="x", scaleratio=1),
        plot_bgcolor="white",
        legend=dict(orientation="h", y=-0.15, font=dict(size=10)),
        hovermode="closest",
    )
    return fig


@app.callback(
    Output("be-az-bias-bar", "figure"),
    Input("be-layer", "value"),
    Input("be-azbin", "value"),
    Input("be-joint", "value"),
)
def update_az_bias_bar(layer, selected_az, joint):
    sub = df_m4[(df_m4["height_label"] == layer) & (df_m4["joint"] == joint)].copy()
    sub = sub.sort_values("azimuth_bin")
    sub["az_label"] = sub["azimuth_bin"].apply(lambda b: AZ_LABELS[b])

    colors = [BIN_COLORS[b] for b in sub["azimuth_bin"]]
    line_colors = ["black" if b == selected_az else "rgba(0,0,0,0)" for b in sub["azimuth_bin"]]
    line_widths = [3 if b == selected_az else 0 for b in sub["azimuth_bin"]]

    fig = go.Figure()
    fig.add_bar(
        x=sub["az_label"], y=sub["bias_mean"],
        error_y=dict(type="data", array=sub["bias_std"].tolist(), visible=True, color="gray"),
        marker_color=colors,
        marker_line_color=line_colors,
        marker_line_width=line_widths,
        text=[f"w={w:.3f}<br>n={n}" for w, n in zip(sub["reliability_weight"], sub["n"])],
        hovertemplate="<b>%{x}</b><br>bias_mean=%{y:.2f}°<br>%{text}<extra></extra>",
        name="bias_mean",
    )
    fig.update_layout(
        height=380, margin=dict(t=10, b=80, l=40, r=10),
        yaxis_title="Bias Mean (°)",
        xaxis_title="Azimuth Bin",
        xaxis_tickangle=-30,
        plot_bgcolor="white",
        title_text=f"{joint} · {layer}",
        title_font=dict(size=12),
    )
    return fig


@app.callback(
    Output("be-heatmap", "figure"),
    Input("be-layer", "value"),
)
def update_heatmap(layer):
    sub = df_m4[df_m4["height_label"] == layer].copy()
    pivot = sub.pivot_table(values="bias_mean", index="joint", columns="azimuth_bin").reindex(JOINTS)
    pivot.columns = [AZ_LABELS[c] for c in pivot.columns]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=list(pivot.columns),
        y=list(pivot.index),
        colorscale="RdYlGn_r",
        text=[[f"{v:.1f}" for v in row] for row in pivot.values],
        texttemplate="%{text}°",
        textfont={"size": 10},
        colorbar=dict(title="Bias (°)", ticksuffix="°"),
        hovertemplate="<b>%{y}</b> · %{x}<br>bias_mean=%{z:.2f}°<extra></extra>",
    ))
    fig.update_layout(
        height=360, margin=dict(t=10, b=60, l=90, r=10),
        xaxis=dict(title="Azimuth Bin", tickangle=-30),
        yaxis=dict(title="Joint"),
        plot_bgcolor="white",
    )
    return fig


@app.callback(
    Output("be-height-trend", "figure"),
    Input("be-azbin", "value"),
)
def update_height_trend(az_bin):
    sub = df_m4[df_m4["azimuth_bin"] == az_bin].copy()
    fig = go.Figure()

    for j in JOINTS:
        grp = sub[sub["joint"] == j].copy()
        # LAYERS の順序で並べ直す（非連続インデックスを避け .tolist() で渡す）
        grp["_order"] = grp["height_label"].map({"Y=0.5": 0, "Y=1.0": 1, "Y=1.5": 2, "Y=2.0": 3})
        grp = grp.sort_values("_order")
        if grp.empty:
            continue
        x_vals = grp["height_label"].tolist()
        y_vals = grp["bias_mean"].tolist()
        y_err  = grp["bias_std"].tolist()
        w_vals = grp["reliability_weight"].tolist()
        fig.add_trace(go.Scatter(
            x=x_vals, y=y_vals,
            mode="lines+markers",
            name=j,
            error_y=dict(type="data", array=y_err, visible=False),
            customdata=list(zip(y_err, w_vals)),
            hovertemplate=(
                f"<b>{j}</b><br>layer=%{{x}}<br>"
                "bias=%{y:.2f}°<br>std=%{customdata[0]:.2f}°<br>w=%{customdata[1]:.3f}<extra></extra>"
            ),
        ))

    fig.update_layout(
        height=360, margin=dict(t=30, b=60, l=50, r=10),
        yaxis_title="Bias Mean (°)",
        xaxis=dict(
            title="Camera Height Layer",
            categoryorder="array",
            categoryarray=LAYERS,
            type="category",
        ),
        legend=dict(orientation="h", y=-0.3, font=dict(size=10)),
        plot_bgcolor="white",
        hovermode="x unified",
        title_text=f"Azimuth Bin {az_bin}: {AZ_LABELS[az_bin]} — 高さ別バイアス推移",
        title_font=dict(size=12),
    )
    return fig


@app.callback(
    Output("be-bin-stats", "children"),
    Input("be-layer", "value"),
    Input("be-azbin", "value"),
)
def update_bin_stats(layer, az_bin):
    sub = df_m4[(df_m4["height_label"] == layer) & (df_m4["azimuth_bin"] == az_bin)]
    cov = df_cov[(df_cov["height_bin"] == sub["height_bin"].iloc[0]) & (df_cov["azimuth_bin"] == az_bin)]
    n_calib = cov["n_calib"].values[0] if len(cov) else "N/A"
    n_test = cov["n_test"].values[0] if len(cov) else "N/A"
    covered = cov["covered_by_test"].values[0] if len(cov) else False

    rows = []
    for _, r in sub.iterrows():
        rows.append(html.Tr([
            html.Td(r["joint"], style={"fontSize": "0.8rem"}),
            html.Td(f'{r["bias_mean"]:.1f}°', style={"fontSize": "0.8rem"}),
            html.Td(f'{r["reliability_weight"]:.3f}',
                    style={"fontSize": "0.8rem",
                           "color": "#E53935" if r["reliability_weight"] < 0.07 else "#43A047"}),
        ]))

    return [
        html.P([
            html.Strong(f"Layer: {layer}  Bin: {az_bin}"),
            html.Br(),
            html.Span(f"Direction: {AZ_LABELS[az_bin]}"),
            html.Br(),
            html.Span(f"n_calib={n_calib}  n_test={n_test}"),
            html.Br(),
            dbc.Badge("Test covered" if covered else "Not in test",
                      color="success" if covered else "secondary", className="mt-1"),
        ], style={"fontSize": "0.85rem"}),
        dbc.Table([
            html.Thead(html.Tr([html.Th("Joint"), html.Th("bias"), html.Th("w")])),
            html.Tbody(rows),
        ], striped=True, hover=True, size="sm"),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks: Linear Model
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("lm-r2-bar", "figure"),
    Input("lm-joint", "value"),
)
def update_r2_bar(_):
    stats = df_local.groupby("joint")["r2"].agg(["mean", "min", "max"]).reindex(JOINTS).reset_index()
    colors = [BIN_COLORS[i % len(BIN_COLORS)] for i in range(len(stats))]

    fig = go.Figure()
    fig.add_bar(
        x=stats["joint"], y=stats["mean"],
        error_y=dict(
            type="data",
            array=(stats["max"] - stats["mean"]).tolist(),
            arrayminus=(stats["mean"] - stats["min"]).tolist(),
            visible=True, color="gray",
        ),
        marker_color=colors,
        text=[f'{v:.3f}' for v in stats["mean"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>mean R²=%{y:.3f}<extra></extra>",
        name="mean R²",
    )
    fig.add_hline(y=0.718, line_dash="dot", line_color="gray",
                  annotation_text="overall mean=0.718", annotation_position="top right",
                  annotation_font_size=10)
    fig.update_layout(
        height=260, margin=dict(t=30, b=40, l=40, r=10),
        yaxis=dict(title="R²", range=[0, 1.15]),
        xaxis_title="Joint",
        plot_bgcolor="white",
        showlegend=False,
    )
    return fig


@app.callback(
    Output("lm-r2-heatmap", "figure"),
    Input("lm-joint", "value"),
)
def update_r2_heatmap(joint):
    sub = df_local[df_local["joint"] == joint].copy()
    pivot = sub.pivot_table(values="r2", index="height_bin", columns="azimuth_bin")

    height_labels = [LAYERS[i] if i < len(LAYERS) else str(i) for i in pivot.index]
    az_labels_short = [f"Bin{c}\n{AZ_LABELS[c].split(' ')[0]}" for c in pivot.columns]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=az_labels_short,
        y=height_labels,
        colorscale="RdYlGn",
        zmin=0, zmax=1,
        text=[[f"{v:.2f}" if not np.isnan(v) else "—" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont={"size": 9},
        colorbar=dict(title="R²"),
        hovertemplate="height=%{y}<br>az=%{x}<br>R²=%{z:.3f}<extra></extra>",
    ))
    fig.update_layout(
        height=340, margin=dict(t=50, b=60, l=60, r=10),
        title=dict(
            text=(
                f"局所線形性マップ — {joint}｜緑=線形近似有効（R²→1）、赤=不十分<br>"
                "<sup>各セル = 1ビンで OLS フィットした R²。赤いビンはサンプル不足 or 非線形領域。</sup>"
            ),
            font=dict(size=11),
        ),
        xaxis=dict(title="Azimuth Bin（方位角）", tickangle=-30),
        yaxis=dict(title="Height Layer（高さ層）"),
    )
    return fig


@app.callback(
    Output("lm-beta-bar", "figure"),
    Input("lm-joint", "value"),
)
def update_beta_bar(joint):
    beta = beta_global.get(joint, [0] * 6)
    feat_labels = ["intercept", "camera_y", "distance", "sin_azimuth", "cos_azimuth", "elevation"]
    colors = ["#E53935" if b < 0 else "#43A047" for b in beta]

    fig = go.Figure()
    fig.add_bar(
        x=feat_labels, y=beta,
        marker_color=colors,
        text=[f"{b:+.3f}" for b in beta],
        textposition="outside",
        hovertemplate="<b>%{x}</b>: %{y:.4f}<extra></extra>",
    )
    fig.add_hline(y=0, line_color="gray", line_width=1)
    fig.add_annotation(
        text=(
            "グローバルモデル: e = β₀ + β₁·Y + β₂·D + β₃·sinφ + β₄·cosφ + β₅·ε<br>"
            "正 = その変数が増えると誤差が増加、負 = 誤差が減少<br>"
            "局所モデルでは各ビンごとに異なる β を持つ（→ ヒートマップで確認）"
        ),
        xref="paper", yref="paper",
        x=0.5, y=1.0,
        xanchor="center", yanchor="bottom",
        showarrow=False,
        font=dict(size=9, color="#555"),
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="#ccc",
        borderwidth=1,
    )
    fig.update_layout(
        height=340, margin=dict(t=70, b=60, l=40, r=10),
        title=dict(text=f"グローバル β係数 — {joint}  ｜e = X·β （全視点一括回帰）", font=dict(size=11)),
        yaxis_title="Coefficient value",
        plot_bgcolor="white",
        showlegend=False,
    )
    return fig


@app.callback(
    Output("lm-local-scatter", "figure"),
    Input("lm-joint", "value"),
)
def update_local_scatter(joint):
    sub = df_local[df_local["joint"] == joint].copy()
    sub["height_label"] = sub["height_bin"].apply(
        lambda b: LAYERS[b] if b < len(LAYERS) else str(b)
    )
    fig = go.Figure()
    palette = ["#E53935", "#FB8C00", "#43A047", "#1E88E5"]

    for i, layer in enumerate(LAYERS):
        grp = sub[sub["height_label"] == layer]
        if grp.empty:
            continue
        fig.add_trace(go.Scatter(
            x=grp["n"].tolist(),
            y=grp["r2"].tolist(),
            mode="markers",
            name=layer,
            marker=dict(size=9, color=palette[i % len(palette)]),
            customdata=list(zip(
                grp["azimuth_bin"].tolist(),
                grp["rmse"].tolist(),
                grp["local_mae"].tolist(),
            )),
            hovertemplate=(
                f"<b>{layer}</b><br>"
                "n=%{x}  R²=%{y:.3f}<br>"
                "az_bin=%{customdata[0]}<br>"
                "rmse=%{customdata[1]:.3f}  mae=%{customdata[2]:.3f}<extra></extra>"
            ),
        ))

    overall_mean = float(df_local[df_local["joint"] == joint]["r2"].mean())

    # 局所モデル平均 R² ライン（= 局所線形仮説の全ビン平均的な成立度）
    fig.add_hline(
        y=overall_mean, line_dash="dot", line_color="steelblue",
        annotation_text=f"局所モデル平均 R²={overall_mean:.3f}",
        annotation_font_size=10, annotation_position="top right",
        annotation_font_color="steelblue",
    )
    # 「線形近似有効」とみなす目安ライン (R²=0.7)
    fig.add_hline(
        y=0.7, line_dash="dash", line_color="#E53935", line_width=1,
        annotation_text="線形近似有効の目安 R²=0.70",
        annotation_font_size=9, annotation_position="bottom right",
        annotation_font_color="#E53935",
    )
    # 説明アノテーション
    fig.add_annotation(
        text=(
            "【読み方】各点 = 1ビン（方位角×高さ）<br>"
            "X軸 = ビン内サンプル数（少ないと R² が不安定）<br>"
            "Y軸 = 局所線形モデルの R²（仮説の成立度）<br>"
            "赤線以上 → そのビンで線形近似が有効"
        ),
        xref="paper", yref="paper",
        x=0.01, y=0.01,
        showarrow=False,
        align="left",
        font=dict(size=9, color="#555"),
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="#ccc",
        borderwidth=1,
    )
    fig.update_layout(
        height=360,
        margin=dict(t=40, b=50, l=50, r=10),
        xaxis_title="n (ビン内サンプル数)",
        yaxis=dict(title="Local R²（局所線形近似の精度）", range=[0, 1.1]),
        title=dict(
            text=(
                f"局所線形性の検証 — {joint}  "
                "（各ビンで OLS フィット → R² 算出 → 仮説の成立を確認）"
            ),
            font=dict(size=11),
        ),
        plot_bgcolor="white",
        legend=dict(title="Height Layer", orientation="h", y=-0.22),
        hovermode="closest",
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks: Grid Search
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("gs-scatter", "figure"),
    Input("main-tabs", "active_tab"),
)
def update_gs_scatter(_):
    fig = px.scatter(
        df_gs, x="n_azimuth", y="score",
        size="n_bins", color="n_distance",
        hover_data=["min_samples", "e_val", "gen_gap", "n_bins", "n_small_bins"],
        labels={"score": "Score (lower=better)", "n_azimuth": "n_azimuth",
                "n_distance": "n_distance"},
        title="Grid Search: Score by n_azimuth (circle size = n_bins)",
        height=380,
        color_continuous_scale="Viridis_r",
    )
    fig.update_layout(margin=dict(t=40, b=40, l=40, r=10), plot_bgcolor="white")
    return fig


@app.callback(
    Output("gs-gap-scatter", "figure"),
    Input("main-tabs", "active_tab"),
)
def update_gs_gap(_):
    fig = px.scatter(
        df_gs, x="e_val", y="gen_gap",
        color="n_azimuth",
        size="n_bins",
        hover_data=["min_samples", "score", "n_bins"],
        labels={"e_val": "e_val (MAE on val)", "gen_gap": "Gen. Gap",
                "n_azimuth": "n_azimuth"},
        title="e_val vs Generalization Gap",
        height=380,
        color_continuous_scale="Plasma",
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(margin=dict(t=40, b=40, l=40, r=10), plot_bgcolor="white")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks: Raw Data
# ─────────────────────────────────────────────────────────────────────────────

def _filter_raw(joint, layers, sample):
    """Raw Data タブ用フィルタ・サンプリングヘルパー。"""
    sub = df_all[df_all["height_label"].isin(layers)].copy()
    if sample == "half":
        sub = sub.sample(frac=0.5, random_state=42)
    elif sample == "quarter":
        sub = sub.sample(frac=0.25, random_state=42)
    return sub


@app.callback(
    Output("rd-az",     "figure"),
    Output("rd-dist",   "figure"),
    Output("rd-height", "figure"),
    Output("rd-elev",   "figure"),
    Output("rd-sinaz",  "figure"),
    Output("rd-cosaz",  "figure"),
    Input("rd-joint",   "value"),
    Input("rd-layers",  "value"),
    Input("rd-sample",  "value"),
)
def update_raw_plots(joint, layers, sample):
    if not layers or not joint:
        empty = go.Figure()
        return [empty] * 6

    sub = _filter_raw(joint, layers, sample)

    return (
        _make_raw_scatter(sub, "azimuth_deg",   joint, "方位角 [°]"),
        _make_raw_scatter(sub, "distance",      joint, "水平距離 [m]"),
        _make_raw_scatter(sub, "camera_y",      joint, "カメラ高さ Y [m]"),
        _make_raw_scatter(sub, "elevation_deg", joint, "仰角 [°]"),
        _make_raw_scatter(sub, "sin_azimuth",   joint, "sin(方位角)"),
        _make_raw_scatter(sub, "cos_azimuth",   joint, "cos(方位角)"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks: Angle Timeseries
# ─────────────────────────────────────────────────────────────────────────────
def _ats_layer_cameras(layer: str) -> list[str]:
    """高さ層内の全カメラ（folder_name）。"""
    return sorted(
        df_all.loc[df_all["height_label"] == layer, "folder_name"].unique()
    )


@app.callback(
    Output("ats-camera", "options"),
    Output("ats-camera", "value"),
    Input("ats-version", "value"),
    Input("ats-layer", "value"),
    State("ats-camera", "value"),
)
def update_ats_camera_list(version, layer, current):
    layer = layer or "Y=1.0"
    version = version or "v3"
    layer_cams = _ats_layer_cameras(layer)
    available = set(list_angle_ts_cameras(version))
    options = [
        {"label": (c if c in available else f"{c} (no data)"), "value": c}
        for c in layer_cams
    ]
    with_data = [c for c in layer_cams if c in available]
    if current and current in layer_cams:
        value = current
    else:
        prefer = f"CapturedFrames_0.0_{layer.replace('Y=', '')}_3.0"
        if prefer in with_data:
            value = prefer
        else:
            value = with_data[0] if with_data else (layer_cams[0] if layer_cams else None)
    return options, value


@app.callback(
    Output("ats-camera-map", "figure"),
    Input("ats-version", "value"),
    Input("ats-layer", "value"),
    Input("ats-camera", "value"),
    Input("ats-joint", "value"),
)
def update_ats_camera_map(version, layer, selected_cam, joint):
    """Bin Explorer と同系の XZ マップ。クリック選択・選択中は星。"""
    sub = df_all[df_all["height_label"] == (layer or "Y=1.0")].drop_duplicates(
        "folder_name"
    ).copy()
    available = set(list_angle_ts_cameras(version or "v3"))

    fig = go.Figure()
    for az_bin in range(8):
        grp = sub[sub["azimuth_bin"] == az_bin]
        if grp.empty:
            continue

        has_data = grp["folder_name"].isin(available)
        # データあり
        g_ok = grp[has_data]
        if not g_ok.empty:
            is_sel = g_ok["folder_name"] == selected_cam
            # 非選択
            g_other = g_ok[~is_sel]
            if not g_other.empty:
                fig.add_trace(go.Scatter(
                    x=g_other["camera_x"], y=g_other["camera_z"],
                    mode="markers",
                    name=f"Bin {az_bin}: {AZ_LABELS[az_bin]}",
                    customdata=g_other["folder_name"],
                    marker=dict(
                        size=11, color=BIN_COLORS[az_bin], symbol="circle",
                        line=dict(width=0), opacity=0.85,
                    ),
                    text=[
                        f"<b>{r.folder_name}</b><br>"
                        f"({r.camera_x:.1f}, {r.camera_z:.1f})<br>"
                        f"az={r.azimuth_deg:.1f}° · d={r.distance:.2f}m<br>"
                        f"Bin {az_bin}: {AZ_LABELS[az_bin]}"
                        for _, r in g_other.iterrows()
                    ],
                    hovertemplate="%{text}<extra></extra>",
                    showlegend=True,
                ))
            # 選択中（星）
            g_sel = g_ok[is_sel]
            if not g_sel.empty:
                fig.add_trace(go.Scatter(
                    x=g_sel["camera_x"], y=g_sel["camera_z"],
                    mode="markers",
                    name="選択中",
                    customdata=g_sel["folder_name"],
                    marker=dict(
                        size=18, color=BIN_COLORS[az_bin], symbol="star",
                        line=dict(width=2, color="black"), opacity=1.0,
                    ),
                    text=[
                        f"<b>★ {r.folder_name}</b><br>"
                        f"({r.camera_x:.1f}, {r.camera_z:.1f})<br>"
                        f"az={r.azimuth_deg:.1f}° · Bin {az_bin}"
                        for _, r in g_sel.iterrows()
                    ],
                    hovertemplate="%{text}<extra></extra>",
                    showlegend=False,
                ))

        # データなし（灰色）
        g_miss = grp[~has_data]
        if not g_miss.empty:
            fig.add_trace(go.Scatter(
                x=g_miss["camera_x"], y=g_miss["camera_z"],
                mode="markers",
                name="データなし",
                legendgroup="missing",
                customdata=g_miss["folder_name"],
                marker=dict(
                    size=9, color="#d0d0d0", symbol="circle",
                    line=dict(width=1, color="#aaa"), opacity=0.7,
                ),
                text=[
                    f"<b>{r.folder_name}</b><br>時系列データなし ({version})"
                    for _, r in g_miss.iterrows()
                ],
                hovertemplate="%{text}<extra></extra>",
                showlegend=(az_bin == 0),
            ))

    # 選択カメラが高さ層外のときも強調（稀）
    if selected_cam and selected_cam not in set(sub["folder_name"]):
        row = df_all[df_all["folder_name"] == selected_cam].head(1)
        if not row.empty:
            r = row.iloc[0]
            fig.add_trace(go.Scatter(
                x=[r.camera_x], y=[r.camera_z],
                mode="markers", name="選択中（他層）",
                customdata=[selected_cam],
                marker=dict(size=18, color="#f1c40f", symbol="star",
                            line=dict(width=2, color="black")),
                hovertemplate=f"<b>★ {selected_cam}</b> (他の高さ層)<extra></extra>",
            ))

    fig.add_trace(go.Scatter(
        x=[0], y=[0], mode="markers",
        marker=dict(size=16, color="red", symbol="x",
                    line=dict(width=3, color="darkred")),
        name="Origin (bot)",
        hovertemplate="<b>Bot / Origin</b><extra></extra>",
    ))

    # データ範囲に合わせつつ正方形
    if not sub.empty:
        pad = 1.0
        xmax = float(max(sub["camera_x"].abs().max(), sub["camera_z"].abs().max()) + pad)
        xmax = max(xmax, 7.0)
    else:
        xmax = 7.0

    fig.update_layout(
        height=400, margin=dict(t=10, b=10, l=40, r=10),
        xaxis=dict(title="Camera X (m)", range=[-xmax, xmax], dtick=1, gridcolor="#eee"),
        yaxis=dict(title="Camera Z (m)", range=[-xmax, xmax], dtick=1, gridcolor="#eee",
                   scaleanchor="x", scaleratio=1),
        plot_bgcolor="white",
        legend=dict(orientation="h", y=-0.18, font=dict(size=9)),
        hovermode="closest",
        uirevision=f"ats-map-{layer}",
        title=dict(
            text=f"{layer} · {joint or ''} · {version}",
            font=dict(size=12), x=0.01, xanchor="left",
        ),
    )
    return fig


@app.callback(
    Output("ats-camera", "value", allow_duplicate=True),
    Input("ats-camera-map", "clickData"),
    prevent_initial_call=True,
)
def ats_map_click(clickData):
    if not clickData or "points" not in clickData:
        raise PreventUpdate
    pt = clickData["points"][0]
    cam = pt.get("customdata")
    if not cam:
        raise PreventUpdate
    # customdata が list の場合あり
    if isinstance(cam, (list, tuple)):
        cam = cam[0]
    return cam


@app.callback(
    Output("ats-graph", "figure"),
    Output("ats-status", "children"),
    Input("ats-version", "value"),
    Input("ats-joint", "value"),
    Input("ats-camera", "value"),
)
def update_ats_graph(version, joint, camera):
    from plotly.subplots import make_subplots

    if not camera or not joint:
        fig = go.Figure()
        fig.update_layout(title="カメラ / 関節を選択してください")
        return fig, "未選択"

    df = load_angle_timeseries(camera, joint, version or "v3")
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"データなし: {camera} / {joint} ({version})",
            annotations=[dict(
                text="scripts/batch_angle_timeseries.py で生成してください",
                xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            )],
        )
        return fig, f"missing · {version}"

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35],
        vertical_spacing=0.07,
        subplot_titles=("関節角度 [°]", "絶対誤差 |推定 − GT| [°]"),
    )
    frames = df["frame"]
    fig.add_trace(go.Scatter(
        x=frames, y=df["gt"], mode="lines", name="Ground Truth",
        line=dict(color="#2ecc71", width=2),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=frames, y=df["mp"], mode="lines", name="MediaPipe (raw)",
        line=dict(color="#e74c3c", width=1.5),
    ), row=1, col=1)
    if "corr" in df.columns:
        fig.add_trace(go.Scatter(
            x=frames, y=df["corr"], mode="lines", name="Corrected (Model 4)",
            line=dict(color="#3498db", width=1.6, dash="dash"),
        ), row=1, col=1)

    err_mp = (df["mp"] - df["gt"]).abs()
    fig.add_trace(go.Scatter(
        x=frames, y=err_mp, mode="lines", name="|MP−GT|",
        line=dict(color="#e74c3c", width=1.2), showlegend=False,
        fill="tozeroy", fillcolor="rgba(231,76,60,0.25)",
    ), row=2, col=1)
    if "corr" in df.columns:
        err_c = (df["corr"] - df["gt"]).abs()
        fig.add_trace(go.Scatter(
            x=frames, y=err_c, mode="lines", name="|Corr−GT|",
            line=dict(color="#3498db", width=1.2), showlegend=False,
            fill="tozeroy", fillcolor="rgba(52,152,219,0.25)",
        ), row=2, col=1)

    both = df["mp"].notna() & df["gt"].notna()
    mae_raw = float((df.loc[both, "mp"] - df.loc[both, "gt"]).abs().mean()) if both.any() else float("nan")
    if "corr" in df.columns:
        both_c = df["corr"].notna() & df["gt"].notna()
        mae_corr = float((df.loc[both_c, "corr"] - df.loc[both_c, "gt"]).abs().mean()) if both_c.any() else float("nan")
    else:
        mae_corr = float("nan")

    title = f"{joint} @ {camera} [{version}]"
    if np.isfinite(mae_raw):
        title += f"  |  MAE raw: {mae_raw:.1f}°"
    if np.isfinite(mae_corr):
        title += f"  →  corr: {mae_corr:.1f}°"

    fig.update_layout(
        title=title,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=80, b=40),
        plot_bgcolor="white",
    )
    # v3 は 0–120 固定（CSV も揃っている）
    if version == "v3":
        fig.update_xaxes(range=[0, 120], row=1, col=1)
        fig.update_xaxes(range=[0, 120], title_text="Frame", row=2, col=1)
    else:
        fig.update_xaxes(title_text="Frame", row=2, col=1)
    fig.update_yaxes(rangemode="tozero", row=2, col=1)

    status = (
        f"{version} · frames {int(df['frame'].min())}–{int(df['frame'].max())} "
        f"· GT {df['gt'].notna().sum()} · MP {df['mp'].notna().sum()}"
    )
    return fig, status


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks: Error · MC
# ─────────────────────────────────────────────────────────────────────────────
def _emc_available_set() -> set:
    if df_emc_meta.empty:
        return set()
    return set(df_emc_meta["folder_name"].tolist())


@app.callback(
    Output("emc-camera", "options"),
    Output("emc-camera", "value"),
    Input("emc-layer", "value"),
    State("emc-camera", "value"),
)
def update_emc_camera_list(layer, current):
    layer = layer or "Y=1.0"
    available = _emc_available_set()
    # マップ用: df_all の当該層 + Error·MC 有無
    layer_cams = sorted(
        df_all.loc[df_all["height_label"] == layer, "folder_name"].unique()
    )
    options = [
        {"label": (c if c in available else f"{c} (no data)"), "value": c}
        for c in layer_cams
    ]
    with_data = [c for c in layer_cams if c in available]
    if current and current in layer_cams:
        value = current
    else:
        y = layer.replace("Y=", "")
        for prefer in (
            f"CapturedFrames_3.0_{y}_0.0",
            f"CapturedFrames_0.0_{y}_3.0",
        ):
            if prefer in with_data:
                value = prefer
                break
        else:
            value = with_data[0] if with_data else (layer_cams[0] if layer_cams else None)
    return options, value


@app.callback(
    Output("emc-camera-map", "figure"),
    Input("emc-layer", "value"),
    Input("emc-camera", "value"),
    Input("emc-joint", "value"),
)
def update_emc_camera_map(layer, selected_cam, joint):
    sub = df_all[df_all["height_label"] == (layer or "Y=1.0")].drop_duplicates(
        "folder_name"
    ).copy()
    available = _emc_available_set()

    fig = go.Figure()
    for az_bin in range(8):
        grp = sub[sub["azimuth_bin"] == az_bin]
        if grp.empty:
            continue
        has_data = grp["folder_name"].isin(available)
        g_ok = grp[has_data]
        if not g_ok.empty:
            is_sel = g_ok["folder_name"] == selected_cam
            g_other = g_ok[~is_sel]
            if not g_other.empty:
                fig.add_trace(go.Scatter(
                    x=g_other["camera_x"], y=g_other["camera_z"],
                    mode="markers",
                    name=f"Bin {az_bin}: {AZ_LABELS[az_bin]}",
                    customdata=g_other["folder_name"],
                    marker=dict(
                        size=11, color=BIN_COLORS[az_bin], symbol="circle",
                        opacity=0.85,
                    ),
                    text=[
                        f"<b>{r.folder_name}</b><br>"
                        f"({r.camera_x:.1f}, {r.camera_z:.1f}) · Bin {az_bin}"
                        for _, r in g_other.iterrows()
                    ],
                    hovertemplate="%{text}<extra></extra>",
                ))
            g_sel = g_ok[is_sel]
            if not g_sel.empty:
                fig.add_trace(go.Scatter(
                    x=g_sel["camera_x"], y=g_sel["camera_z"],
                    mode="markers", name="選択中",
                    customdata=g_sel["folder_name"],
                    marker=dict(
                        size=18, color=BIN_COLORS[az_bin], symbol="star",
                        line=dict(width=2, color="black"),
                    ),
                    text=[f"<b>★ {r.folder_name}</b>" for _, r in g_sel.iterrows()],
                    hovertemplate="%{text}<extra></extra>",
                    showlegend=False,
                ))
        g_miss = grp[~has_data]
        if not g_miss.empty:
            fig.add_trace(go.Scatter(
                x=g_miss["camera_x"], y=g_miss["camera_z"],
                mode="markers", name="データなし",
                legendgroup="missing",
                customdata=g_miss["folder_name"],
                marker=dict(
                    size=9, color="#d0d0d0", symbol="circle",
                    line=dict(width=1, color="#aaa"), opacity=0.7,
                ),
                text=[f"<b>{r.folder_name}</b><br>Error·MC なし"
                      for _, r in g_miss.iterrows()],
                hovertemplate="%{text}<extra></extra>",
                showlegend=(az_bin == 0),
            ))

    fig.add_trace(go.Scatter(
        x=[0], y=[0], mode="markers",
        marker=dict(size=16, color="red", symbol="x",
                    line=dict(width=3, color="darkred")),
        name="Origin (bot)",
        hovertemplate="<b>Bot / Origin</b><extra></extra>",
    ))

    xmax = 7.0
    if not sub.empty:
        xmax = float(max(sub["camera_x"].abs().max(),
                         sub["camera_z"].abs().max()) + 1.0)
        xmax = max(xmax, 7.0)

    fig.update_layout(
        height=400, margin=dict(t=30, b=10, l=40, r=10),
        xaxis=dict(title="Camera X (m)", range=[-xmax, xmax], dtick=1, gridcolor="#eee"),
        yaxis=dict(title="Camera Z (m)", range=[-xmax, xmax], dtick=1, gridcolor="#eee",
                   scaleanchor="x", scaleratio=1),
        plot_bgcolor="white",
        legend=dict(orientation="h", y=-0.18, font=dict(size=9)),
        hovermode="closest",
        uirevision=f"emc-map-{layer}",
        title=dict(text=f"{layer} · {joint or ''}", font=dict(size=12),
                   x=0.01, xanchor="left"),
    )
    return fig


@app.callback(
    Output("emc-camera", "value", allow_duplicate=True),
    Input("emc-camera-map", "clickData"),
    prevent_initial_call=True,
)
def emc_map_click(clickData):
    if not clickData or "points" not in clickData:
        raise PreventUpdate
    cam = clickData["points"][0].get("customdata")
    if not cam:
        raise PreventUpdate
    if isinstance(cam, (list, tuple)):
        cam = cam[0]
    return cam


@app.callback(
    Output("emc-graph", "figure"),
    Output("emc-status", "children"),
    Input("emc-camera", "value"),
    Input("emc-joint", "value"),
    Input("emc-metric", "value"),
)
def update_emc_graph(camera, joint, metric):
    metric = metric or "cos_phi"
    metric_labels = {
        "cos_phi": "cos φ",
        "abs_cos_phi": "|cos φ|",
        "error_dot_mc": "Error · MC（生内積）",
    }
    ylabel = metric_labels.get(metric, metric)

    if not camera or not joint:
        fig = go.Figure()
        fig.update_layout(title="カメラ / 関節を選択してください")
        return fig, "未選択"

    df = get_emc_frame()
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="Error·MC データなし",
            annotations=[dict(
                text="python 02_mediapipe_v2/run_error_mc_analysis.py",
                xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            )],
        )
        return fig, "missing data"

    sub = df[(df["folder_name"] == camera) & (df["joint"] == joint)].sort_values(
        "frame_id"
    )
    if sub.empty:
        fig = go.Figure()
        fig.update_layout(title=f"データなし: {camera} / {joint}")
        return fig, f"no rows · {camera}"

    y = sub[metric]
    mc_norm = sub["MC_norm"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sub["frame_id"], y=y,
        mode="lines+markers",
        name=ylabel,
        line=dict(color="#2980b9", width=2),
        marker=dict(size=5),
        yaxis="y",
        hovertemplate=(
            "frame=%{x}<br>"
            + f"{ylabel}=%{{y:.4f}}<br>"
            + "Error·MC=%{customdata[0]:.4f}<br>"
            + "|Error|=%{customdata[1]:.3f}<br>"
            + "|MC|=%{customdata[2]:.3f} m<extra></extra>"
        ),
        customdata=np.column_stack([
            sub["error_dot_mc"].to_numpy(),
            sub["Error_norm"].to_numpy(),
            mc_norm.to_numpy(),
        ]),
    ))
    fig.add_trace(go.Scatter(
        x=sub["frame_id"], y=mc_norm,
        mode="lines",
        name="|MC_n| = |C − GT_n|",
        line=dict(color="#e67e22", width=2, dash="dash"),
        yaxis="y2",
        hovertemplate="frame=%{x}<br>|MC_n|=%{y:.3f} m<extra></extra>",
    ))
    # cos φ = 0 → Error ⊥ MC
    fig.add_hline(y=0, line_dash="dot", line_color="#95a5a6",
                  annotation_text="cos φ = 0（直交）",
                  annotation_position="bottom right")

    mean_v = float(y.mean())
    med_v = float(y.median())
    mean_mc = float(mc_norm.mean())
    layout_yaxis = dict(
        title=dict(text=ylabel, font=dict(color="#2980b9")),
        tickfont=dict(color="#2980b9"),
        gridcolor="#eee",
        zeroline=True, zerolinecolor="#bbb",
    )
    if metric == "cos_phi":
        layout_yaxis["range"] = [-1.05, 1.05]
    elif metric == "abs_cos_phi":
        layout_yaxis["range"] = [-0.05, 1.05]

    fig.update_layout(
        title=(
            f"{joint} @ {camera}  |  mean {ylabel}={mean_v:.3f}  "
            f"median={med_v:.3f}  |  mean |MC|={mean_mc:.2f} m"
        ),
        xaxis=dict(title="Frame", gridcolor="#eee"),
        yaxis=layout_yaxis,
        yaxis2=dict(
            title=dict(text="|MC_n| [m]", font=dict(color="#e67e22")),
            tickfont=dict(color="#e67e22"),
            overlaying="y",
            side="right",
            showgrid=False,
            rangemode="tozero",
        ),
        hovermode="x unified",
        margin=dict(t=60, b=40, r=60),
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    status = (
        f"{camera} · {joint} · frames {int(sub['frame_id'].min())}–"
        f"{int(sub['frame_id'].max())} (n={len(sub)}) · "
        f"mean {ylabel}={mean_v:.3f} · mean |MC|={mean_mc:.2f} m"
    )
    return fig, status


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks: MA Noise
# ─────────────────────────────────────────────────────────────────────────────
def _ma_available_set() -> set:
    if df_ma_meta.empty:
        return set()
    return set(df_ma_meta["folder_name"].tolist())


@app.callback(
    Output("ma-camera", "options"),
    Output("ma-camera", "value"),
    Input("ma-layer", "value"),
    State("ma-camera", "value"),
)
def update_ma_camera_list(layer, current):
    layer = layer or "Y=1.0"
    available = _ma_available_set()
    layer_cams = sorted(
        df_all.loc[df_all["height_label"] == layer, "folder_name"].unique()
    )
    options = [
        {"label": (c if c in available else f"{c} (no data)"), "value": c}
        for c in layer_cams
    ]
    with_data = [c for c in layer_cams if c in available]
    if current and current in layer_cams:
        value = current
    else:
        y = layer.replace("Y=", "")
        prefer = f"CapturedFrames_3.0_{y}_0.0"
        value = prefer if prefer in with_data else (
            with_data[0] if with_data else (layer_cams[0] if layer_cams else None)
        )
    return options, value


@app.callback(
    Output("ma-camera-map", "figure"),
    Input("ma-layer", "value"),
    Input("ma-camera", "value"),
    Input("ma-joint", "value"),
)
def update_ma_camera_map(layer, selected_cam, joint):
    sub = df_all[df_all["height_label"] == (layer or "Y=1.0")].drop_duplicates(
        "folder_name"
    ).copy()
    available = _ma_available_set()
    fig = go.Figure()
    for az_bin in range(8):
        grp = sub[sub["azimuth_bin"] == az_bin]
        if grp.empty:
            continue
        has_data = grp["folder_name"].isin(available)
        g_ok = grp[has_data]
        if not g_ok.empty:
            is_sel = g_ok["folder_name"] == selected_cam
            g_other = g_ok[~is_sel]
            if not g_other.empty:
                fig.add_trace(go.Scatter(
                    x=g_other["camera_x"], y=g_other["camera_z"],
                    mode="markers",
                    name=f"Bin {az_bin}: {AZ_LABELS[az_bin]}",
                    customdata=g_other["folder_name"],
                    marker=dict(size=11, color=BIN_COLORS[az_bin], opacity=0.85),
                    hovertemplate="%{customdata}<extra></extra>",
                ))
            g_sel = g_ok[is_sel]
            if not g_sel.empty:
                fig.add_trace(go.Scatter(
                    x=g_sel["camera_x"], y=g_sel["camera_z"],
                    mode="markers", name="選択中",
                    customdata=g_sel["folder_name"],
                    marker=dict(
                        size=18, color=BIN_COLORS[az_bin], symbol="star",
                        line=dict(width=2, color="black"),
                    ),
                    hovertemplate="★ %{customdata}<extra></extra>",
                    showlegend=False,
                ))
        g_miss = grp[~has_data]
        if not g_miss.empty:
            fig.add_trace(go.Scatter(
                x=g_miss["camera_x"], y=g_miss["camera_z"],
                mode="markers", name="データなし",
                customdata=g_miss["folder_name"],
                marker=dict(size=9, color="#d0d0d0"),
                hovertemplate="%{customdata}<extra></extra>",
                showlegend=(az_bin == 0),
            ))
    fig.add_trace(go.Scatter(
        x=[0], y=[0], mode="markers",
        marker=dict(size=16, color="red", symbol="x"),
        name="Origin",
    ))
    xmax = 7.0
    if not sub.empty:
        xmax = max(7.0, float(max(sub["camera_x"].abs().max(),
                                  sub["camera_z"].abs().max()) + 1))
    fig.update_layout(
        height=400, margin=dict(t=30, b=10, l=40, r=10),
        xaxis=dict(title="Camera X (m)", range=[-xmax, xmax], dtick=1, gridcolor="#eee"),
        yaxis=dict(title="Camera Z (m)", range=[-xmax, xmax], dtick=1, gridcolor="#eee",
                   scaleanchor="x", scaleratio=1),
        plot_bgcolor="white",
        legend=dict(orientation="h", y=-0.18, font=dict(size=9)),
        hovermode="closest",
        title=dict(text=f"{layer} · {joint or ''}", font=dict(size=12)),
    )
    return fig


@app.callback(
    Output("ma-camera", "value", allow_duplicate=True),
    Input("ma-camera-map", "clickData"),
    prevent_initial_call=True,
)
def ma_map_click(clickData):
    if not clickData or "points" not in clickData:
        raise PreventUpdate
    cam = clickData["points"][0].get("customdata")
    if not cam:
        raise PreventUpdate
    if isinstance(cam, (list, tuple)):
        cam = cam[0]
    return cam


@app.callback(
    Output("ma-graph", "figure"),
    Output("ma-status", "children"),
    Input("ma-camera", "value"),
    Input("ma-joint", "value"),
)
def update_ma_graph(camera, joint):
    if not camera or not joint:
        fig = go.Figure()
        fig.update_layout(title="カメラ / 関節を選択してください")
        return fig, "未選択"

    df = get_ma_frame()
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="MA Noise データなし")
        return fig, "missing data"

    sub = df[(df["folder_name"] == camera) & (df["joint"] == joint)].sort_values(
        "frame_id"
    )
    if sub.empty:
        fig = go.Figure()
        fig.update_layout(title=f"データなし: {camera} / {joint}")
        return fig, f"no rows · {camera}"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sub["frame_id"], y=sub["eps_norm"],
        mode="lines+markers", name="||ε||",
        line=dict(color="#2980b9", width=2), marker=dict(size=5),
    ))
    fig.add_trace(go.Scatter(
        x=sub["frame_id"], y=sub["eps_bar_norm"],
        mode="lines", name="MA ||ε̄||",
        line=dict(color="#27ae60", width=2, dash="dash"),
    ))
    fig.add_trace(go.Scatter(
        x=sub["frame_id"], y=sub["threshold"],
        mode="lines", name="threshold Kσ",
        line=dict(color="#95a5a6", width=1.5, dash="dot"),
    ))
    bad = sub[~sub["keep"].astype(bool)]
    if not bad.empty:
        fig.add_trace(go.Scatter(
            x=bad["frame_id"], y=bad["eps_norm"],
            mode="markers", name="rejected",
            marker=dict(color="#e74c3c", size=9, symbol="circle"),
        ))

    n_rej = int((~sub["keep"].astype(bool)).sum())
    rej_rate = n_rej / len(sub)
    fig.update_layout(
        title=(
            f"{joint} @ {camera}  |  reject {n_rej}/{len(sub)} "
            f"({rej_rate:.1%})  mean||ε||={sub['eps_norm'].mean():.3f}"
        ),
        xaxis_title="Frame",
        yaxis_title="||ε|| (walk-orthogonal)",
        hovermode="x unified",
        margin=dict(t=60, b=40),
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(gridcolor="#eee")
    fig.update_yaxes(gridcolor="#eee", rangemode="tozero")

    status = (
        f"{camera} · {joint} · frames {int(sub['frame_id'].min())}–"
        f"{int(sub['frame_id'].max())} · reject {rej_rate:.1%}"
    )
    return fig, status


# ─────────────────────────────────────────────────────────────────────────────
# 起動
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    host = os.environ.get("DASH_HOST", "127.0.0.1")
    port = int(os.environ.get("DASH_PORT", "8051"))
    debug = os.environ.get("DASH_DEBUG", "true").lower() == "true"

    print("\n" + "=" * 60)
    print("  Calibration Framework Dashboard")
    print("=" * 60)
    print(f"\n  Open: http://localhost:{port}/")
    print("  Press Ctrl+C to stop\n")

    app.run(debug=debug, host=host, port=port)
