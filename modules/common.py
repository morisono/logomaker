import os
import json
import zipfile
import streamlit as st
import qrcode
import shutil


def clear_temp_folder(temp_folder_path):
    for filename in os.listdir(temp_folder_path):
        file_path = os.path.join(temp_folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")

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

def generate_qr(raw_text, size, border):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=size, border=border)
    qr.add_data(raw_text)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    return qr_image