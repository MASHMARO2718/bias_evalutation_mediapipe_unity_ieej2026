"""
関節間エラー相関分析スクリプト（11: Y軸反転修正版）
各関節の角度誤差がどのように相関しているかを定量化
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib import font_manager
import warnings
warnings.filterwarnings('ignore')
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for headless execution

# プロジェクトルートをパスに追加（05_direction_detection）
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
import config

# 日本語フォントの設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Meiryo']
plt.rcParams['axes.unicode_minus'] = False


class CorrelationAnalyzer:
    """関節間エラー相関分析"""
    
    def __init__(self, detailed_results_csv: str):
        """
        Parameters:
            detailed_results_csv: process_all_data.pyで生成された詳細結果CSV
        """
        self.df = pd.read_csv(detailed_results_csv)
        self.output_dir = config.OUTPUT_DIR / "correlation_analysis"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[INFO] Loaded {len(self.df)} rows from {detailed_results_csv}")
        print(f"[INFO] Frames: {self.df['frame_id'].nunique()}")
        print(f"[INFO] Cameras: {self.df['camera'].nunique()}")
        print(f"[INFO] Joints: {self.df['joint'].nunique()}")
        
        # 関節リスト
        self.joints = sorted(self.df['joint'].unique())
        self.n_joints = len(self.joints)
        
    def compute_option_a_theta(self):
        """
        オプションA: θ（XY平面）の相関行列を計算
        各関節について、全フレーム×全カメラでの誤差時系列を作成
        
        Returns:
            pd.DataFrame: N×N相関行列（indexとcolumnsは関節名）
        """
        print("\n=== Option A: Computing θ (XY plane) correlation matrix ===")
        
        # ピボットテーブル: 行=(frame, camera), 列=joint, 値=delta_theta_deg
        pivot = self.df.pivot_table(
            index=['frame_id', 'camera'],
            columns='joint',
            values='delta_theta_deg',
            aggfunc='first'
        )
        
        print(f"[INFO] Pivot shape: {pivot.shape} (observations × joints)")
        print(f"[INFO] Missing values: {pivot.isna().sum().sum()}")
        
        # 欠損値を持つ行を削除（全関節が揃っている観測のみ使用）
        pivot_clean = pivot.dropna()
        print(f"[INFO] Clean pivot shape: {pivot_clean.shape}")
        
        # 相関行列を計算
        corr_matrix = pivot_clean.corr(method='pearson')
        
        print(f"[INFO] Correlation matrix shape: {corr_matrix.shape}")
        
        return corr_matrix
    
    def compute_option_a_psi(self):
        """
        オプションA: ψ（XZ平面）の相関行列を計算
        
        Returns:
            pd.DataFrame: N×N相関行列（indexとcolumnsは関節名）
        """
        print("\n=== Option A: Computing ψ (XZ plane) correlation matrix ===")
        
        # ピボットテーブル: 行=(frame, camera), 列=joint, 値=delta_psi_deg
        pivot = self.df.pivot_table(
            index=['frame_id', 'camera'],
            columns='joint',
            values='delta_psi_deg',
            aggfunc='first'
        )
        
        print(f"[INFO] Pivot shape: {pivot.shape} (observations × joints)")
        print(f"[INFO] Missing values: {pivot.isna().sum().sum()}")
        
        # 欠損値を持つ行を削除
        pivot_clean = pivot.dropna()
        print(f"[INFO] Clean pivot shape: {pivot_clean.shape}")
        
        # 相関行列を計算
        corr_matrix = pivot_clean.corr(method='pearson')
        
        print(f"[INFO] Correlation matrix shape: {corr_matrix.shape}")
        
        return corr_matrix
    
    def compute_option_c_3d_norm(self):
        """
        オプションC: 3D誤差ノルムの相関行列を計算
        
        Returns:
            pd.DataFrame: N×N相関行列（indexとcolumnsは関節名）
        """
        print("\n=== Option C: Computing 3D error norm correlation matrix ===")
        
        # ピボットテーブル: 行=(frame, camera), 列=joint, 値=error_3d
        pivot = self.df.pivot_table(
            index=['frame_id', 'camera'],
            columns='joint',
            values='error_3d',
            aggfunc='first'
        )
        
        print(f"[INFO] Pivot shape: {pivot.shape} (observations × joints)")
        print(f"[INFO] Missing values: {pivot.isna().sum().sum()}")
        
        # 欠損値を持つ行を削除
        pivot_clean = pivot.dropna()
        print(f"[INFO] Clean pivot shape: {pivot_clean.shape}")
        
        # 相関行列を計算
        corr_matrix = pivot_clean.corr(method='pearson')
        
        print(f"[INFO] Correlation matrix shape: {corr_matrix.shape}")
        
        return corr_matrix
    
    def save_correlation_matrix(self, corr_matrix: pd.DataFrame, name: str):
        """
        相関行列をCSVに保存
        
        Parameters:
            corr_matrix: 相関行列
            name: ファイル名の識別子（例: 'theta', 'psi', '3d_norm'）
        """
        output_path = self.output_dir / f'correlation_matrix_{name}.csv'
        corr_matrix.to_csv(output_path)
        print(f"[SAVE] {output_path}")
    
    def plot_heatmap(self, corr_matrix: pd.DataFrame, title: str, filename: str):
        """
        相関行列のヒートマップを作成
        
        Parameters:
            corr_matrix: 相関行列
            title: グラフタイトル
            filename: 保存ファイル名（拡張子なし）
        """
        print(f"\n[PLOT] Creating heatmap: {title}")
        
        # 図のサイズを設定（関節数に応じて調整・論文用にやや大きめ）
        figsize = (max(14, self.n_joints * 0.6), max(12, self.n_joints * 0.5))
        fig, ax = plt.subplots(figsize=figsize)
        
        # ヒートマップを描画（セル内数値・軸ラベルを読みやすく）
        sns.heatmap(
            corr_matrix,
            vmin=-1, vmax=1,
            cmap='coolwarm',
            center=0,
            annot=True,
            fmt='.2f',
            square=True,
            linewidths=0.5,
            annot_kws={'fontsize': 9},
            cbar_kws={'label': 'Correlation Coefficient', 'shrink': 0.8},
            ax=ax
        )
        
        ax.set_title(title, fontsize=18, pad=20)
        ax.set_xlabel('Joint', fontsize=14)
        ax.set_ylabel('Joint', fontsize=14)
        
        plt.xticks(rotation=45, ha='right', fontsize=11)
        plt.yticks(rotation=0, fontsize=11)
        
        plt.tight_layout()
        
        # 保存（高解像度で論文掲載時に縮小しても読めるように）
        output_path = self.output_dir / f'{filename}.png'
        plt.savefig(output_path, dpi=200, bbox_inches='tight')
        print(f"[SAVE] {output_path}")
        
        plt.close()
    
    def extract_important_joints(self, corr_matrix: pd.DataFrame, 
                                  important_joints: list = None):
        """
        主要関節のみを抽出した相関行列を作成
        
        Parameters:
            corr_matrix: 元の相関行列
            important_joints: 抽出する関節名のリスト（Noneの場合はデフォルト）
        
        Returns:
            pd.DataFrame: 抽出された相関行列
        """
        if important_joints is None:
            # デフォルト: 主要な関節のみ（肩、肘、手首、膝、足首）
            important_joints = [
                'LEFT_SHOULDER', 'RIGHT_SHOULDER',
                'LEFT_ELBOW', 'RIGHT_ELBOW',
                'LEFT_WRIST', 'RIGHT_WRIST',
                'LEFT_KNEE', 'RIGHT_KNEE',
                'LEFT_ANKLE', 'RIGHT_ANKLE'
            ]
            # データに存在する関節のみに絞る
            important_joints = [j for j in important_joints if j in corr_matrix.columns]
        
        # 抽出
        extracted = corr_matrix.loc[important_joints, important_joints]
        
        print(f"[INFO] Extracted important joints: {len(important_joints)} joints")
        
        return extracted
    
    def analyze_high_correlations(self, corr_matrix: pd.DataFrame, 
                                   threshold: float = 0.7):
        """
        高い相関を持つ関節ペアを分析
        
        Parameters:
            corr_matrix: 相関行列
            threshold: 相関係数の閾値（これ以上を高相関とみなす）
        
        Returns:
            pd.DataFrame: 高相関ペアのリスト
        """
        print(f"\n=== Analyzing high correlations (|r| > {threshold}) ===")
        
        # 対角成分（自己相関=1.0）を除外
        # 上三角のみを取得（対称行列なので重複排除）
        high_corr_pairs = []
        
        for i in range(len(corr_matrix)):
            for j in range(i+1, len(corr_matrix)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) > threshold:
                    high_corr_pairs.append({
                        'joint_1': corr_matrix.index[i],
                        'joint_2': corr_matrix.columns[j],
                        'correlation': corr_value
                    })
        
        # DataFrameに変換してソート
        df_pairs = pd.DataFrame(high_corr_pairs)
        
        if len(df_pairs) > 0:
            df_pairs = df_pairs.sort_values('correlation', ascending=False, key=abs)
            print(f"[INFO] Found {len(df_pairs)} high-correlation pairs:")
            print(df_pairs.to_string(index=False))
        else:
            print(f"[INFO] No pairs found with |r| > {threshold}")
        
        return df_pairs
    
    def run_full_analysis(self):
        """
        完全な相関分析を実行
        """
        print("\n" + "="*60)
        print("         Joint Error Correlation Analysis (11: Y-flip corrected)")
        print("="*60)
        
        # オプションA: θの相関
        corr_theta = self.compute_option_a_theta()
        self.save_correlation_matrix(corr_theta, 'theta')
        self.plot_heatmap(corr_theta, 
                         'Joint Error Correlation (theta - XY Plane)', 
                         'heatmap_theta')
        
        # オプションA: ψの相関
        corr_psi = self.compute_option_a_psi()
        self.save_correlation_matrix(corr_psi, 'psi')
        self.plot_heatmap(corr_psi, 
                         'Joint Error Correlation (psi - XZ Plane)', 
                         'heatmap_psi')
        
        # オプションC: 3D誤差ノルムの相関
        corr_3d = self.compute_option_c_3d_norm()
        self.save_correlation_matrix(corr_3d, '3d_norm')
        self.plot_heatmap(corr_3d, 
                         'Joint Error Correlation (3D Norm)', 
                         'heatmap_3d_norm')
        
        # 主要関節のみ抽出してプロット
        print("\n=== Extracting important joints ===")
        
        corr_theta_important = self.extract_important_joints(corr_theta)
        self.plot_heatmap(corr_theta_important, 
                         'Joint Error Correlation (theta - Important Joints Only)', 
                         'heatmap_theta_important')
        
        corr_psi_important = self.extract_important_joints(corr_psi)
        self.plot_heatmap(corr_psi_important, 
                         'Joint Error Correlation (psi - Important Joints Only)', 
                         'heatmap_psi_important')
        
        corr_3d_important = self.extract_important_joints(corr_3d)
        self.plot_heatmap(corr_3d_important, 
                         'Joint Error Correlation (3D Norm - Important Joints Only)', 
                         'heatmap_3d_norm_important')
        
        # 高相関ペアの分析
        print("\n" + "="*60)
        print("         High Correlation Pairs Analysis")
        print("="*60)
        
        print("\n[theta (XY Plane)]")
        pairs_theta = self.analyze_high_correlations(corr_theta, threshold=0.7)
        if len(pairs_theta) > 0:
            pairs_theta.to_csv(self.output_dir / 'high_correlation_pairs_theta.csv', index=False)
        
        print("\n[psi (XZ Plane)]")
        pairs_psi = self.analyze_high_correlations(corr_psi, threshold=0.7)
        if len(pairs_psi) > 0:
            pairs_psi.to_csv(self.output_dir / 'high_correlation_pairs_psi.csv', index=False)
        
        print("\n[3D Norm]")
        pairs_3d = self.analyze_high_correlations(corr_3d, threshold=0.7)
        if len(pairs_3d) > 0:
            pairs_3d.to_csv(self.output_dir / 'high_correlation_pairs_3d_norm.csv', index=False)
        
        print("\n" + "="*60)
        print("         Analysis Complete!")
        print("="*60)
        print(f"\nResults saved to: {self.output_dir.absolute()}")
        print("\nGenerated files:")
        print("  - correlation_matrix_theta.csv")
        print("  - correlation_matrix_psi.csv")
        print("  - correlation_matrix_3d_norm.csv")
        print("  - heatmap_*.png (6 heatmap visualizations)")
        print("  - high_correlation_pairs_*.csv (if any found)")


def main():
    """メイン実行"""
    # 詳細結果CSVのパス（11の出力）
    detailed_csv = config.OUTPUT_DIR / "processed_data" / "detailed_results.csv"
    
    # 分析器を初期化
    analyzer = CorrelationAnalyzer(detailed_csv)
    
    # 完全な分析を実行
    analyzer.run_full_analysis()


if __name__ == '__main__':
    main()
