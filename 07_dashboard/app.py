"""
インタラクティブ可視化ダッシュボード
Plotly Dashを使用して全データをインタラクティブに表示

プロジェクトルート直下の 07_dashboard/ に配置。
05_direction_detection の output を参照。
"""

import sys
import importlib.util
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc

# パス設定: プロジェクトルートと 05_direction_detection
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
dir_direction = project_root / "05_direction_detection"
sys.path.insert(0, str(dir_direction))

from scripts.data_loader import DataLoader
from scripts.coordinate_transform import CoordinateTransformer

# ダッシュボード用のデータソース（同フォルダの config.py）
_spec = importlib.util.spec_from_file_location("dash_config", Path(__file__).parent / "config.py")
dash_config = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dash_config)
output_dir = dash_config.DATA_SOURCE / "processed_data"

# データ読み込み
print("Loading data...")
df_detailed = pd.read_csv(output_dir / "detailed_results.csv")
df_summary = pd.read_csv(output_dir / "frame_camera_summary.csv")
df_joint = pd.read_csv(output_dir / "joint_summary.csv")

# 相関行列データも読み込み
corr_dir = dash_config.DATA_SOURCE / "correlation_analysis"
try:
    df_corr_theta = pd.read_csv(corr_dir / "correlation_matrix_theta.csv", index_col=0)
    df_corr_psi = pd.read_csv(corr_dir / "correlation_matrix_psi.csv", index_col=0)
    df_corr_3d = pd.read_csv(corr_dir / "correlation_matrix_3d_norm.csv", index_col=0)
    df_high_theta = pd.read_csv(corr_dir / "high_correlation_pairs_theta.csv")
    df_high_psi = pd.read_csv(corr_dir / "high_correlation_pairs_psi.csv")
    df_high_3d = pd.read_csv(corr_dir / "high_correlation_pairs_3d_norm.csv")
    correlation_data_available = True
    print(f"Loaded correlation matrices: theta={df_corr_theta.shape}, psi={df_corr_psi.shape}, 3d={df_corr_3d.shape}")
except FileNotFoundError as e:
    print(f"Warning: Correlation data not found: {e}")
    print("Run 'python run.py --dashboard' to generate correlation analysis")
    correlation_data_available = False

# GroundTruthデータも読み込み（ボット位置表示用）
loader = DataLoader()
gt_df = loader.load_ground_truth()

print(f"Loaded {len(df_detailed)} detailed records")
print(f"Frames: {df_detailed['frame_id'].nunique()}, Cameras: {df_detailed['camera'].nunique()}")


# データ準備関数
def parse_camera_coordinates(camera_name):
    """CapturedFrames_X_Y_Z から座標を抽出"""
    try:
        parts = camera_name.replace('CapturedFrames_', '').split('_')
        return float(parts[0]), float(parts[1]), float(parts[2])
    except (IndexError, ValueError) as e:
        print(f"Warning: Failed to parse camera name '{camera_name}': {e}")
        return None, None, None


def build_camera_availability_map(df_summary):
    """フレームとY座標ごとのカメラ利用可能性マップを作成"""
    camera_map = {}
    for _, row in df_summary.iterrows():
        frame_id = row['frame_id']
        camera = row['camera']
        x, y, z = parse_camera_coordinates(camera)
        
        if x is not None:  # パース成功した場合のみ追加
            key = (frame_id, y)
            if key not in camera_map:
                camera_map[key] = {}
            camera_map[key][(x, z)] = camera
    
    return camera_map


# カメラ利用可能性マップを構築
camera_availability_map = build_camera_availability_map(df_summary)
print(f"Built camera availability map with {len(camera_availability_map)} frame-Y combinations")

# Dashアプリ初期化
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "MotionTrack Data Visualization"

