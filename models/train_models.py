"""
Treinamento e Serialização de Modelos de IA - Sprint 4 (SEFIN Palmas / UFT BIINAR)
Equipe: Hyag, Ludmylla, Maiara, Sofia e Vitória
Coordenação: Prof. Dr. David Nadler Prata

Modelos:
- Baseline 1: Regressão Logística
- Baseline 2: Árvore de Decisão
- Modelo Principal: Random Forest (comitê de árvores calibrado)
- Split Temporal rigoroso (Treino até 2022, Validação 2023, Teste 2024) para evitar Data Leakage.
"""

import os
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix
)

# Import do gerador de dados se necessário
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
sys.path.append(os.path.join(project_dir, "data"))
from generate_synthetic_data import generate_sefin_data

def train_and_export_models():
    print("Iniciando pipeline de modelagem e serialização...")
    
    # 1. Carregamento / Geração dos Dados
    csv_path = os.path.join(project_dir, "data", "divida_ativa_palmas.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
    else:
        df = generate_sefin_data(n_samples=2500)
        df.to_csv(csv_path, index=False, encoding="utf-8")
        print(f"Dataset salvo em {csv_path}")

    # Variável Alvo para Recuperabilidade Efetiva (1 se Faixa Alta ou Média com sucesso, 0 se Inadimplência Crônica/Baixa)
    # Target binário: Recuperável em até 12 meses (Score >= 50)
    df["target_recuperavel"] = (df["score_recuperabilidade"] >= 50.0).astype(int)

    # 2. Definição de Features
    num_features = ["tempo_inscricao_meses", "valor_principal", "juros_multas", "valor_total_divida", "quantidade_debitos", "historico_parcelamentos"]
    cat_features = ["tributo", "tipo_pessoa", "execucao_ajuizada", "possui_bens", "contato_atualizado", "faixa_renda", "regiao"]

    # 3. Split Temporal (E1 - Metodologia anti-leakage)
    train_mask = df["ano_inscricao"] <= 2022
    val_mask = df["ano_inscricao"] == 2023
    test_mask = df["ano_inscricao"] >= 2024

    X_train = df.loc[train_mask, num_features + cat_features]
    y_train = df.loc[train_mask, "target_recuperavel"]

    X_val = df.loc[val_mask, num_features + cat_features]
    y_val = df.loc[val_mask, "target_recuperavel"]

    X_test = df.loc[test_mask, num_features + cat_features]
    y_test = df.loc[test_mask, "target_recuperavel"]

    print(f"Divisão Temporal -> Treino: {len(X_train)} | Validação: {len(X_val)} | Teste: {len(X_test)}")

    # 4. Pipeline de Pré-processamento
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_features)
        ]
    )

    # 5. Treinamento dos Modelos
    # Baseline 1: Regressão Logística
    pipe_lr = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", LogisticRegression(max_iter=1000, random_state=42))
    ])
    pipe_lr.fit(X_train, y_train)

    # Baseline 2: Árvore de Decisão
    pipe_dt = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", DecisionTreeClassifier(max_depth=6, random_state=42))
    ])
    pipe_dt.fit(X_train, y_train)

    # Modelo Final Principal: Random Forest
    pipe_rf = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(n_estimators=150, max_depth=10, min_samples_split=5, random_state=42, n_jobs=1))
    ])
    pipe_rf.fit(X_train, y_train)

    # Modelo Principal 2: XGBoost (Gradient Boosting)
    pipe_xgb = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", XGBClassifier(n_estimators=120, max_depth=5, learning_rate=0.08, random_state=42, eval_metric="logloss"))
    ])
    pipe_xgb.fit(X_train, y_train)

    # 6. Avaliação no Conjunto de Teste Temporal (E2 & E3)
    models_dict = {
        "Regressão Logística (Baseline)": pipe_lr,
        "Árvore de Decisão (Baseline)": pipe_dt,
        "Random Forest (Modelo Final Campeão)": pipe_rf,
        "XGBoost (Gradient Boosting)": pipe_xgb
    }

    metrics_report = {}
    for name, model in models_dict.items():
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

        metrics_report[name] = {
            "acuracia": round(float(accuracy_score(y_test, y_pred)), 4),
            "precisao": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
            "f1_score": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
            "roc_auc": round(float(roc_auc_score(y_test, y_prob)), 4),
            "matriz_confusao": confusion_matrix(y_test, y_pred).tolist()
        }

    # 7. Serialização dos Modelos (.joblib) no diretório /models
    models_dir = os.path.join(project_dir, "models")
    os.makedirs(models_dir, exist_ok=True)

    rf_path = os.path.join(models_dir, "random_forest_debt_model.joblib")
    lr_path = os.path.join(models_dir, "logistic_regression_baseline.joblib")
    dt_path = os.path.join(models_dir, "decision_tree_baseline.joblib")
    xgb_path = os.path.join(models_dir, "xgboost_debt_model.joblib")
    metrics_path = os.path.join(models_dir, "model_metrics.json")

    def _safe_dump(model_obj, path):
        tmp_path = path + ".tmp"
        joblib.dump(model_obj, tmp_path, compress=3)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
        os.replace(tmp_path, path)

    _safe_dump(pipe_rf, rf_path)
    _safe_dump(pipe_lr, lr_path)
    _safe_dump(pipe_dt, dt_path)
    _safe_dump(pipe_xgb, xgb_path)

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_report, f, indent=4, ensure_ascii=False)

    print(f"Modelos serializados com sucesso:")
    print(f" - Random Forest: {rf_path}")
    print(f" - Logistic Regression: {lr_path}")
    print(f" - Decision Tree: {dt_path}")
    print(f" - Métricas de Teste salvas em: {metrics_path}")

    return metrics_report

if __name__ == "__main__":
    train_and_export_models()
