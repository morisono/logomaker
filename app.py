import os
import glob
import datetime
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import tempfile
import matplotlib.font_manager as fm
import uuid
from modules.common import load_settings, load_ui_config, create_zip, export_settings, generate_qr, clear_temp_folder
from modules.ui import hide_ft_style


load_ui_config()
load_settings()
st.set_page_config(
    page_title=st.session_state['page_title'],
    page_icon=st.session_state['page_icon'],
    layout=st.session_state['layout'],
    initial_sidebar_state='auto')
hide_ft_style()


def generate_images(temp_path, draw_settings, **params):
    def process_logo(image):
        for lx, ly, lz, logo_file in zip(params['font_x'], params['font_y'], params['font_z'], params['logo_path']):
            logo_image = Image.open(logo_file).convert("RGBA")
            logo_w, logo_h = logo_image.size
            resized_logo_w = int(logo_w * lz)
            resized_logo_h = int(logo_h * lz)
            resized_logo = logo_image.resize((resized_logo_w, resized_logo_h))
            image.paste(resized_logo, (lx, ly), mask=resized_logo)
            return image

    def process_image(image):
        for word, px, py, f, fs, sc, sw in zip(words, params['font_x'], params['font_y'], params['font'], params['font_z'], params['stroke_fill'], params['stroke_width']):

            font = ImageFont.truetype(f, fs)
            text_bbox = draw.textbbox((0, 0), word, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = (params['width'] - text_width) * 0.5 + px
            text_y = (params['height'] - text_height) * 0.5 + py

            draw.text((text_x, text_y),
                        text=word, stroke_fill=sc, stroke_width=sw, fill=fc, font=font, anchor='lm')
        return image

    def process_qr(image, qr_text):
        for qr in qr_text:
            qr_size = params['height'] * 0.01 if params['height'] < params['width'] else params['width'] * 0.01
            qr_border =  qr_size * 0.2
            qr_position = (int(params['width']-30*qr_size),  int(params['height']-30*qr_size))
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

    # os.makedirs(temp_path, exist_ok=True)
    # for words in params['wordlist']:
        # subfolder_path = os.path.join(temp_path, f"{words}")
        # os.makedirs(subfolder_path, exist_ok=True)

    # font_paths = fm.findSystemFonts()
    # fontlist = [os.path.splitext(os.path.basename(font_path))[0] for font_path in font_paths]
    for filename in os.listdir(params['font_path']):
        if filename.endswith(".ttf"):
            params['fontlist'].append(os.path.join(params['font_path'], filename))

    for i, words in enumerate(params['wordlist']):
        for j, word in enumerate(words):
            unique_key = str(uuid.uuid4())
            with draw_settings:
                params['font_x'].append(st.slider(f"Pad x : \"{word}\"", -500, 500, 0, 10, key=f'{unique_key}_font_x'))
                params['font_y'].append(st.slider(f"Pad y : \"{word}\"", -500, 500, 0, 10, key=f'{unique_key}_font_y'))
                params['font_z'].append(st.slider(f"Font size : \"{word}\"", 0, 800, 100, 8, key=f'{unique_key}_font_z'))
                params['font'].append(st.selectbox(f"Font : \"{word}\"", params['fontlist'], key=f'{unique_key}_font'))
                params['logo_z'].append(st.slider("Logo Zoom", 0.05, 4.0, 0.20, 0.01, key=f'{unique_key}_logo_z'))
                params['stroke_fill'].append(st.text_input(f"Stroke fill: \"{word}\"", "gray", key=f'{unique_key}_stroke_fill'))
                params['stroke_width'].append(st.slider(f"Stroke width: \"{word}\"", 0, 20, 0, key=f'{unique_key}_stroke_width'))
# TODO
    for colors in params['colorlist']:
        bc, fc = colors
        image = Image.new("RGBA", (params['width'], params['height']), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        for sh in params['shape']:
            if sh == "fill":
                draw.rectangle((0, 0, params['width'], params['height']), fill=bc)
            elif sh == "circle":
                params['r'] = 50
                params['cx'], params['cy'] = params['width'] * 0.5, params['height'] * 0.5
                draw.ellipse((params['cx'] - params['r'], params['cy'] - params['r'], params['cx'] + params['r'], params['cy'] + r), fill=bc, outline=None)
            elif sh == "roundrect":
                params['rx'], params['ry'] = 0, 0
                params['r'] = 20
                draw.rounded_rectangle((params['rx'], params['ry'], params['rx'] + params['width'], params['ry'] + params['h']), params['r'], fill=bc, outline=None)
            elif sh == "frame":
                params['margin'] = 20
                params['frame_width'] = 5
                draw.rectangle((params['margin'], params['margin'], params['width'] - params['margin'], params['height'] - params['margin']), fill=bc, outline=fc, width=frame_width)

            if params['logo_path']:
                with draw_settings:
                    params['logo_x'].append(st.slider(f"Logo x: \"{word}\"", -params['width'], params['width'], 0, 10, key=f'{unique_key}_logo_x'))
                    params['logo_y'].append(st.slider(f"Logo y: \"{word}\"", -params['height'], params['height'], 0, 10, key=f'{unique_key}_logo_y'))
                image = process_logo(image)
            image = process_image(image)

            if params['gen_qr']:
                image = process_qr(image, params['qr_text'])

            out_name = f"{len(params['filelist']):05d}{params['ext']}"
            temp_image_path = os.path.join(temp_path, out_name)
            # temp_image_path = os.path.join(subfolder_path, out_name)
            image.save(temp_image_path)
            params['filelist'].append(temp_image_path)

    if params['gen_gif']:
        images_path = temp_path
        # images_path = subfolder_path
        gif_path =  'output.gif'
        image = generate_gif(images_path, params['delay'], 0, gif_path)
        st.image(gif_path)

    if params['gen_preview']:
        params['preview_image'] = params['filelist']
    else:
        params['preview_image'].append(params['filelist'][0])


    if params['gen_gridview']:
        for idx in range(len(params['preview_image'])):
            img = params['preview_image'][idx]
            params['cols'][idx % params['grid_col']].image(img, caption=os.path.basename(img), use_column_width=True)
    else:
        for idx in range(len(params['preview_image'])):
            img = params['preview_image'][idx]
            st.image(img, caption=os.path.basename(img), use_column_width=True)


    return params['filelist']


def main():
    title = st.title("Logo Maker Web UI")

    settings = st.sidebar.title("Settings")
    input_settings = st.sidebar.expander("Input Settings")
    with input_settings:
        colorlist = st.session_state['colorlist']
        colors = st.text_area("Enter color list (split like c1;c2;.., newline for next)", value="\n".join([f"{arg1};{arg2}" for arg1, arg2 in colorlist]))
        colorlist = [tuple(line.split(';')) for line in colors.splitlines() if line.strip()]

        wordlist = st.session_state['wordlist']
        words = st.text_area("Enter word list (split like w1;w2;..,newline for next)", value="\n".join([f"{arg1};{arg2}" for arg1, arg2 in wordlist]))
        wordlist = [tuple(line.split(';')) for line in words.splitlines() if line.strip()]

    view_settings = st.sidebar.expander("View Settings")
    with view_settings:
        gen_preview = st.checkbox("Preview All")
        gen_gridview = st.checkbox("Grid View")
        grid_col = 1
        if gen_gridview:
            grid_col = st.slider("Grid Col",1,8,4)
    cols = st.columns(grid_col)

    draw_settings = st.sidebar.expander("Draw Settings")
    with draw_settings:
        size_preset = st.session_state['size_preset']
        size_selected = st.selectbox("Size Preset", list(size_preset.keys()))
        if size_selected:
            preset_size = size_preset[size_selected]
            w, h = preset_size
        w = st.slider("Width", 0, 2560, w, 8)
        h = st.slider("Height", 0, 2560, h, 8)

        shape = st.multiselect('Shape', ["fill", "circle", "roundrect", "frame"], default='fill')
        r, cx, cy, rx, ry, margin = 0,0,0,0,0,0
        if shape:
            if "circle" in shape:
                r = st.slider("Circle Radius", 1, 100, 50)
                cx = st.slider("Circle Center X", 0, w, int(w *0.5))
                cy = st.slider("Circle Center Y", 0, h, int(h *0.5))

            elif "roundrect" in shape:
                rx = st.slider("Round Rectangle X", 0, w, int(w *0.5))
                ry = st.slider("Round Rectangle Y", 0, h, int(h *0.5))

            elif "frame" in shape:
                margin = st.slider("Frame margin", 0, min(w, h)//2, m)

    insert_settings = st.sidebar.expander("Insert Settings")
    with insert_settings:
        # logo_path = 'images/logo'
        # for filename in os.listdir(logo_path):
        #     if filename.endswith(".png"):
        #         logolist.append(os.path.join(logo_path, filename))
        # logo = st.sidebar.selectbox("Logo", logolist)
        logo = st.file_uploader("Logo Image", accept_multiple_files=True)
        logo_path = logo if logo else [].append([])
        temp_path = tempfile.gettempdir()

        gen_qr = st.checkbox("QR")
        _qr_text = ""
        if gen_qr:
            _qr_text = st.text_area("QR text", "example.com")
        qr_text = [line for line in _qr_text.splitlines() if line.strip()]

        gen_gif = st.checkbox("GIF Animation")
        if gen_gif:
            delay = st.slider("Delay", 0, 5000, 0, 100)
        else:
            delay = 0

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    size = f"{w}x{h}"

    output_settings = st.sidebar.expander("Output Settings")
    with output_settings:
        ext = st.selectbox("File Format", st.session_state['ext'])

    params = {
        'gen_qr': gen_qr,
        'gen_gif': gen_gif,
        'gen_preview': gen_preview,
        'gen_gridview':gen_gridview,
        'logo_path':st.session_state['logo_path'],
        'filelist': st.session_state['filelist'],
        'colorlist': colorlist,
        'wordlist': wordlist,
        'logolist': st.session_state['logolist'],
        'ext': ext,
        'size_preset': st.session_state['size_preset'],
        'timestamp': timestamp,
        'size': size,
        'width': w,
        'height': h,
        'shape': shape,
        'font': st.session_state['font'],
        'font_x': st.session_state['font_x'],
        'font_y': st.session_state['font_y'],
        'font_z': st.session_state['font_z'],
        'logo_x': st.session_state['logo_x'],
        'logo_y': st.session_state['logo_y'],
        'logo_z': st.session_state['logo_z'],
        'stroke_fill': st.session_state['stroke_fill'],
        'stroke_width': st.session_state['stroke_width'],
        'grid_col': grid_col,
        'cols': cols,
        'r': r,
        'cx': cx,
        'cy': cy,
        'rx': rx,
        'ry': ry,
        'margin': margin,
        'qr_text': qr_text,
        'delay': delay,
        'font_path': st.session_state['font_path'],
        'fontlist': st.session_state['fontlist'],
        'preview_image': st.session_state['preview_image'],
    }

    filelist = generate_images(temp_path, draw_settings, **params)

    with output_settings:
        zip_fname = st.text_input("Images filename","images.zip")
        zip_path = create_zip(zip_fname, filelist)
        st.download_button("Download images(.zip)", data=zip_path, file_name=zip_fname)

        setting_fname = st.text_input("Settings filename",'settings.json')
        # export_settings(params, setting_fname)
        st.download_button("Export settings (.json)", data=open
        (setting_fname, 'rb').read(), file_name=setting_fname)



    # clear_temp_folder(temp_path)

if __name__ == "__main__":
    main()