# レイアウト
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("🎯 MotionTrack - インタラクティブ可視化ダッシュボード", 
                   className="text-center mb-3 mt-3",
                   style={'font-size': '1.5rem'})
        ])
    ]),
    
    # メインコントロールエリア（左：コントロール、右：カメラマップ）
    dbc.Row([
        # 左側：全てのコントロール
        dbc.Col([
            # データ概要
            dbc.Card([
                dbc.CardHeader("📊 データ概要", style={'padding': '0.5rem 1rem', 'font-size': '0.9rem'}),
                dbc.CardBody([
                    html.P(f"総データポイント: {len(df_detailed):,}", style={'margin-bottom': '0.3rem', 'font-size': '0.85rem'}),
                    html.P(f"フレーム数: {df_detailed['frame_id'].nunique()}", style={'margin-bottom': '0.3rem', 'font-size': '0.85rem'}),
                    html.P(f"カメラ数: {df_detailed['camera'].nunique()}", style={'margin-bottom': '0.3rem', 'font-size': '0.85rem'}),
                    html.P(f"関節数: {df_detailed['joint'].nunique()}", style={'margin-bottom': '0', 'font-size': '0.85rem'}),
                ], style={'padding': '0.75rem 1rem'})
            ], className="mb-2"),
            
            # フレーム選択
            dbc.Card([
                dbc.CardHeader("⚙️ フレーム選択", style={'padding': '0.5rem 1rem', 'font-size': '0.9rem'}),
                dbc.CardBody([
                    dcc.Dropdown(
                        id='frame-dropdown',
                        options=[{'label': f'Frame {f}', 'value': f} 
                                for f in sorted(df_detailed['frame_id'].unique())],
                        value=20,
                        clearable=False
                    )
                ], style={'padding': '0.75rem 1rem'})
            ], className="mb-2"),
            
            # カメラ高さ選択
            dbc.Card([
                dbc.CardHeader("📐 カメラ高さ (Y座標)", style={'padding': '0.5rem 1rem', 'font-size': '0.9rem'}),
                dbc.CardBody([
                    dcc.Dropdown(
                        id='y-coordinate-dropdown',
                        options=[
                            {'label': 'Y = 0.5', 'value': 0.5},
                            {'label': 'Y = 1.0', 'value': 1.0},
                            {'label': 'Y = 1.5', 'value': 1.5},
                            {'label': 'Y = 2.0', 'value': 2.0},
                        ],
                        value=0.5,
                        clearable=False
                    )
                ], style={'padding': '0.75rem 1rem'})
            ], className="mb-2"),
            
            # 折りたたみ可能なカメラドロップダウン
            dbc.Button(
                "📷 詳細カメラ選択",
                id="collapse-button",
                className="mb-2",
                size="sm",
                color="secondary",
                outline=True
            ),
            dbc.Collapse(
                dbc.Card([
                    dbc.CardHeader("📷 カメラ手動選択（詳細）", style={'padding': '0.5rem 1rem', 'font-size': '0.9rem'}),
                    dbc.CardBody([
                        dcc.Dropdown(
                            id='camera-dropdown',
                            options=[],  # 動的に更新
                            value=None,
                            clearable=False
                        )
                    ], style={'padding': '0.75rem 1rem'})
                ]),
                id="camera-dropdown-collapse",
                is_open=False
            ),
        ], width=6),
        
        # 右側：カメラマップ
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🗺️ カメラ位置選択 (XZ平面)", style={'padding': '0.5rem 1rem', 'font-size': '0.9rem'}),
                dbc.CardBody([
                    dcc.Graph(
                        id='camera-map-graph',
                        config={'displayModeBar': False},
                        style={'height': '530px'}
                    ),
                    html.Div([
                        html.Span("🟢 データあり", style={'margin-right': '15px', 'font-size': '0.85rem'}),
                        html.Span("⚪ データなし", style={'margin-right': '15px', 'font-size': '0.85rem'}),
                        html.Span("🟡 選択中", style={'margin-right': '15px', 'font-size': '0.85rem'}),
                        html.Span("🔴 ボット位置", style={'font-size': '0.85rem'})
                    ], style={'text-align': 'center', 'margin-top': '0.5rem'})
                ], style={'padding': '0.75rem 1rem'})
            ])
        ], width=6),
    ], className="mb-3"),
    
    # 3D骨格表示（最優先で表示）
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🎯 3D骨格表示 - GroundTruth"),
                dbc.CardBody([
                    dcc.Graph(id='skeleton-gt-graph', style={'height': '500px'})
                ])
            ])
        ], width=6),
        
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🎯 3D骨格表示 - MediaPipe"),
                dbc.CardBody([
                    dcc.Graph(id='skeleton-mp-graph', style={'height': '500px'})
                ])
            ])
        ], width=6),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📈 フレーム・カメラ別角度誤差"),
                dbc.CardBody([
                    dcc.Graph(id='frame-camera-error-graph', style={'height': '400px'})
                ])
            ])
        ], width=12),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📊 関節別角度誤差 (選択フレーム・カメラ)"),
                dbc.CardBody([
                    dcc.Graph(id='joint-error-bar-graph', style={'height': '400px'})
                ])
            ])
        ], width=12),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🗺️ カメラ位置別誤差ヒートマップ (選択フレーム)"),
                dbc.CardBody([
                    dcc.Graph(id='camera-heatmap-graph', style={'height': '500px'})
                ])
            ])
        ], width=12),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📉 時系列角度誤差 (選択カメラ)"),
                dbc.CardBody([
                    dcc.Graph(id='time-series-graph', style={'height': '400px'})
                ])
            ])
        ], width=12),
    ], className="mb-4"),
    
    # 相関分析セクション
    dbc.Row([
        dbc.Col([
            html.H3("📊 関節間エラー相関分析", className="text-center mb-3")
        ])
    ]) if correlation_data_available else html.Div(),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🔥 相関行列ヒートマップ"),
                dbc.CardBody([
                    dbc.Tabs([
                        dbc.Tab(
                            dcc.Graph(id='correlation-heatmap-theta', style={'height': '600px'}),
                            label="θ (XY平面)",
                            tab_id="tab-theta"
                        ),
                        dbc.Tab(
                            dcc.Graph(id='correlation-heatmap-psi', style={'height': '600px'}),
                            label="ψ (XZ平面)",
                            tab_id="tab-psi"
                        ),
                        dbc.Tab(
                            dcc.Graph(id='correlation-heatmap-3d', style={'height': '600px'}),
                            label="3D誤差ノルム",
                            tab_id="tab-3d"
                        ),
                    ], id='correlation-tabs', active_tab='tab-theta')
                ])
            ])
        ], width=12)
    ], className="mb-4") if correlation_data_available else html.Div(),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("⚡ 高相関関節ペア (|r| > 0.7)"),
                dbc.CardBody([
                    dbc.Tabs([
                        dbc.Tab([
                            html.Div(id='high-corr-table-theta')
                        ], label="θ (XY平面)", tab_id="tab-theta-table"),
                        dbc.Tab([
                            html.Div(id='high-corr-table-psi')
                        ], label="ψ (XZ平面)", tab_id="tab-psi-table"),
                        dbc.Tab([
                            html.Div(id='high-corr-table-3d')
                        ], label="3D誤差ノルム", tab_id="tab-3d-table"),
                    ], id='high-corr-tabs', active_tab='tab-theta-table')
                ])
            ])
        ], width=12)
    ], className="mb-4") if correlation_data_available else html.Div(),
    
    dcc.Store(id='selected-camera-store', data='CapturedFrames_-1.0_0.5_-3.0'),
    
], fluid=True)


