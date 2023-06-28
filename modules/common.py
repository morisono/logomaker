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
            arcname = os.path.join(os.path.dirname(file), os.path.basename(file))
            zipf.write(file, arcname)
    return zip_path


def export_settings(export_data):
    with open('settings.json', mode='w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
