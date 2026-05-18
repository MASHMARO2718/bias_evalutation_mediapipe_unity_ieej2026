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
    1. Overview       - モデル比較・補正前後 MAE・評価サマリー
    2. Bin Explorer   - カメラ位置 × ビン構造の可視化（インタラクティブ）
    3. Linear Model   - 局所線形モデルの R² ヒートマップ・係数
    4. Grid Search    - ハイパーパラメータ探索結果
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

print(f"  all_data: {len(df_all)} rows  eval: {len(df_eval)} rows  m4: {len(df_m4)} rows")

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
def build_linear_tab():
    return dbc.Container([
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
                card("R² 全関節 × ビン統計",
                     dcc.Graph(id="lm-r2-bar", style={"height": "280px"},
                               config={"displayModeBar": False}))
            ], width=9),
        ]),
        dbc.Row([
            dbc.Col(card("局所線形 R² ヒートマップ (height_bin × azimuth_bin)",
                         dcc.Graph(id="lm-r2-heatmap", style={"height": "360px"},
                                   config={"displayModeBar": True})),
                    width=6),
            dbc.Col(card("Model 5 グローバル係数 β (選択関節)",
                         dcc.Graph(id="lm-beta-bar", style={"height": "360px"},
                                   config={"displayModeBar": False})),
                    width=6),
        ]),
        dbc.Row([
            dbc.Col(card("局所 vs グローバル R² 比較 (選択関節 × 全ビン)",
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
# レイアウト
# ─────────────────────────────────────────────────────────────────────────────
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H4("Calibration Framework Dashboard",
                    className="text-primary mb-0",
                    style={"fontWeight": "700"}),
            html.Small("MediaPipe Pose — Parametric Bias Correction · 2026-05-18",
                       className="text-muted"),
        ], className="py-3")
    ]),

    dbc.Tabs([
        dbc.Tab(build_overview_tab(),    label="Overview",      tab_id="tab-overview"),
        dbc.Tab(build_bin_explorer_tab(), label="Bin Explorer",  tab_id="tab-bin"),
        dbc.Tab(build_linear_tab(),       label="Linear Model",  tab_id="tab-linear"),
        dbc.Tab(build_gridsearch_tab(),   label="Grid Search",   tab_id="tab-gs"),
        dbc.Tab(build_bin_reference_tab(), label="Bin Reference", tab_id="tab-ref"),
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
        height=340, margin=dict(t=30, b=60, l=60, r=10),
        title=dict(text=f"Local Linear R² — {joint}", font=dict(size=12)),
        xaxis=dict(title="Azimuth Bin", tickangle=-30),
        yaxis=dict(title="Height Layer"),
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
    fig.update_layout(
        height=340, margin=dict(t=30, b=60, l=40, r=10),
        title=dict(text=f"Global β — {joint}  (e = X·β)", font=dict(size=12)),
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
    fig.add_hline(y=overall_mean, line_dash="dot", line_color="gray",
                  annotation_text=f"joint mean R²={overall_mean:.3f}",
                  annotation_font_size=10, annotation_position="top right")
    fig.update_layout(
        height=320,
        margin=dict(t=40, b=40, l=50, r=10),
        xaxis_title="n (samples in bin)",
        yaxis=dict(title="Local R²", range=[0, 1.05]),
        title=dict(text=f"Local R² vs sample size — {joint}", font=dict(size=12)),
        plot_bgcolor="white",
        legend=dict(title="Height", orientation="h", y=-0.25),
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