# ========== コールバック ==========

# カメラマップの更新とクリックイベント処理
@app.callback(
    Output('camera-map-graph', 'figure'),
    Output('selected-camera-store', 'data'),
    Input('frame-dropdown', 'value'),
    Input('y-coordinate-dropdown', 'value'),
    Input('camera-map-graph', 'clickData'),
    State('selected-camera-store', 'data')
)
def update_camera_map(frame_id, y_coord, click_data, current_selection):
    """カメラマップを更新し、クリックイベントを処理"""
    from dash import callback_context
    
    # 選択されたフレームとY座標で利用可能なカメラを取得
    df_frame_y = df_summary[df_summary['frame_id'] == frame_id]
    
    # カメラ座標をパース
    camera_coords = []
    camera_lookup = {}  # (x, z) -> camera_name のマッピング
    
    for _, row in df_frame_y.iterrows():
        x, y, z = parse_camera_coordinates(row['camera'])
        # Y座標の比較を緩和（浮動小数点の誤差を考慮）
        if x is not None and abs(y - y_coord) < 0.25:  # 0.1から0.25に変更
            camera_coords.append({'x': x, 'z': z, 'camera': row['camera']})
            camera_lookup[(x, z)] = row['camera']
    
    # GroundTruthから腰の位置を取得（ボットの位置）
    bot_position = None
    try:
        gt_frame = gt_df[gt_df['Frame'] == frame_id]
        if len(gt_frame) > 0:
            # Hips（腰）の位置を取得
            if 'Hips_X' in gt_frame.columns and 'Hips_Z' in gt_frame.columns:
                bot_x = float(gt_frame['Hips_X'].values[0])
                bot_z = float(gt_frame['Hips_Z'].values[0])
                bot_position = (bot_x, bot_z)
    except Exception as e:
        print(f"Failed to get bot position: {e}")
    
    # すべての可能なカメラ位置を生成（-5から5まで1刻み）
    all_x = np.arange(-6, 7, 1)  # -6から6まで
    all_z = np.arange(-6, 7, 1)  # -6から6まで
    
    available_set = {(c['x'], c['z']) for c in camera_coords}
    
    data_available = []
    data_unavailable = []
    
    for x in all_x:
        for z in all_z:
            if (x, z) in available_set:
                data_available.append({'x': x, 'z': z})
            else:
                data_unavailable.append({'x': x, 'z': z})
    
    # クリックイベントの処理
    selected_camera = current_selection
    ctx = callback_context
    
    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'camera-map-graph' and click_data:
            clicked_x = click_data['points'][0]['x']
            clicked_z = click_data['points'][0]['y']
            
            # クリックされた点がデータありの場合のみ選択
            if (clicked_x, clicked_z) in camera_lookup:
                selected_camera = camera_lookup[(clicked_x, clicked_z)]
        elif trigger_id in ['frame-dropdown', 'y-coordinate-dropdown']:
            # フレームまたはY座標が変更された場合
            # 現在選択中のカメラが新しい条件で利用可能かチェック
            if selected_camera:
                sel_x, sel_y, sel_z = parse_camera_coordinates(selected_camera)
                if sel_x is None or (sel_x, sel_z) not in camera_lookup:
                    # 利用可能でない場合、最初の利用可能なカメラを選択
                    if camera_coords:
                        selected_camera = camera_coords[0]['camera']
                    else:
                        selected_camera = None
            else:
                # カメラが未選択の場合、最初の利用可能なカメラを選択
                if camera_coords:
                    selected_camera = camera_coords[0]['camera']
    else:
        # 初回起動時
        if not selected_camera and camera_coords:
            selected_camera = camera_coords[0]['camera']
    
    # プロット作成
    fig = go.Figure()
    
    # データなし（灰色）
    if data_unavailable:
        df_unavail = pd.DataFrame(data_unavailable)
        fig.add_trace(go.Scatter(
            x=df_unavail['x'],
            y=df_unavail['z'],
            mode='markers',
            marker=dict(size=12, color='lightgray', opacity=0.3, symbol='circle'),
            name='データなし',
            hoverinfo='skip',
            showlegend=False
        ))
    
    # データあり（緑）
    if data_available:
        df_avail = pd.DataFrame(data_available)
        hover_texts = []
        for _, row in df_avail.iterrows():
            cam_name = camera_lookup.get((row['x'], row['z']), 'Unknown')
            hover_texts.append(f"X: {row['x']}<br>Z: {row['z']}<br>{cam_name}<br><b>クリックで選択</b>")
        
        fig.add_trace(go.Scatter(
            x=df_avail['x'],
            y=df_avail['z'],
            mode='markers',
            marker=dict(size=15, color='green', symbol='circle'),
            name='データあり',
            text=hover_texts,
            hovertemplate='%{text}<extra></extra>',
            showlegend=False
        ))
    
    # 選択中（黄色）
    if selected_camera:
        sel_x, sel_y, sel_z = parse_camera_coordinates(selected_camera)
        if sel_x is not None and abs(sel_y - y_coord) < 0.25:  # 0.1から0.25に変更
            fig.add_trace(go.Scatter(
                x=[sel_x],
                y=[sel_z],
                mode='markers',
                marker=dict(size=20, color='yellow', symbol='star', 
                           line=dict(width=2, color='black')),
                name='選択中',
                hovertemplate=f'<b>選択中</b><br>X: {sel_x}<br>Z: {sel_z}<br>{selected_camera}<extra></extra>',
                showlegend=False
            ))
    
    # ボットの位置（赤い点）
    if bot_position:
        fig.add_trace(go.Scatter(
            x=[bot_position[0]],
            y=[bot_position[1]],
            mode='markers',
            marker=dict(size=18, color='red', symbol='circle', 
                       line=dict(width=2, color='darkred')),
            name='ボット位置',
            hovertemplate=f'<b>ボット位置 (Frame {frame_id})</b><br>X: {bot_position[0]:.2f}<br>Z: {bot_position[1]:.2f}<extra></extra>',
            showlegend=False
        ))
    
    fig.update_layout(
        xaxis_title="Camera X",
        yaxis_title="Camera Z",
        xaxis=dict(
            scaleanchor="y", 
            scaleratio=1,
            range=[-6.5, 6.5],
            dtick=1,
            gridcolor='lightgray'
        ),
        yaxis=dict(
            scaleanchor="x", 
            scaleratio=1,
            range=[-6.5, 6.5],
            dtick=1,
            gridcolor='lightgray'
        ),
        showlegend=False,
        hovermode='closest',
        height=530,
        plot_bgcolor='white'
    )
    
    return fig, selected_camera


