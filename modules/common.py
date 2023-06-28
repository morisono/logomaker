import os
import json
import zipfile
import streamlit as st


def load_ui_config():
    with open('ui-config.json') as f:
        config = json.load(f)
    for k, v in config.items():
        st.session_state[k] = v


def create_zip(zip_path, filelist):
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in filelist:
            zipf.write(file, zip_path)
    return zip_path


def export_settings(export_data, export_path):
    with open(export_path, mode='w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
