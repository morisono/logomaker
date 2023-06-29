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


def generate_images(state, draw_settings):
    def process_logo(image):
        for lx, ly, lz, logo_file in zip(state['font_x'], state['font_y'], state['font_z'], state['logo_path']):
            logo_image = Image.open(logo_file).convert("RGBA")
            logo_w, logo_h = logo_image.size
            resized_logo_w = int(logo_w * lz)
            resized_logo_h = int(logo_h * lz)
            resized_logo = logo_image.resize((resized_logo_w, resized_logo_h))
            image.paste(resized_logo, (lx, ly), mask=resized_logo)
            return image

    def process_image(image):
        for word, px, py, f, fs, sc, sw in zip(words, state['font_x'], state['font_y'], state['font'], state['font_z'], state['stroke_fill'], state['stroke_width']):

            font = ImageFont.truetype(f, fs)
            text_bbox = draw.textbbox((0, 0), word, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = (state['canvas_w'] - text_width) * 0.5 + px
            text_y = (state['canvas_h'] - text_height) * 0.5 + py

            draw.text((text_x, text_y),
                        text=word, stroke_fill=sc, stroke_width=sw, fill=fc, font=font, anchor='lm')
        return image

    def process_qr(image, qr_text):
        for qr in qr_text:
            qr_size = state['canvas_h'] * 0.01 if state['canvas_h'] < state['canvas_w'] else state['canvas_w'] * 0.01
            qr_border =  qr_size * 0.2
            qr_position = (int(state['canvas_w']-30*qr_size),  int(state['canvas_h']-30*qr_size))
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
    # for words in state['wordlist']:
        # subfolder_path = os.path.join(temp_path, f"{words}")
        # os.makedirs(subfolder_path, exist_ok=True)

    # font_paths = fm.findSystemFonts()
    # fontlist = [os.path.splitext(os.path.basename(font_path))[0] for font_path in font_paths]
    for filename in os.listdir(state['font_path']):
        if filename.endswith(".ttf"):
            state['fontlist'].append(os.path.join(state['font_path'], filename))

    for i, words in enumerate(state['wordlist']):
        for j, word in enumerate(words):
            unique_key = str(uuid.uuid4())
            with draw_settings:
                state['font_x'].append(st.slider(f"Pad x : \"{word}\"", -500, 500, 0, 10, key=f'{unique_key}_font_x'))
                state['font_y'].append(st.slider(f"Pad y : \"{word}\"", -500, 500, 0, 10, key=f'{unique_key}_font_y'))
                state['font_z'].append(st.slider(f"Font size : \"{word}\"", 0, 800, 100, 8, key=f'{unique_key}_font_z'))
                state['font'].append(st.selectbox(f"Font : \"{word}\"", state['fontlist'], key=f'{unique_key}_font'))
                state['logo_z'].append(st.slider("Logo Zoom", 0.05, 4.0, 0.20, 0.01, key=f'{unique_key}_logo_z'))
                state['stroke_fill'].append(st.text_input(f"Stroke fill: \"{word}\"", "gray", key=f'{unique_key}_stroke_fill'))
                state['stroke_width'].append(st.slider(f"Stroke width: \"{word}\"", 0, 20, 0, key=f'{unique_key}_stroke_width'))
# TODO
    for colors in state['colorlist']:
        bc, fc = colors
        image = Image.new("RGBA", (state['canvas_w'], state['canvas_h']), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        for sh in state['shape']:
            if sh == "fill":
                draw.rectangle((0, 0, state['canvas_w'], state['canvas_h']), fill=bc)
            elif sh == "circle":
                state['radius'] = 50
                state['circle_x'], state['circle_y'] = state['canvas_w'] * 0.5, state['canvas_h'] * 0.5
                draw.ellipse((state['circle_x'] - state['radius'], state['circle_y'] - state['radius'], state['circle_x'] + state['radius'], state['circle_y'] + state['radius']), fill=bc, outline=None)
            elif sh == "roundrect":
                state['rect_x'], state['rect_y'] = 0, 0
                state['radius'] = 20
                draw.rounded_rectangle((state['rect_x'], state['rect_y'], state['rect_x'] + state['canvas_w'], state['rect_y'] + state['canvas_h']), state['radius'], fill=bc, outline=None)
            elif sh == "frame":
                draw.rectangle((state['margin'], state['margin'], state['canvas_w'] - state['margin'], state['canvas_h'] - state['margin']), fill=state['frame_fill'], outline=bc, width=state['frame_width'])

            if state['logo_path']:
                with draw_settings:
                    state['logo_x'].append(st.slider(f"Logo x: \"{word}\"", -state['canvas_w'], state['canvas_w'], 0, 10, key=f'{unique_key}_logo_x'))
                    state['logo_y'].append(st.slider(f"Logo y: \"{word}\"", -state['canvas_h'], state['canvas_h'], 0, 10, key=f'{unique_key}_logo_y'))
                image = process_logo(image)
            image = process_image(image)

            if state['gen_qr']:
                image = process_qr(image, state['qr_text'])

            out_name = f"{len(state['filelist']):05d}{state['ext']}"
            temp_image_path = os.path.join(state['temp_path'], out_name)
            # temp_image_path = os.path.join(subfolder_path, out_name)
            image.save(temp_image_path)
            state['filelist'].append(temp_image_path)

    if state['gen_gif']:
        images_path = state['temp_path']
        # images_path = subfolder_path
        gif_path =  'output.gif'
        image = generate_gif(images_path, state['delay'], 0, gif_path)
        st.image(gif_path)

    if state['gen_preview']:
        state['preview_image'] = state['filelist']
    else:
        if state['filelist']:
            state['preview_image'].append(state['filelist'][0])


    if state['gen_gridview']:
        for idx in range(len(state['preview_image'])):
            img = state['preview_image'][idx]
            state['cols'][idx % state['grid_col']].image(img, caption=os.path.basename(img), use_column_width=True)
    else:
        for idx in range(len(state['preview_image'])):
            img = state['preview_image'][idx]
            st.image(img, caption=os.path.basename(img), use_column_width=True)


    return state['filelist']


def main():
    load_ui_config()
    load_settings()
    state = st.session_state
    st.set_page_config(
        page_title=state['page_title'],
        page_icon=state['page_icon'],
        layout=state['layout'],
        initial_sidebar_state='auto')
    hide_ft_style()

    title = st.title("Logo Maker Web UI")
    settings = st.sidebar.title("Settings")
    input_settings = st.sidebar.expander("Input Settings")
    with input_settings:
        colorlist = state['colorlist']
        colors = st.text_area("Enter color list (split like c1;c2;.., newline for next)", value="\n".join([f"{arg1};{arg2}" for arg1, arg2 in colorlist]))
        colorlist = [tuple(line.split(';')) for line in colors.splitlines() if line.strip()]

        wordlist = state['wordlist']
        words = st.text_area("Enter word list (split like w1;w2;..,newline for next)", value="\n".join([f"{arg1};{arg2}" for arg1, arg2 in wordlist]))
        wordlist = [tuple(line.split(';')) for line in words.splitlines() if line.strip()]

    view_settings = st.sidebar.expander("View Settings")
    with view_settings:
        state['gen_preview'] = st.checkbox("Preview All")
        state['gen_gridview'] = st.checkbox("Grid View")
        if state['gen_gridview']:
            state['grid_col'] = st.slider("Grid Col",1,8,2)
    state['cols'] = st.columns(state['grid_col'])

    draw_settings = st.sidebar.expander("Draw Settings")
    with draw_settings:
        size_selected = st.selectbox("Size Preset", list(state['size_preset'].keys()))
        if size_selected:
            preset_size = state['size_preset'][size_selected]
        state['canvas_w'], state['canvas_h'] = preset_size
        state['canvas_w'] = st.slider("Width", 0, 2560, state['canvas_w'], 8)
        state['canvas_h'] = st.slider("Height", 0, 2560, state['canvas_h'], 8)

        state['shape'] = st.multiselect('Shape', ["fill", "circle", "roundrect", "frame"], default='fill')
        if state['shape']:
            if "circle" in state['shape']:
                state['radius'] = st.slider("Circle Radius", 1, 100, 50)
                state['circle_x'] = st.slider("Circle Center X", 0, state['w'], int(state['w'] *0.5))
                state['circle_y'] = st.slider("Circle Center Y", 0, state['h'], int(state['h'] *0.5))

            elif "roundrect" in state['shape']:
                state['rect_x'] = st.slider("Round Rectangle X", 0, state['w'], int(state['w'] *0.5))
                state['rect_y'] = st.slider("Round Rectangle Y", 0, state['h'], int(state['h'] *0.5))

            elif "frame" in state['shape']:
                state['margin'] = st.slider("Frame margin", 0, min(state['w'], state['h'])//2, 50)

    insert_settings = st.sidebar.expander("Insert Settings")
    with insert_settings:
        # logo_path = 'images/logo'
        # for filename in os.listdir(logo_path):
        #     if filename.endswith(".png"):
        #         logolist.append(os.path.join(logo_path, filename))
        # logo = st.sidebar.selectbox("Logo", logolist)
        state['logo'] = st.file_uploader("Logo Image", accept_multiple_files=True)
        state['logo_path'] = state['logo'] if state['logo'] else [].append([])
        state['temp_path'] = tempfile.gettempdir()

        state['gen_qr'] = st.checkbox("QR")
        if state['gen_qr']:
            state['qr_text'] = st.text_area("QR text", "example.com")
        state['qr_text'] = [line for line in state['qr_text'].splitlines() if line.strip()]

        state['gen_gif'] = st.checkbox("GIF Animation")
        if state['gen_gif']:
            state['delay'] = st.slider("Delay", 0, 5000, 0, 100)

    state['timestamp'] = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    state['size'] = f"{state['canvas_w']}x{state['canvas_h']}"

    output_settings = st.sidebar.expander("Output Settings")
    with output_settings:
        state['ext'] = st.selectbox("File Format", state['ext'])

    state['filelist'] = generate_images(state, draw_settings)

    with output_settings:
        state['zip_fname'] = st.text_input("Images filename","images.zip")
        state['zip_path'] = create_zip(state['zip_fname'], state['filelist'])
        st.download_button("Download images(.zip)", data=state['zip_path'], file_name=state['zip_fname'])

        state['setting_fname'] = st.text_input("Settings filename",'settings.json')
        # export_settings(state, state['setting_fname'])
        st.download_button("Export settings (.json)", data=open
        (state['setting_fname'], 'rb').read(), file_name=state['setting_fname'])



    # clear_temp_folder(temp_path)

if __name__ == "__main__":
    main()