import os
import glob
import json
import zipfile
import streamlit as st
import qrcode


def clear_temp_folder(folder_path):
    file_list = glob.glob(os.path.join(folder_path, "*"))
    for file_path in file_list:
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                os.rmdir(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")

def load_settings(file):
    with open(file) as f:
        config = json.load(f)
    for k, v in config.items():
        st.session_state[k] = v

def load_ui_config(file):
    with open(file) as f:
        config = json.load(f)
    for k, v in config.items():
        if k not in st.session_state:
            st.session_state[k] = v

def create_zip(zip_path, filelist):
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in filelist:
            zipf.write(file, os.path.basename(file))

def export_settings(export_data, export_path):
    with open(export_path, mode='w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

def generate_qr(raw_text, size, border):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=size, border=border)
    qr.add_data(raw_text)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    return qr_image