# カメラリストを更新（折りたたみ用）
@app.callback(
    Output('camera-dropdown', 'options'),
    Output('camera-dropdown', 'value'),
    Input('frame-dropdown', 'value'),
    Input('selected-camera-store', 'data')
)
def update_camera_list(frame_id, selected_camera):
    """選択されたフレームで利用可能なカメラリストを更新"""
    cameras = df_detailed[df_detailed['frame_id'] == frame_id]['camera'].unique()
    options = [{'label': cam, 'value': cam} for cam in sorted(cameras)]
    
    # selected_camera_storeの値を優先、なければデフォルト値を設定
    if selected_camera and selected_camera in cameras:
        default_camera = selected_camera
    else:
        default_camera = 'CapturedFrames_-1.0_0.5_-3.0' if 'CapturedFrames_-1.0_0.5_-3.0' in cameras else (cameras[0] if len(cameras) > 0 else None)
    
    return options, default_camera


# 折りたたみボタンのコールバック
@app.callback(
    Output("camera-dropdown-collapse", "is_open"),
    Input("collapse-button", "n_clicks"),
    State("camera-dropdown-collapse", "is_open"),
    prevent_initial_call=True
)
def toggle_collapse(n, is_open):
    """カメラドロップダウンの表示/非表示を切り替え"""
    if n:
        return not is_open
    return is_open


# フレーム・カメラ別誤差グラフ
@app.callback(
    Output('frame-camera-error-graph', 'figure'),
    Input('selected-camera-store', 'data')
)
def update_frame_camera_error(camera):
    """選択されたカメラの全フレームでの誤差推移"""
    if not camera:
        return go.Figure()
    
    df_cam = df_summary[df_summary['camera'] == camera].sort_values('frame_id')
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_cam['frame_id'],
        y=df_cam['mean_abs_delta_theta'],
        mode='lines+markers',
        name='平均|Δθ| (XY平面)',
        line=dict(color='blue', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=df_cam['frame_id'],
        y=df_cam['mean_abs_delta_psi'],
        mode='lines+markers',
        name='平均|Δψ| (XZ平面)',
        line=dict(color='red', width=2)
    ))
    
    fig.update_layout(
        title=f"カメラ: {camera}",
        xaxis_title="Frame ID",
        yaxis_title="角度誤差 (degrees)",
        hovermode='x unified',
        showlegend=True
    )
    
    return fig


