import os
import datetime
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import tempfile
import matplotlib.font_manager as fm

from modules.common import load_ui_config, create_zip, export_settings
from modules.ui import hide_ft_style


load_ui_config()
st.set_page_config(
    page_title=st.session_state['page_title'],
    page_icon=st.session_state['page_icon'],
    layout=st.session_state['layout'],
    initial_sidebar_state='auto')
hide_ft_style()


def generate_images(colorlist, wordlist, gf, ext, w, h, gpx, gpy, gfs, temp_path, logo_path, global_settings):
    filelist = []
    os.makedirs(temp_path, exist_ok=True)
    # font_paths = fm.findSystemFonts()
    # fontlist = [os.path.splitext(os.path.basename(font_path))[0] for font_path in font_paths]
    fontlist = []
    font_path = 'fonts'
    for filename in os.listdir(font_path):
        if filename.endswith(".ttf"):
            fontlist.append(os.path.join(font_path, filename))

    def process_image(image, colors, words, gpx, gpy, gf, gfs):
        for word, px, py, f, fs in zip(words, gpx, gpy, gf, gfs):
            with st.expander(f"Settings: {word}"):
                stc = st.text_input("stroke fill", "gray", key=f'{len(filelist):05d}_{colors}_{word}_stc')
                stw = st.slider("stroke width", 0, 20, 0, key=f'{len(filelist):05d}_{colors}_{word}_stw')

            font = ImageFont.truetype(f, fs)
            text_bbox = draw.textbbox((0, 0), word, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = (w - text_width) * 0.5 + px
            text_y = (h - text_height) * 0.5 + py

            st.write(word)
            draw.text((text_x, text_y),
                    text=word, stroke_fill=stc, stroke_width=stw, fill=fc, font=font, anchor='lt')

        return image

    if logo_path:
        for logo_file in logo_path:
            with global_settings:
                logo_x = st.slider("Logo x", -w, w, 0, 10, key=f'{logo_file}_x')
                logo_y = st.slider("Logo y", -h, h, 0, 10, key=f'{logo_file}_y')
                logo_z = st.slider("Logo Zoom", 0.05, 20.0, 0.20, 0.01, key=f'{logo_file}_z')

            logo_image = Image.open(logo_file).convert("RGBA")

            for words in wordlist:
                subfolder_path = os.path.join(temp_path, f"{words}")
                os.makedirs(subfolder_path, exist_ok=True)

                # with st.expander(f"Settings: {words}"):
                #     fs = st.slider("Fontsize", 0, 1256, gfs, 8, key=f'{len(filelist):05d}_{words}_fs')

                logo_w, logo_h = logo_image.size
                resized_logo_w = int(logo_w * logo_z)
                resized_logo_h = int(logo_h * logo_z)
                resized_logo = logo_image.resize((resized_logo_w, resized_logo_h))
                image.paste(resized_logo, (logo_x, logo_y), mask=resized_logo)

                image = process_image(image, colors, words, gpx, gpy, gf, gfs)
                st.image(image, caption=logo_file.name, use_column_width=True)
                image.save(temp_image_path)
                filelist.append(temp_image_path)

    else:
        for words in wordlist:
            subfolder_path = os.path.join(temp_path, f"{words}")
            os.makedirs(subfolder_path, exist_ok=True)

            for word in words:
                with global_settings:
                    gpx.append(st.slider(f"Pad x : {word}", -500, 500, 0, 10, key=f'{len(filelist):05d}_{word}_gpx'))
                    gpy.append(st.slider(f"Pad y : {word}", -500, 500, 100, 10, key=f'{len(filelist):05d}_{word}_gpy'))
                    gfs.append(st.slider("Font size : {word}", 0, 2560, 100, 8, key=f'{len(filelist):05d}_{word}_gfs'))
                    gf.append(st.sidebar.selectbox("Font : {word}", fontlist, key=f'{len(filelist):05d}_{word}_gf'))

            # with st.expander(f"Settings: {words}"):
            #     fs = st.slider("Fontsize", 0, 1256, gfs, 8, key=f'{len(filelist):05d}_{words}_fs')
            for colors in colorlist:
                bc, fc = colors
                image = Image.new("RGB", (w, h), color=bc)
                draw = ImageDraw.Draw(image)
                image = process_image(image, colors, words, gpx, gpy, gf, gfs)
                out_name = f"{len(filelist):05d}{ext}"
                temp_image_path = os.path.join(subfolder_path, out_name)
                image.save(temp_image_path)
                st.image(image, caption=os.path.basename(temp_image_path), use_column_width=True)
                filelist.append(temp_image_path)

    return filelist


def main():
    _colorlist = [
        ("black", "white"),
        ("white", "red"),
        ("yellow", "black"),
    ]
    _wordlist = [
        ("Designed by", "m.s."),
    ]

    st.title("Logo Maker Web UI")
    st.sidebar.title("Settings")
    colorlist_input = st.sidebar.text_area("Enter color list (split like c1;c2;..,newline for next)", value="\n".join([f"{arg1};{arg2}" for arg1, arg2 in _colorlist]))
    colorlist = [tuple(line.split(';')) for line in colorlist_input.splitlines() if line.strip()]

    wordlist_input = st.sidebar.text_area("Enter word list (split like w1;w2;..,newline for next)", value="\n".join([f"{arg1};{arg2}" for arg1, arg2 in _wordlist]))
    wordlist = [tuple(line.split(';')) for line in wordlist_input.splitlines() if line.strip()]


    size_preset = {
        "2:1 (1024, 512)": (1024, 512),
        "Square (1024, 1024)": (1024, 1024),
        "WQHD (2560, 1440)": (2560, 1440),
        "FHD (1920, 1080)": (1920, 1080),
        "HD (1280, 720)": (1280, 720),
        "4:3 (1280, 960)": (1280, 960),
        "2:1 (1280, 640)": (1280, 640),
        "3:2 (1440, 960)": (1440, 960),
        "FHD vert (1080, 1920)": (1080, 1920),
        "HD vert (720, 1280)": (720, 1280),
        "3:4 (960, 1280)": (960, 1280),
        "1:2 (640, 1280)": (640, 1280),
        "2:3 960, 1440)": (960, 1440),
        "Banner (1500, 500)": (1500, 500),
    }
    size_selected = st.sidebar.selectbox("Size Preset", list(size_preset.keys()))
    if size_selected:
        preset_size = size_preset[size_selected]
        w, h = preset_size

    global_settings = st.sidebar.expander("Global Settings")
    with global_settings:
        w = st.slider("Width", 0, 2560, w, 8)
        h = st.slider("Height", 0, 2560, h, 8)

    logolist = []
    logo_path = 'images/logo'
    for filename in os.listdir(logo_path):
        if filename.endswith(".png"):
            logolist.append(os.path.join(logo_path, filename))
    logo = st.sidebar.selectbox("Logo", logolist)
    logo = st.sidebar.file_uploader("Logo Image", accept_multiple_files=True)
    logo_path = logo if logo else [].append(logolist)
    temp_path = tempfile.gettempdir()

    # exts = Image.registered_extensions()
    # ext = st.sidebar.selectbox("File Format", {ex for ex, f in exts.items() if f in Image.OPEN})
    ext = st.sidebar.selectbox("File Format", [".png",".jpg",".tiff"])

    # generate = st.sidebar.button("Generate GIF")
    # if generate:


    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    size = f"{w}x{h}"
    gpx, gpy, gf, gfs = [],[],[],[]

    export_data = {
        'colorlist': colorlist,
        'wordlist': wordlist,
        'logolist': logolist,
        'current_time': current_time,
        'size': size,
        'width': w,
        'height': h,
        'font': gf,
        'default_x': gpx,
        'default_y': gpy,
        'default_fontsize': gfs,
    }
    filelist = generate_images(colorlist, wordlist, gf, ext, w, h, gpx, gpy, gfs, temp_path, logo_path, global_settings)

    export_path = os.path.join(temp_path, 'settings.json')
    export_settings(export_data, export_path)
    st.sidebar.download_button("Export settings (.json)", data=open
    (export_path, 'rb').read(), file_name=export_path)

    save_as_path = "outputs.zip"
    zip_path = create_zip(save_as_path, filelist)
    st.sidebar.download_button("Download (.zip)", data=zip_path, file_name=save_as_path)


if __name__ == "__main__":
    main()
