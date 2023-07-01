import os
import datetime
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import tempfile
from pathlib import Path
import matplotlib.font_manager as fm
from modules.common import load_settings, load_ui_config, create_zip, export_settings, generate_qr, clear_temp_folder
from modules.ui import hide_ft_style
import itertools

def process_image(image, image_dir, image_x, image_y, image_z):
    for img_path in image_dir:
        logo_image = Image.open(img_path).convert("RGBA")
        image_w, image_h = logo_image.size
        resized_image_w = int(image_w * image_z)
        resized_image_h = int(image_h * image_z)
        resized_logo = logo_image.resize((resized_image_w, resized_image_h))
        image.paste(resized_logo, (image_x, image_y), mask=resized_logo)
    return image

def process_logo(image, words, fonts, fc, text_x, text_y, text_z, stroke_fill, stroke_width, **kwargs):
    for word in words:
        font = ImageFont.truetype(fonts, text_z)
        text_bbox = ImageDraw.Draw(image).textbbox((0, 0), word, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = int((kwargs['canvas_w'] - text_width) * 0.5 + text_x)
        text_y = int((kwargs['canvas_h'] - text_height) * 0.5 + text_y)

        ImageDraw.Draw(image).text((text_x, text_y),
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


def generate_images(state, temp_dir, selected_ext, delay, widget_input, widget_view, widget_text, widget_shape,  widget_lmage, widget_qr, widget_gif, widget_output):

    state['filelist'] = []
    # temp_image_path = os.path.join(subfolder_path, temp_fname)    # os.makedirs(temp_dir, exist_ok=True)
    # for words in state['wordlist']:
        # subfolder_path = os.path.join(temp_dir, f"{words}")
        # os.makedirs(subfolder_path, exist_ok=True)
    # font_paths = fm.findSystemFonts()
    # fontlist = [os.path.splitext(os.path.basename(font_path))[0] for font_path in font_paths]
    # TODO: state --> param ?
    # Load font
    for font_path in os.listdir(state['font_dir']):
        if font_path.endswith(".ttf"):
            state['fontlist'].append(os.path.join(state['font_path'], font_path))

    with widget_view:
        limits_gen = st.slider("Limits of Generation", 0, 1000, state['limits_gen'], 1)

    # Draw
    generated_count = 0
    for index, (clrs, wrds, sh, qr_text) in enumerate(itertools.product(state['colorlist'], state['wordlist'], state['shape'], state['qr_text']), start=1):
        if generated_count >= limits_gen:
            break

        temp_fname = f"{index:05d}{selected_ext}"
        temp_image_path = os.path.join(temp_dir, temp_fname)
        state['bc'], state['fc'] = clrs
        image = Image.new("RGBA", (state['canvas_w'], state['canvas_h']), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        with widget_shape:
            # TODO: GLOBAL SETTINGS set default with state[]
            # st.title(f'All')

            # state['radius'] = st.slider("Circle Radius", 1, 200, state['radius'], key=f'all_{index}_radius')
            # state['circle_x'] = st.slider("Circle Center X", 0, state['canvas_w'], int(state['canvas_w'] *0.5), key=f'all_{index}_canvas_w')
            # state['circle_y'] = st.slider("Circle Center Y", 0, state['canvas_h'], int(state['canvas_h'] *0.5), key=f'all_{index}_circle_y')
            st.title(f'{index:05d}')
            if "circle" in sh:
                state['radius'] = st.slider("Circle Radius", 1, 200, 80, key=f'{index}_radius')
                state['circle_x'] = st.slider("Circle Center X", 0, state['canvas_w'], int(state['canvas_w'] *0.5), key=f'{index}_circle_x')
                state['circle_y'] = st.slider("Circle Center Y", 0, state['canvas_h'], int(state['canvas_h'] *0.5), key=f'{index}_circle_y')

            elif "roundrect" in sh:
                state['rect_x'] = st.slider("Round Rectangle X", 0, 400, 0, key=f'{index}_rect_x')
                state['rect_y'] = st.slider("Round Rectangle Y", 0, state['canvas_h'], 0, key=f'{index}_rect_y')

            elif "frame" in sh:
                state['margin'] = st.slider("Frame margin", 0, min(state['canvas_w'], state['canvas_h'])//2, 0, key=f'{index}_margin')

            if sh == "fill":
                draw.rectangle((0, 0, state['canvas_w'], state['canvas_h']), fill=state['bc'])
            elif sh == "circle":
                draw.ellipse((state['circle_x'] - state['radius'], state['circle_y'] - state['radius'], state['circle_x'] + state['radius'], state['circle_y'] + state['radius']), fill=state['bc'], outline=None)
            elif sh == "roundrect":
                draw.rounded_rectangle((state['rect_x'], state['rect_y'], state['rect_x'] + state['canvas_w'], state['rect_y'] + state['canvas_h']), state['radius'], fill=state['bc'], outline=None)
            elif sh == "frame":
                draw.rectangle((state['margin'], state['margin'], state['canvas_w'] - state['margin'], state['canvas_h'] - state['margin']), fill=state['frame_fill'], outline=state['bc'], width=state['frame_width'])
                # draw.rounded_rectangle((state['rect_x'], state['rect_y'], state['rect_x'] + state['canvas_w'], state['rect_y'] + state['canvas_h']), state['radius'], fill=(0, 0, 0, 0), outline=None)


    # Insert
        with widget_text:
            st.title(f'{index:05d}')
            state['font'] = st.selectbox(f"Font", state['fontlist'], key=f'font_{index}')
            state['text_x'] = st.slider(f"Text x", -500, 500, 0, 10, key=f'text_x_{index}')
            state['text_y'] = st.slider(f"Text y", -500, 500, 0, 10, key=f'text_y_{index}')
            state['text_z'] = st.slider(f"Text size", 0, 100, 100, 8, key=f'text_z_{index}')
            state['stroke_width'] = st.slider(f"Stroke width", 0, 20, 0, key=f'stroke_width_{index}')
            state['stroke_fill'] = st.text_input(f"Stroke fill", "gray", key=f'stroke_fill_{index}')

        image = process_logo(
            image,
            wrds,
            state['font'],
            state['fc'],
            state['text_x'],
            state['text_y'],
            state['text_z'],
            state['stroke_fill'],
            state['stroke_width'],
            canvas_w=state['canvas_w'],
            canvas_h=state['canvas_h']
        )

        with widget_lmage:
            if state['image_dir']:
                st.title(f'{index:05d}')
                state['image_x'] = st.slider(f"Image x", -state['canvas_w'], state['canvas_w'], 0, 10, key=f'image_x_{index}')
                state['image_y'] = st.slider(f"Image y", -state['canvas_h'], state['canvas_h'], 0, 10, key=f'image_y_{index}')
                state['image_z'] = st.slider(f"Image z", 0.2, 10.0, 0.2, 0.1, key=f'image_z_{index}')

                image = process_image(
                image,
                state['image_dir'],
                state['image_x'],
                state['image_y'],
                state['image_z']
                )

        with widget_qr:
            if state['gen_qr']:
                st.title(f'{index:05d}')
                state['qr_position'] = st.slider(f"QR Position",int(0),  int(50), key=f'qr_position_{index}')
                state['qr_size'] = st.slider(f"QR Size", 0, 50, 10, key=f'qr_size_{index}')

                image = process_qr(image,
                 qr_text,
                 state['qr_size'],
                 state['qr_position'],
                 state['qr_border'],
                 canvas_w=state['canvas_w'],
                 canvas_h=state['canvas_h']
                 )

        image.save(temp_image_path)
        state['filelist'].append(temp_image_path)
        generated_count += 1
        # st.write(state['filelist'])

    if state['gen_gif']:
        images_path = temp_dir
        # images_path = subfolder_path
        with widget_output:
            temp_gif_path = generate_gif(images_path, selected_ext, state['gif_fname'], delay)
            state['filelist'].append(temp_gif_path)



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


    # project_root = Path(__file__).resolve().parent
    # temp_dir = tempfile.mkdtemp(dir=f'{project_root}/outputs')
    temp_dir = tempfile.gettempdir()



    state['timestamp'] = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    title = st.title("Logo Maker Web UI")
    settings = st.sidebar.title("Settings")

    widget_input = st.sidebar.expander("Input Settings")
    with widget_input:

        cols1, cols2 = st.columns([1, 1])
        with cols1:
            bc_pick = st.color_picker('Background color',key=f'bc_pick')
        with cols2:
            fc_pick = st.color_picker('Foreground color', '#fff',key=f'fc_pick')

        append_colors = st.button("Append", key=f'append_colors')
        if append_colors:
            state['colorlist'].extend([(bc_pick, fc_pick) for bc_pick, fc_pick in [tuple(line.split(',')) for line in colors.splitlines() if line.strip()]])
        colors = st.text_area("Colors", value="\n".join([f"{bc},{fc}" for bc, fc in state['colorlist']]))

        state['colorlist'] = [tuple(line.split(',')) for line in colors.splitlines() if line.strip()]


        cols1, cols2 = st.columns([1, 1])
        with cols1:
            word1 = st.text_input('Word 1',key=f'word1')
        with cols2:
            word2 = st.text_input('Word 2',key=f'word2')

        append_words = st.button("Append", key=f'append_words')
        if append_words:
            state['wordlist'] = list(state['wordlist'])
            state['wordlist'].append((word1, word2))
        words = st.text_area("Words", value="\n".join([f"{arg1},{arg2}" for arg1, arg2 in state['wordlist']]))
        state['wordlist'] = [tuple(line.split(',')) for line in words.splitlines() if line.strip()]


        if st.button("Reset"):
            clear_temp_folder(temp_dir)


    widget_view = st.sidebar.expander("View Settings")
    with widget_view:
        state['gen_preview'] = st.checkbox("Preview All")
        state['gen_gridview'] = st.checkbox("Grid View")
        if state['gen_gridview']:
            state['grid_col'] = st.slider("Grid Col",1,8,2)
    state['cols'] = st.columns(state['grid_col'])

    widget_text = st.sidebar.expander("Text Settings")
    with widget_text:
        preset_selected = st.selectbox("Size Preset", list(state['preset'].keys()))
        if preset_selected:
            state['canvas_w'], state['canvas_h'], state['text_x'], state['text_y'], state['text_z'] = state['preset'][preset_selected]
        state['canvas_w'] = st.slider("Width", 0, 2560, state['canvas_w'], 8)
        state['canvas_h'] = st.slider("Height", 0, 2560, state['canvas_h'], 8)


    widget_shape = st.sidebar.expander("Shape Settings")
    with widget_shape:
        state['shape'] = st.multiselect('Shape', state['shapelist'], default=['fill', 'circle'])

    widget_lmage = st.sidebar.expander("Image Settings")
    with widget_lmage:
        # image_dir = 'images/logo'
        # for filename in os.listdir(image_dir):
        #     if filename.endswith(".png"):
        #         logolist.append(os.path.join(image_dir, filename))
        # logo = st.sidebar.selectbox("Logo", logolist)
        state['image'] = st.file_uploader("Image", accept_multiple_files=True)
        state['image_dir'] = state['image'] if state['image'] else [].append([])

    widget_gif = st.sidebar.expander("GIF Settings")
    with widget_gif:
        state['gen_gif'] = st.checkbox("GIF Animation", True)
        if state['gen_gif']:
            delay = st.slider("Delay", 0, 5000, 0, 100, key='delay')

    widget_qr = st.sidebar.expander("QR Settings")
    with widget_qr:
        state['gen_qr'] = st.checkbox("QR", True)
        if state['gen_qr']:
            state['qr_text'] = st.text_area("QR text", "example.com")
            state['qr_text'] = [line for line in state['qr_text'].splitlines() if line.strip()]

    widget_output = st.sidebar.expander("Output Settings")
    with widget_output:
        selected_ext = st.selectbox("File Format", state['exts'])

    generate_images(state, temp_dir, selected_ext, delay, widget_input, widget_view, widget_text, widget_shape, widget_lmage, widget_qr, widget_gif, widget_output)

    if state['filelist'] is None:
        pass
    else:
        if state['gen_preview']:
            state['preview_image'] = state['filelist']
        else:
            state['preview_image'] = state['filelist'][0]

    if state['gen_gridview']:
        col_count = state['grid_col']
        image_count = len(state['filelist'])
        for idx, img in enumerate(state['filelist']):
            col_idx = idx % col_count
            if col_idx == 0:
                col = st.columns(col_count)
            col[col_idx].image(img, caption=os.path.basename(img), use_column_width=True)
    else:
        for img in state['filelist']:
            st.image(img, caption=os.path.basename(img), use_column_width=True)

    with widget_output:
        if st.button("Create Zip"):
            zip_fname = state['zip_fname']
            zip_path = os.path.join(temp_dir, zip_fname)
            filelist = state['filelist']
            create_zip(zip_path, filelist)
            with open(zip_path, "rb") as file:
                st.download_button(
                    label="Download images (.zip)",
                    data=file,
                    file_name=zip_fname,
                    mime="application/zip"
                )


        st.download_button("Export settings (.json)", data=open
        (state['settings_fname'], 'rb').read(), file_name=state['settings_fname'])


if __name__ == "__main__":
    main()