# 3D骨格表示（GroundTruth）
@app.callback(
    Output('skeleton-gt-graph', 'figure'),
    Input('frame-dropdown', 'value'),
    Input('selected-camera-store', 'data')
)
def update_skeleton_gt(frame_id, camera):
    """GroundTruth骨格の3D表示（棒人間）"""
    if not camera:
        return go.Figure()
    
    df_frame = df_detailed[(df_detailed['frame_id'] == frame_id) & 
                           (df_detailed['camera'] == camera)]
    
    # 座標辞書を作成（HIPを含む）
    coords = {}
    for _, row in df_frame.iterrows():
        coords[row['joint']] = (row['gt_x'], row['gt_y'], row['gt_z'])
    
    # HIP（原点）を追加
    if 'LEFT_HIP' in coords and 'RIGHT_HIP' in coords:
        coords['HIP_CENTER'] = (0, 0, 0)
    
    # 骨格の接続定義
    connections = [
        # 胴体
        ('HIP_CENTER', 'LEFT_SHOULDER'),
        ('HIP_CENTER', 'RIGHT_SHOULDER'),
        ('LEFT_SHOULDER', 'RIGHT_SHOULDER'),
        
        # 左腕
        ('LEFT_SHOULDER', 'LEFT_ELBOW'),
        ('LEFT_ELBOW', 'LEFT_WRIST'),
        
        # 右腕
        ('RIGHT_SHOULDER', 'RIGHT_ELBOW'),
        ('RIGHT_ELBOW', 'RIGHT_WRIST'),
        
        # 左脚
        ('HIP_CENTER', 'LEFT_KNEE'),
        ('LEFT_KNEE', 'LEFT_ANKLE'),
        
        # 右脚
        ('HIP_CENTER', 'RIGHT_KNEE'),
        ('RIGHT_KNEE', 'RIGHT_ANKLE'),
    ]
    
    fig = go.Figure()
    
    # 骨格の線を描画
    for joint1, joint2 in connections:
        if joint1 in coords and joint2 in coords:
            x1, y1, z1 = coords[joint1]
            x2, y2, z2 = coords[joint2]
            
            fig.add_trace(go.Scatter3d(
                x=[x1, x2],
                y=[y1, y2],
                z=[z1, z2],
                mode='lines',
                line=dict(color='blue', width=5),
                showlegend=False,
                hoverinfo='skip'
            ))
    
    # 関節点を描画
    df_no_hip = df_frame[~df_frame['joint'].str.contains('HIP')]
    fig.add_trace(go.Scatter3d(
        x=df_no_hip['gt_x'],
        y=df_no_hip['gt_y'],
        z=df_no_hip['gt_z'],
        mode='markers+text',
        marker=dict(size=5, color='darkblue'),
        text=df_no_hip['joint'],
        textposition='top center',
        textfont=dict(size=8),
        name='関節',
        hovertemplate='<b>%{text}</b><br>X: %{x:.3f}<br>Y: %{y:.3f}<br>Z: %{z:.3f}<extra></extra>'
    ))
    
    # 原点（腰）
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[0],
        mode='markers',
        marker=dict(size=8, color='red', symbol='diamond'),
        name='HIP (原点)',
        hovertemplate='<b>HIP CENTER</b><br>X: 0<br>Y: 0<br>Z: 0<extra></extra>'
    ))
    
    # データの範囲を取得
    all_coords = list(coords.values())
    if all_coords:
        x_vals = [c[0] for c in all_coords]
        y_vals = [c[1] for c in all_coords]
        z_vals = [c[2] for c in all_coords]
        
        # 範囲を計算（余裕を持たせる）
        x_range = [min(x_vals) - 0.5, max(x_vals) + 0.5]
        y_range = [min(y_vals) - 0.5, max(y_vals) + 0.5]
        z_range = [min(z_vals) - 0.5, max(z_vals) + 0.5]
    else:
        x_range = [-1, 1]
        y_range = [-1, 1]
        z_range = [-1, 1]
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(
                title='X (m)',
                backgroundcolor="rgb(240, 240, 240)",
                gridcolor="white",
                showbackground=True,
                range=x_range,
                dtick=0.2
            ),
            yaxis=dict(
                title='Y (m)',
                backgroundcolor="rgb(240, 240, 240)",
                gridcolor="white",
                showbackground=True,
                range=y_range,
                dtick=0.2
            ),
            zaxis=dict(
                title='Z (m)',
                backgroundcolor="rgb(240, 240, 240)",
                gridcolor="white",
                showbackground=True,
                range=z_range,
                dtick=0.2
            ),
            aspectmode='cube',
            camera=dict(
                eye=dict(x=2.0, y=2.5, z=2.0),
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=1, z=0)
            )
        ),
        title=dict(
            text=f"GroundTruth 骨格 - Frame {frame_id}<br><sub>マウスドラッグで回転 | ホイールでズーム | 右クリックドラッグで移動</sub>",
            x=0.5,
            xanchor='center'
        ),
        showlegend=True,
        hovermode='closest',
        margin=dict(l=0, r=0, t=60, b=0)
    )
    
    return fig


