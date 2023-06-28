import os
import glob
import datetime
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import tempfile
import matplotlib.font_manager as fm

from modules.common import load_ui_config, create_zip, export_settings, generate_qr, clear_temp_folder
from modules.ui import hide_ft_style


load_ui_config()
st.set_page_config(
    page_title=st.session_state['page_title'],
    page_icon=st.session_state['page_icon'],
    layout=st.session_state['layout'],
    initial_sidebar_state='auto')
hide_ft_style()


def generate_images(colorlist, wordlist, gf, ext, w, h, gpx, gpy, gfs, glx, gly, glz, stc, stw, temp_path, logo_path, gen_qr, gen_gif, delay,  qr_text, global_settings, preview_button, gridview_button, grid_col, cols):
    def process_logo(image, lx, ly, lz):
        for lx, ly, lz, logo_file in zip(glx, gly, glz, logo_path):
            logo_image = Image.open(logo_file).convert("RGBA")
            logo_w, logo_h = logo_image.size
            resized_logo_w = int(logo_w * lz)
            resized_logo_h = int(logo_h * lz)
            resized_logo = logo_image.resize((resized_logo_w, resized_logo_h))
            image.paste(resized_logo, (lx, ly), mask=resized_logo)
            return image

    def process_image(image, words, gpx, gpy, gf, gfs, stc, stw):
        for word, px, py, f, fs, sc, sw in zip(words, gpx, gpy, gf, gfs, stc, stw):

            font = ImageFont.truetype(f, fs)
            text_bbox = draw.textbbox((0, 0), word, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = (w - text_width) * 0.5 + px
            text_y = (h - text_height) * 0.5 + py

            draw.text((text_x, text_y),
                    text=word, stroke_fill=sc, stroke_width=sw, fill=fc, font=font, anchor='lm')
        return image

    def process_qr(image, qr_text):
        for qr in qr_text:
            qr_size = h * 0.01 if h < w else w * 0.01
            qr_border =  qr_size * 0.2
            qr_position = (int(w-30*qr_size),  int(h-30*qr_size))
            qr_image = generate_qr(qr, qr_size, qr_border)
            image.paste(qr_image, qr_position)
        return image

    def generate_gif(image_path, delay, loop, output_path):
        images = glob.glob(os.path.join(image_path, "*"))
        frames = []

        for image_file in images:
            img = Image.open(image_file)
            frames.append(img)

        frames[0].save(output_path, format="GIF", append_images=frames[1:], save_all=True, duration=delay, loop=loop)

        return image

    filelist, fontlist, preview_image = [],[],[]
    os.makedirs(temp_path, exist_ok=True)
    for words in wordlist:
        subfolder_path = os.path.join(temp_path, f"{words}")
        os.makedirs(subfolder_path, exist_ok=True)

    # font_paths = fm.findSystemFonts()
    # fontlist = [os.path.splitext(os.path.basename(font_path))[0] for font_path in font_paths]
    font_path = 'fonts'
    for filename in os.listdir(font_path):
        if filename.endswith(".ttf"):
            fontlist.append(os.path.join(font_path, filename))

    for words in wordlist:

        for word in words:
            with global_settings:
                gpx.append(st.slider(f"Pad x : \"{word}\"", -500, 500, 0, 10, key=f'{len(filelist):05d}_{word}_gpx'))
                gpy.append(st.slider(f"Pad y : \"{word}\"", -500, 500, 0, 10, key=f'{len(filelist):05d}_{word}_gpy'))
                gfs.append(st.slider(f"Font size : \"{word}\"", 0, 800, 100, 8, key=f'{len(filelist):05d}_{word}_gfs'))
                gf.append(st.sidebar.selectbox(f"Font : \"{word}\"", fontlist, key=f'{len(filelist):05d}_{word}_gf'))
                glz.append(st.slider("Logo Zoom", 0.05, 4.0, 0.20, 0.01, key=f'{len(filelist):05d}_{word}_glz'))
                stc.append(st.text_input(f"Stroke fill: \"{word}\"", "gray", key=f'{len(filelist):05d}_{word}_stc'))
                stw.append(st.slider(f"Stroke width: \"{word}\"", 0, 20, 0, key=f'{len(filelist):05d}_{word}_stw'))

    for colors in colorlist:
        bc, fc = colors
        image = Image.new("RGB", (w, h), color=bc)
        draw = ImageDraw.Draw(image)

        if logo_path:
            with global_settings:
                glx.append(st.slider(f"Logo x: \"{word}\"", -w, w, 0, 10, key=f'{len(filelist):05d}_{word}_glx'))
                gly.append(st.slider(f"Logo y: \"{word}\"", -h, h, 0, 10, key=f'{len(filelist):05d}_{word}_gly'))
            image = process_logo(image, glx, gly, glz)
        image = process_image(image, words, gpx, gpy, gf, gfs, stc, stw)

        if gen_qr:
            image = process_qr(image, qr_text)

        out_name = f"{len(filelist):05d}{ext}"
        temp_image_path = os.path.join(subfolder_path, out_name)
        image.save(temp_image_path)
        filelist.append(temp_image_path)

    if gen_gif:
        images_path = subfolder_path
        gif_path =  'output.gif'
        image = generate_gif(images_path, delay, 0, gif_path)
        st.image(gif_path)

    if preview_button:
        preview_image = filelist
    else:
        preview_image.append(filelist[0])

    if gridview_button:
        for idx, img in enumerate(preview_image):
            cols[idx % grid_col].image(img, caption=os.path.basename(preview_image[idx]), use_column_width=True)
    else:
        for idx, img in enumerate(preview_image):
            st.image(img, caption=os.path.basename(preview_image[idx]), use_column_width=True)


    return filelist


def main():
    _colorlist = [
        ("black", "white"),
        ("cyan", "magenta"),
        ("red", "blue"),
        ("green", "yellow")
    ]
    _wordlist = [
        ("Designed by", "m.s."),
    ]

    st.title("Logo Maker Web UI")
    preview_button = st.sidebar.checkbox("Preview All")
    gridview_button = st.sidebar.checkbox("Grid View")
    # select_shape = st.sidebar.multiselect("Shape", ["Circle","RoundRect"])
    if gridview_button:
        grid_col = st.sidebar.slider("Grid Col",1,8,2)

    else:
        grid_col = 1
    cols = st.columns(grid_col)

    st.sidebar.title("Settings")
    _colorlist = st.sidebar.text_area("Enter color list (split like c1;c2;..,newline for next)", value="\n".join([f"{arg1};{arg2}" for arg1, arg2 in _colorlist]))
    colorlist = [tuple(line.split(';')) for line in _colorlist.splitlines() if line.strip()]

    _wordlist = st.sidebar.text_area("Enter word list (split like w1;w2;..,newline for next)", value="\n".join([f"{arg1};{arg2}" for arg1, arg2 in _wordlist]))
    wordlist = [tuple(line.split(';')) for line in _wordlist.splitlines() if line.strip()]


    size_preset = {
        "Banner (1500, 500)": (1500, 500),
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
    # logo_path = 'images/logo'
    # for filename in os.listdir(logo_path):
    #     if filename.endswith(".png"):
    #         logolist.append(os.path.join(logo_path, filename))
    # logo = st.sidebar.selectbox("Logo", logolist)
    logo = st.sidebar.file_uploader("Logo Image", accept_multiple_files=True)
    logo_path = logo if logo else [].append(logolist)
    temp_path = tempfile.gettempdir()

    gen_qr = st.sidebar.checkbox("QR")
    if gen_qr:
        _qr_text = st.sidebar.text_area("QR text", "example.com")
    else:
        _qr_text = ""
    qr_text = [line for line in _qr_text.splitlines() if line.strip()]

    gen_gif = st.sidebar.checkbox("GIF Animation")
    if gen_gif:
        delay = st.sidebar.slider("Delay", 0, 5000, 0, 100)
    else:
        delay = 0

    # exts = Image.registered_extensions()
    # ext = st.sidebar.selectbox("File Format", {ex for ex, f in exts.items() if f in Image.OPEN})
    ext = st.sidebar.selectbox("File Format", [".png",".jpg",".tiff", ".gif", ".eps",".ico", ".webp"])

    # generate = st.sidebar.button("Generate GIF")
    # if generate:


    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    size = f"{w}x{h}"
    gpx, gpy, gf, gfs, glx, gly, glz, stc, stw = [],[],[],[],[],[],[],[],[]
    export_data = {
        'timestamp': timestamp,
        'size': size,
        'width': w,
        'height': h,
        'font': gf,
        'default_x': gpx,
        'default_y': gpy,
        'default_fontsize': gfs,
        'default_logo_x': glx,
        'default_logo_y': gly,
        'default_logo_zoom': glz,
        'default_stroke_color': stc,
        'default_stroke_width': stw,
        'colorlist': colorlist,
        'wordlist': wordlist,
        'logolist': logolist,
    }
    filelist = generate_images(colorlist, wordlist, gf, ext, w, h, gpx, gpy, gfs, glx, gly, glz, stc, stw, temp_path, logo_path, gen_qr, gen_gif, delay,  qr_text, global_settings, preview_button, gridview_button, grid_col, cols)

    export_path = os.path.join(temp_path, 'settings.json')
    export_settings(export_data, export_path)
    st.sidebar.download_button("Export settings (.json)", data=open
    (export_path, 'rb').read(), file_name=export_path)

    save_as_path = "outputs.zip"
    zip_path = create_zip(save_as_path, filelist)
    st.sidebar.download_button("Download (.zip)", data=zip_path, file_name=save_as_path)

    # clear_temp_folder(temp_path)

if __name__ == "__main__":
    main()