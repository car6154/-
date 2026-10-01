# scripts/merge_ledger.py
"""
Git Custom Merge Driver for J-PRO Ledger and JSON DBs.
Automatically merges records between Desktop and Laptop without conflicts.
"""
import sys
import os
import json
import pandas as pd

def merge_csv(base_path, local_path, remote_path):
    try:
        df_local = pd.read_csv(local_path, encoding='utf-8-sig') if os.path.exists(local_path) else pd.DataFrame()
    except Exception:
        try:
            df_local = pd.read_csv(local_path, encoding='cp949') if os.path.exists(local_path) else pd.DataFrame()
        except Exception:
            df_local = pd.DataFrame()

    try:
        df_remote = pd.read_csv(remote_path, encoding='utf-8-sig') if os.path.exists(remote_path) else pd.DataFrame()
    except Exception:
        try:
            df_remote = pd.read_csv(remote_path, encoding='cp949') if os.path.exists(remote_path) else pd.DataFrame()
        except Exception:
            df_remote = pd.DataFrame()

    if df_local.empty and df_remote.empty:
        return True

    # Combine both
    combined = pd.concat([df_local, df_remote], ignore_index=True)
    if '차량번호' in combined.columns:
        combined['차량번호'] = combined['차량번호'].astype(str).str.strip()
        # Deduplicate keeping the one with most non-null values or last
        combined = combined.drop_duplicates(subset=['차량번호'], keep='last')

    if '등록일' in combined.columns:
        try:
            combined = combined.sort_values(by='등록일', ascending=False)
        except Exception:
            pass

    combined.to_csv(local_path, index=False, encoding='utf-8-sig')
    return True

def merge_json(base_path, local_path, remote_path):
    data_local = {}
    data_remote = {}
    if os.path.exists(local_path):
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                data_local = json.load(f)
        except Exception:
            pass

    if os.path.exists(remote_path):
        try:
            with open(remote_path, 'r', encoding='utf-8') as f:
                data_remote = json.load(f)
        except Exception:
            pass

    # Merge dictionaries
    if isinstance(data_local, dict) and isinstance(data_remote, dict):
        merged = {**data_remote, **data_local}
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        return True
    return False

if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(0)

    base = sys.argv[1]
    local = sys.argv[2]
    remote = sys.argv[3]

    if local.endswith('.csv') or remote.endswith('.csv'):
        merge_csv(base, local, remote)
    elif local.endswith('.json') or remote.endswith('.json'):
        merge_json(base, local, remote)

    sys.exit(0)