# 3D骨格表示（MediaPipe）
@app.callback(
    Output('skeleton-mp-graph', 'figure'),
    Input('frame-dropdown', 'value'),
    Input('selected-camera-store', 'data')
)
def update_skeleton_mp(frame_id, camera):
    """MediaPipe骨格の3D表示（棒人間）"""
    if not camera:
        return go.Figure()
    
    df_frame = df_detailed[(df_detailed['frame_id'] == frame_id) & 
                           (df_detailed['camera'] == camera)]
    
    # 座標辞書を作成（HIPを含む）
    coords = {}
    for _, row in df_frame.iterrows():
        coords[row['joint']] = (row['mp_x'], row['mp_y'], row['mp_z'])
    
    # HIP（原点）を追加
    if 'LEFT_HIP' in coords and 'RIGHT_HIP' in coords:
        coords['HIP_CENTER'] = (0, 0, 0)
    
    # 骨格の接続定義
    connections = [
        # 胴体
        ('HIP_CENTER', 'LEFT_SHOULDER'),
        ('HIP_CENTER', 'RIGHT_SHOULDER'),
        ('LEFT_SHOULDER', 'RIGHT_SHOULDER'),
        
        # 左腕
        ('LEFT_SHOULDER', 'LEFT_ELBOW'),
        ('LEFT_ELBOW', 'LEFT_WRIST'),
        
        # 右腕
        ('RIGHT_SHOULDER', 'RIGHT_ELBOW'),
        ('RIGHT_ELBOW', 'RIGHT_WRIST'),
        
        # 左脚
        ('HIP_CENTER', 'LEFT_KNEE'),
        ('LEFT_KNEE', 'LEFT_ANKLE'),
        
        # 右脚
        ('HIP_CENTER', 'RIGHT_KNEE'),
        ('RIGHT_KNEE', 'RIGHT_ANKLE'),
    ]
    
    fig = go.Figure()
    
    # 骨格の線を描画
    for joint1, joint2 in connections:
        if joint1 in coords and joint2 in coords:
            x1, y1, z1 = coords[joint1]
            x2, y2, z2 = coords[joint2]
            
            fig.add_trace(go.Scatter3d(
                x=[x1, x2],
                y=[y1, y2],
                z=[z1, z2],
                mode='lines',
                line=dict(color='red', width=5),
                showlegend=False,
                hoverinfo='skip'
            ))
    
    # 関節点を描画
    df_no_hip = df_frame[~df_frame['joint'].str.contains('HIP')]
    fig.add_trace(go.Scatter3d(
        x=df_no_hip['mp_x'],
        y=df_no_hip['mp_y'],
        z=df_no_hip['mp_z'],
        mode='markers+text',
        marker=dict(size=5, color='darkred'),
        text=df_no_hip['joint'],
        textposition='top center',
        textfont=dict(size=8),
        name='関節',
        hovertemplate='<b>%{text}</b><br>X: %{x:.3f}<br>Y: %{y:.3f}<br>Z: %{z:.3f}<extra></extra>'
    ))
    
    # 原点（腰）
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[0],
        mode='markers',
        marker=dict(size=8, color='orange', symbol='diamond'),
        name='HIP (原点)',
        hovertemplate='<b>HIP CENTER</b><br>X: 0<br>Y: 0<br>Z: 0<extra></extra>'
    ))
    
    # データの範囲を取得
    all_coords = list(coords.values())
    if all_coords:
        x_vals = [c[0] for c in all_coords]
        y_vals = [c[1] for c in all_coords]
        z_vals = [c[2] for c in all_coords]
        
        # 範囲を計算（余裕を持たせる）
        x_range = [min(x_vals) - 0.5, max(x_vals) + 0.5]
        y_range = [min(y_vals) - 0.5, max(y_vals) + 0.5]
        z_range = [min(z_vals) - 0.5, max(z_vals) + 0.5]
    else:
        x_range = [-1, 1]
        y_range = [-1, 1]
        z_range = [-1, 1]
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(
                title='X',
                backgroundcolor="rgb(255, 240, 240)",
                gridcolor="white",
                showbackground=True,
                range=x_range,
                dtick=0.2
            ),
            yaxis=dict(
                title='Y',
                backgroundcolor="rgb(255, 240, 240)",
                gridcolor="white",
                showbackground=True,
                range=y_range,
                dtick=0.2
            ),
            zaxis=dict(
                title='Z',
                backgroundcolor="rgb(255, 240, 240)",
                gridcolor="white",
                showbackground=True,
                range=z_range,
                dtick=0.2
            ),
            aspectmode='cube',
            camera=dict(
                eye=dict(x=2.0, y=2.5, z=2.0),
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=1, z=0)
            )
        ),
        title=dict(
            text=f"MediaPipe 骨格 - Frame {frame_id}<br><sub>マウスドラッグで回転 | ホイールでズーム | 右クリックドラッグで移動</sub>",
            x=0.5,
            xanchor='center'
        ),
        showlegend=True,
        hovermode='closest',
        margin=dict(l=0, r=0, t=60, b=0)
    )
    
    return fig


