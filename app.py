import os
import glob
import datetime
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import tempfile
import matplotlib.font_manager as fm
from modules.common import load_settings, load_ui_config, create_zip, export_settings, generate_qr, clear_temp_folder
from modules.ui import hide_ft_style
import itertools

def process_image(image, image_dir, image_x, image_y, image_z):
    for logo_file, lx, ly, lz in zip(image_dir, image_x, image_y, image_z):
        logo_image = Image.open(logo_file).convert("RGBA")
        image_w, image_h = logo_image.size
        resized_image_w = int(image_w * lz)
        resized_image_h = int(image_h * lz)
        resized_logo = logo_image.resize((resized_image_w, resized_image_h))
        image.paste(resized_logo, (lx, ly), mask=resized_logo)
    return image

def process_logo(image, words, fonts, fc, logo_x, logo_y, logo_z, stroke_fill, stroke_width, **kwargs):
    for word in words:
        font = ImageFont.truetype(fonts, logo_z)
        text_bbox = ImageDraw.Draw(image).textbbox((0, 0), word, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        logo_x = int((kwargs['canvas_w'] - text_width) * 0.5 + logo_x)
        logo_y = int((kwargs['canvas_h'] - text_height) * 0.5 + logo_y)

        ImageDraw.Draw(image).text((logo_x, logo_y),
                    text=word, stroke_fill=stroke_fill, stroke_width=stroke_width, fill=fc, font=font, anchor='lm')
    return image

def process_qr(image, qr_text, qr_size, qr_position, qr_border, **kwargs):
    qr_size = kwargs['canvas_h'] * 0.01 if kwargs['canvas_h'] < kwargs['canvas_w'] else kwargs['canvas_w'] * 0.01
    qr_border =  qr_size * 0.2
    qr_position = (int(kwargs['canvas_w']-30*qr_size),  int(kwargs['canvas_h']-30*qr_size))
    qr_image = generate_qr(qr_text, qr_size, qr_border)
    image.paste(qr_image, qr_position)
    return image

def generate_gif(image_dir, ext, gif_fname, delay):
    image_paths = []
    frames = []
    for image_path in os.listdir(image_dir):
        if image_path.endswith(ext):
            image_paths.append(os.path.join(image_dir, image_path))

    for image_path in image_paths:
        image = Image.open(image_path)
        frames.append(image)

    out_path = os.path.join(image_dir, gif_fname)

    frames[0].save(out_path, format="GIF", append_images=frames[1:], save_all=True, duration=delay, loop=0)

    return out_path


def generate_images(state, temp_dir, selected_ext, widget_input, widget_view, widget_draw, widget_insert, widget_output):

    state['filelist'] = []
    # temp_image_path = os.path.join(subfolder_path, temp_fname)    # os.makedirs(temp_path, exist_ok=True)
    # for words in state['wordlist']:
        # subfolder_path = os.path.join(temp_path, f"{words}")
        # os.makedirs(subfolder_path, exist_ok=True)
    # font_paths = fm.findSystemFonts()
    # fontlist = [os.path.splitext(os.path.basename(font_path))[0] for font_path in font_paths]
    # TODO: state --> param ?
    # Load font
    for font_path in os.listdir(state['font_dir']):
        if font_path.endswith(".ttf"):
            state['fontlist'].append(os.path.join(state['font_path'], font_path))

    with widget_view:
        limits_gen = st.slider("Limits of Generation", 0, 100, 8, 1)

    # Draw
    generated_count = 0
    for index, (colors, words, sh, qr_text) in enumerate(itertools.product(state['colorlist'], state['wordlist'], state['shape'], state['qr_text']), start=1):
        if generated_count >= limits_gen:
            break

        temp_fname = f"{index:05d}{selected_ext}"
        temp_image_path = os.path.join(temp_dir, temp_fname)
        bc, fc = colors
        image = Image.new("RGBA", (state['canvas_w'], state['canvas_h']), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        if sh == "fill":
            draw.rectangle((0, 0, state['canvas_w'], state['canvas_h']), fill=bc)
        elif sh == "circle":
            state['radius'] = 50
            state['circle_x'], state['circle_y'] = state['canvas_w'] * 0.5, state['canvas_h'] * 0.5
            draw.ellipse((state['circle_x'] - state['radius'], state['circle_y'] - state['radius'], state['circle_x'] + state['radius'], state['circle_y'] + state['radius']), fill=bc, outline=None)
        elif sh == "roundrect":
            state['rect_x'], state['rect_y'] = 0, 0
            state['radius'] = 40
            draw.rounded_rectangle((state['rect_x'], state['rect_y'], state['rect_x'] + state['canvas_w'], state['rect_y'] + state['canvas_h']), state['radius'], fill=bc, outline=None)
        elif sh == "frame":
            draw.rectangle((state['margin'], state['margin'], state['canvas_w'] - state['margin'], state['canvas_h'] - state['margin']), fill=state['frame_fill'], outline=bc, width=state['frame_width'])

    # Insert
        with widget_draw:
            font = st.selectbox(f"Font : \"{words}\"", state['fontlist'], key=f'font_{index}')
            stroke_fill = st.text_input(f"Stroke fill: \"{words}\"", "gray", key=f'stroke_fill_{index}')
            stroke_width = st.slider(f"Stroke width: \"{words}\"", 0, 20, 0, key=f'stroke_width_{index}')
            logo_x = st.slider(f"Logo x : \"{words}\"", -500, 500, state['logo_x'], 10, key=f'logo_x_{index}')
            logo_y = st.slider(f"Logo y : \"{words}\"", -500, 500, state['logo_y'], 10, key=f'logo_y_{index}')
            logo_z = st.slider(f"Logo size : \"{words}\"", 0, 800, state['logo_z'], 8, key=f'logo_z_{index}')

        image = process_logo(
            image,
            words,
            font,
            fc,
            logo_x,
            logo_y,
            logo_z,
            stroke_fill,
            stroke_width,
            canvas_w=state['canvas_w'],
            canvas_h=state['canvas_h']
        )

        if state['image_dir']:
            with widget_draw:
                state['image_x'].append(st.slider(f"Logo x: \"{word}\"", -state['canvas_w'], state['canvas_w'], 0, 10, key=f'image_x_{index}'))
                state['image_y'].append(st.slider(f"Logo y: \"{word}\"", -state['canvas_h'], state['canvas_h'], 0, 10, key=f'image_y_{index}'))

                image = process_image(image, state['image_dir'], state['image_x'], state['image_y'], state['image_z'])


        if state['gen_qr']:
            image = process_qr(image, qr_text, state['qr_size'], state['qr_position'], state['qr_border'], canvas_w=state['canvas_w'], canvas_h=state['canvas_h'])

        image.save(temp_image_path)
        state['filelist'].append(temp_image_path)
        generated_count += 1
        # st.write(state['filelist'])

    if state['gen_gif']:
        images_path = temp_dir
        # images_path = subfolder_path
        with widget_insert:
            out_path = generate_gif(images_path, selected_ext, state['gif_fname'], state['delay'])
            state['filelist'].append(out_path)



def main():
    state = st.session_state
    load_ui_config()
    st.set_page_config(
        page_title=state['page_title'],
        page_icon=state['page_icon'],
        layout=state['layout'],
        initial_sidebar_state='auto')
    hide_ft_style()
    load_settings()
    title = st.title("Logo Maker Web UI")
    settings = st.sidebar.title("Settings")
    widget_input = st.sidebar.expander("Input Settings")
    with widget_input:
        cols1, cols2 = st.columns([1, 1])
        with cols1:
            bc_pick = st.color_picker('Background color',key=f'bc_pick')
        with cols2:
            fc_pick = st.color_picker('Foreground color', '#fff',key=f'fc_pick')

        if st.button("Append"):
            state['colorlist'] = list(state['colorlist'])
            state['colorlist'].append((bc_pick, fc_pick))



        st.text_area("Colors", value="\n".join([f"{bc},{fc}" for bc, fc in state['colorlist']]))


        words = st.text_area("Words", value="\n".join([f"{arg1};{arg2}" for arg1, arg2 in state['wordlist']]))
        state['wordlist'] = [tuple(line.split(';')) for line in words.splitlines() if line.strip()]

    widget_view = st.sidebar.expander("View Settings")
    with widget_view:
        state['gen_preview'] = st.checkbox("Preview All", True)
        state['gen_gridview'] = st.checkbox("Grid View", True)
        if state['gen_gridview']:
            state['grid_col'] = st.slider("Grid Col",1,8,2)
    state['cols'] = st.columns(state['grid_col'])

    widget_draw = st.sidebar.expander("Draw Settings")
    with widget_draw:
        preset_selected = st.selectbox("Size Preset", list(state['preset'].keys()))
        if preset_selected:
            state['canvas_w'], state['canvas_h'], state['logo_x'], state['logo_y'], state['logo_z'] = state['preset'][preset_selected]
        state['canvas_w'] = st.slider("Width", 0, 2560, state['canvas_w'], 8)
        state['canvas_h'] = st.slider("Height", 0, 2560, state['canvas_h'], 8)

        state['shape'] = st.multiselect('Shape', ["fill", "circle", "roundrect", "frame"], default='fill')
        if state['shape']:
            if "circle" in state['shape']:
                state['radius'] = st.slider("Circle Radius", 1, 100, 50)
                state['circle_x'] = st.slider("Circle Center X", 0, state['canvas_w'], int(state['canvas_w'] *0.5))
                state['circle_y'] = st.slider("Circle Center Y", 0, state['canvas_h'], int(state['canvas_h'] *0.5))

            elif "roundrect" in state['shape']:
                state['rect_x'] = st.slider("Round Rectangle X", 0, state['canvas_w'], int(state['canvas_w'] *0.5))
                state['rect_y'] = st.slider("Round Rectangle Y", 0, state['canvas_h'], int(state['canvas_h'] *0.5))

            elif "frame" in state['shape']:
                state['margin'] = st.slider("Frame margin", 0, min(state['canvas_w'], state['canvas_h'])//2, 50)

    widget_insert = st.sidebar.expander("Insert Settings")
    with widget_insert:
        # image_dir = 'images/logo'
        # for filename in os.listdir(image_dir):
        #     if filename.endswith(".png"):
        #         logolist.append(os.path.join(image_dir, filename))
        # logo = st.sidebar.selectbox("Logo", logolist)
        state['logo'] = st.file_uploader("Logo Image", accept_multiple_files=True)
        state['image_dir'] = state['logo'] if state['logo'] else [].append([])

        state['gen_qr'] = st.checkbox("QR", True)
        if state['gen_qr']:
            state['qr_text'] = st.text_area("QR text", "example.com")
            state['qr_text'] = [line for line in state['qr_text'].splitlines() if line.strip()]

        state['gen_gif'] = st.checkbox("GIF Animation", True)
        if state['gen_gif']:
            state['delay'] = st.slider("Delay", 0, 5000, 0, 100)

    temp_dir = tempfile.gettempdir()
    state['timestamp'] = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    state['size'] = f"{state['canvas_w']}x{state['canvas_h']}"

    widget_output = st.sidebar.expander("Output Settings")
    with widget_output:
        selected_ext = st.selectbox("File Format", state['exts'])

    generate_images(state, temp_dir, selected_ext, widget_input, widget_view, widget_draw, widget_insert, widget_output)

    if state['filelist'] is None:
        pass
    else:
        if state['gen_preview']:
            state['preview_image'] = state['filelist']
        else:
            state['preview_image'] = state['filelist'][:limits_gen]

    if state['gen_gridview']:
        col_count = state['grid_col']
        image_count = len(state['preview_image'])
        for idx, img in enumerate(state['preview_image']):
            col_idx = idx % col_count
            if col_idx == 0:
                col = st.columns(col_count)
            col[col_idx].image(img, caption=os.path.basename(img), use_column_width=True)
    else:
        for img in state['preview_image']:
            st.image(img, caption=os.path.basename(img), use_column_width=True)

    with widget_output:
        st.download_button("Download images(.zip)", data=create_zip(os.path.join(temp_dir, state['zip_fname']), state['filelist']), file_name=state['zip_fname'])

        st.download_button("Export settings (.json)", data=open
        (state['settings_fname'], 'rb').read(), file_name=state['settings_fname'])


    # clear_temp_folder(temp_path)


if __name__ == "__main__":
    main()