# 関節別誤差バーグラフ
@app.callback(
    Output('joint-error-bar-graph', 'figure'),
    Input('frame-dropdown', 'value'),
    Input('selected-camera-store', 'data')
)
def update_joint_error_bar(frame_id, camera):
    """選択されたフレーム・カメラでの関節別誤差"""
    if not camera:
        return go.Figure()
    
    df_frame = df_detailed[(df_detailed['frame_id'] == frame_id) & 
                           (df_detailed['camera'] == camera)]
    
    # HIPを除外
    df_frame = df_frame[~df_frame['joint'].str.contains('HIP')]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df_frame['joint'],
        y=df_frame['delta_theta_deg'].abs(),
        name='|Δθ| (XY平面)',
        marker_color='blue'
    ))
    
    fig.add_trace(go.Bar(
        x=df_frame['joint'],
        y=df_frame['delta_psi_deg'].abs(),
        name='|Δψ| (XZ平面)',
        marker_color='red'
    ))
    
    fig.update_layout(
        title=f"Frame {frame_id}, Camera: {camera}",
        xaxis_title="関節",
        yaxis_title="角度誤差 (degrees)",
        barmode='group'
    )
    
    return fig


# カメラ位置別ヒートマップ
@app.callback(
    Output('camera-heatmap-graph', 'figure'),
    Input('frame-dropdown', 'value')
)
def update_camera_heatmap(frame_id):
    """選択されたフレームでのカメラ位置別誤差ヒートマップ"""
    df_frame = df_summary[df_summary['frame_id'] == frame_id].copy()
    
    # カメラ名からXYZ座標を抽出
    def parse_camera_name(name):
        # CapturedFrames_X_Y_Z形式
        parts = name.replace('CapturedFrames_', '').split('_')
        return float(parts[0]), float(parts[1]), float(parts[2])
    
    df_frame[['cam_x', 'cam_y', 'cam_z']] = df_frame['camera'].apply(
        lambda x: pd.Series(parse_camera_name(x))
    )
    
    # Y=0.5, 1.5ごとに分けてヒートマップ作成
    fig = px.scatter(
        df_frame,
        x='cam_x',
        y='cam_z',
        color='mean_abs_delta_theta',
        size='mean_abs_delta_theta',
        hover_data=['camera', 'mean_abs_delta_theta', 'mean_abs_delta_psi'],
        color_continuous_scale='RdYlGn_r',
        title=f"Frame {frame_id} - カメラ位置別平均|Δθ|"
    )
    
    fig.update_layout(
        xaxis_title="Camera X",
        yaxis_title="Camera Z",
        coloraxis_colorbar_title="平均|Δθ| (°)"
    )
    
    return fig


# 時系列グラフ
@app.callback(
    Output('time-series-graph', 'figure'),
    Input('selected-camera-store', 'data')
)
def update_time_series(camera):
    """選択されたカメラの時系列誤差"""
    if not camera:
        return go.Figure()
    
    df_cam = df_summary[df_summary['camera'] == camera].sort_values('frame_id')
    
    fig = go.Figure()
    
    # 全関節の平均
    fig.add_trace(go.Scatter(
        x=df_cam['frame_id'],
        y=df_cam['mean_abs_delta_theta'],
        mode='lines+markers',
        name='全関節平均|Δθ|',
        line=dict(color='blue', width=3)
    ))
    
    # 最大値
    fig.add_trace(go.Scatter(
        x=df_cam['frame_id'],
        y=df_cam['max_abs_delta_theta'],
        mode='lines',
        name='最大|Δθ|',
        line=dict(color='lightblue', width=1, dash='dash')
    ))
    
    # 中央値
    fig.add_trace(go.Scatter(
        x=df_cam['frame_id'],
        y=df_cam['median_abs_delta_theta'],
        mode='lines',
        name='中央値|Δθ|',
        line=dict(color='darkblue', width=1, dash='dot')
    ))
    
    fig.update_layout(
        title=f"Camera: {camera}",
        xaxis_title="Frame ID",
        yaxis_title="角度誤差|Δθ| (degrees)",
        hovermode='x unified',
        showlegend=True
    )
    
    return fig


# ========== 相関分析コールバック ==========

if correlation_data_available:
    # θの相関ヒートマップ
    @app.callback(
        Output('correlation-heatmap-theta', 'figure'),
        Input('correlation-tabs', 'active_tab')
    )
    def update_correlation_heatmap_theta(active_tab):
        """θ（XY平面）の相関ヒートマップ"""
        if active_tab != 'tab-theta':
            return go.Figure()
        
        fig = go.Figure(data=go.Heatmap(
            z=df_corr_theta.values,
            x=df_corr_theta.columns,
            y=df_corr_theta.index,
            colorscale='RdBu',
            zmid=0,
            zmin=-1,
            zmax=1,
            text=df_corr_theta.values,
            texttemplate='%{text:.2f}',
            textfont={"size": 10},
            colorbar=dict(title='相関係数')
        ))
        
        fig.update_layout(
            title='関節間エラー相関行列 - θ (XY平面)',
            xaxis=dict(title='関節', tickangle=45),
            yaxis=dict(title='関節'),
            height=600
        )
        
        return fig
    
    
    # ψの相関ヒートマップ
    @app.callback(
        Output('correlation-heatmap-psi', 'figure'),
        Input('correlation-tabs', 'active_tab')
    )
    def update_correlation_heatmap_psi(active_tab):
        """ψ（XZ平面）の相関ヒートマップ"""
        if active_tab != 'tab-psi':
            return go.Figure()
        
        fig = go.Figure(data=go.Heatmap(
            z=df_corr_psi.values,
            x=df_corr_psi.columns,
            y=df_corr_psi.index,
            colorscale='RdBu',
            zmid=0,
            zmin=-1,
            zmax=1,
            text=df_corr_psi.values,
            texttemplate='%{text:.2f}',
            textfont={"size": 10},
            colorbar=dict(title='相関係数')
        ))
        
        fig.update_layout(
            title='関節間エラー相関行列 - ψ (XZ平面)',
            xaxis=dict(title='関節', tickangle=45),
            yaxis=dict(title='関節'),
            height=600
        )
        
        return fig
    
    
    # 3Dノルムの相関ヒートマップ
    @app.callback(
        Output('correlation-heatmap-3d', 'figure'),
        Input('correlation-tabs', 'active_tab')
    )
    def update_correlation_heatmap_3d(active_tab):
        """3D誤差ノルムの相関ヒートマップ"""
        if active_tab != 'tab-3d':
            return go.Figure()
        
        fig = go.Figure(data=go.Heatmap(
            z=df_corr_3d.values,
            x=df_corr_3d.columns,
            y=df_corr_3d.index,
            colorscale='RdBu',
            zmid=0,
            zmin=-1,
            zmax=1,
            text=df_corr_3d.values,
            texttemplate='%{text:.2f}',
            textfont={"size": 10},
            colorbar=dict(title='相関係数')
        ))
        
        fig.update_layout(
            title='関節間エラー相関行列 - 3D誤差ノルム',
            xaxis=dict(title='関節', tickangle=45),
            yaxis=dict(title='関節'),
            height=600
        )
        
        return fig
    
    
    # 高相関ペアテーブル（θ）
    @app.callback(
        Output('high-corr-table-theta', 'children'),
        Input('high-corr-tabs', 'active_tab')
    )
    def update_high_corr_table_theta(active_tab):
        """θの高相関ペアテーブル"""
        if active_tab != 'tab-theta-table':
            return html.Div()
        
        if len(df_high_theta) == 0:
            return html.P("高相関ペア (|r| > 0.7) は見つかりませんでした。", className="text-muted")
        
        return dbc.Table.from_dataframe(
            df_high_theta.round(3),
            striped=True,
            bordered=True,
            hover=True,
            size='sm'
        )
    
    
    # 高相関ペアテーブル（ψ）
    @app.callback(
        Output('high-corr-table-psi', 'children'),
        Input('high-corr-tabs', 'active_tab')
    )
    def update_high_corr_table_psi(active_tab):
        """ψの高相関ペアテーブル"""
        if active_tab != 'tab-psi-table':
            return html.Div()
        
        if len(df_high_psi) == 0:
            return html.P("高相関ペア (|r| > 0.7) は見つかりませんでした。", className="text-muted")
        
        return dbc.Table.from_dataframe(
            df_high_psi.round(3),
            striped=True,
            bordered=True,
            hover=True,
            size='sm'
        )
    
    
    # 高相関ペアテーブル（3D）
    @app.callback(
        Output('high-corr-table-3d', 'children'),
        Input('high-corr-tabs', 'active_tab')
    )
    def update_high_corr_table_3d(active_tab):
        """3Dの高相関ペアテーブル"""
        if active_tab != 'tab-3d-table':
            return html.Div()
        
        if len(df_high_3d) == 0:
            return html.P("高相関ペア (|r| > 0.7) は見つかりませんでした。", className="text-muted")
        
        return dbc.Table.from_dataframe(
            df_high_3d.round(3),
            striped=True,
            bordered=True,
            hover=True,
            size='sm'
        )


# カメラドロップダウン変更時にStoreを更新
@app.callback(
    Output('selected-camera-store', 'data', allow_duplicate=True),
    Input('camera-dropdown', 'value'),
    prevent_initial_call=True
)
def sync_camera_dropdown_to_store(camera):
    return camera


if __name__ == '__main__':
    import os
    host = os.environ.get('DASH_HOST', '127.0.0.1')
    debug = os.environ.get('DASH_DEBUG', 'true').lower() == 'true'
    port = int(os.environ.get('DASH_PORT', '8050'))

    print("\n" + "="*60)
    print("[START] Interactive Dashboard Starting...")
    print("="*60)
    print("\nDashboard is running!")
    print("Open your browser and navigate to:")
    print(f"\n   http://localhost:{port}/")
    if host == '0.0.0.0':
        print("   (Docker: use host machine's IP or localhost with port mapping)")
    print("\nPress Ctrl+C to stop the server")
    print("="*60 + "\n")

    app.run(debug=debug, host=host, port=port)
