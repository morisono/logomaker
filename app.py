import os
import datetime
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import tempfile
from pathlib import Path
import matplotlib.font_manager as fm
from modules.common import load_settings, load_ui_config, create_zip, export_settings, generate_qr, clear_temp_folder
from modules.ui import hide_ft_style
from modules.utils import markdown_to_svg
from modules.utils import filename_matched, full_text_search
import itertools
import requests
from io import BytesIO

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

        adjusted_text_x = int((kwargs['canvas_w'] - text_width) * 0.5 + text_x)
        adjusted_text_y = int((kwargs['canvas_h'] - text_height) * 0.5 + text_y)

        ImageDraw.Draw(image).text((adjusted_text_x, adjusted_text_y),
                    text=word, stroke_fill=stroke_fill, stroke_width=stroke_width, fill=fc, font=font, anchor='lt')
    return image


def process_qr(image, qr_text, qr_size, qr_position, qr_border, **kwargs):
    qr_size = kwargs['canvas_h'] * 0.005 if kwargs['canvas_h'] < kwargs['canvas_w'] else kwargs['canvas_w'] * 0.005
    qr_border =  qr_size * 0.2
    qr_position = (int(kwargs['canvas_w']-30*qr_size),  int(kwargs['canvas_h']-30*qr_size))
    qr_image = generate_qr(qr_text, qr_size, qr_border)
    image.paste(qr_image, qr_position)
    return image

def process_idcon(image, id, size, ext, text, position, **kwargs):
    url = f"https://avatar.vercel.sh/{id}.{ext}?size={size}&text={text}"
    position = (int((kwargs['canvas_w']-size) * 0.50),  int((kwargs['canvas_h']-size) * 0.50))
    # params = {
    #     'size': ext,
    #     'text': text
    # }

    response = requests.get(url)
    # response = requests.get(url, params=params)
    try:
        if response.status_code == 200:
            image_data = response.content
            identicon = Image.open(BytesIO(image_data))

            mask = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(mask)
            circle_mask = (0, 0, size, size)
            draw.ellipse(circle_mask, fill=255)
            trimmed_image = Image.new("RGBA", (kwargs['canvas_w'], kwargs['canvas_h']))
            trimmed_image.paste(identicon, (0,0), mask=mask)

            result_image = image.copy()
            result_image.paste(trimmed_image, position, mask=trimmed_image)

            # image.paste(identicon, position)
            return result_image
    except Exception as e:
        st.write(e)
    return None


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


def grid_view(file_paths, col_count):
    # image_count = len(file_paths)
    for idx, image_url in enumerate(file_paths):
        col_idx = idx % col_count
        if col_idx == 0:
            col = st.columns(col_count)
        col[col_idx].image(image_url, caption=os.path.basename(image_url), use_column_width=True)


def generate_images(state, temp_dir, selected_ext, delay, widget_input, widget_filter, widget_view, widget_text, widget_shape, widget_image, widget_qr, widget_idcon, widget_gif, widget_svg, widget_output):

    state['image_paths'] = []
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

    with widget_filter:
        pass

    with widget_view:
        limits_gen = st.slider("Limits of Generation", 0, 100, state['limits_gen'], 1)

    # Draw
    generated_count = 0
    for index, (clrs, wrds, sh, qr_text, idcon_id) in enumerate(itertools.product(state['colorlist'], state['wordlist'], state['shape'], state['qr_text'], state['idcon_id']), start=1):
        if generated_count >= limits_gen:
            break

        temp_fname = f"{index:05d}-{state['timestamp']}{selected_ext}"
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


        with widget_idcon:
            if state['gen_idcon']:
                st.title(f'{index:05d}')
                state['idcon_size'] = st.slider("Size", 5, 2560, state['idcon_size'], key=f'idcon_size_{index}')
                state['idcon_ext'] = st.selectbox("Format", ["png", "svg", "jpg"], key=f'idcon_ext_{index}')
                state['idcon_text'] = ""
                if state['idcon_ext'] == "svg":
                    state['idcon_text'] = st.text_input("Text", "", key=f'idcon_text_{index}')
                state['idcon_position'] = st.slider(f"idcon Position", 0, 2560, state['idcon_position'], key=f'idcon_position_{index}')

                image = process_idcon(image,
                    idcon_id,
                    state['idcon_size'],
                    state['idcon_ext'],
                    state['idcon_text'],
                    state['idcon_position'],
                    canvas_w=state['canvas_w'],
                    canvas_h=state['canvas_h']
                 )

        with widget_text:
            st.title(f'{index:05d}')
            state['font'] = st.selectbox(f"Font", state['fontlist'], key=f'font_{index}')
            state['text_x'] = st.slider(f"Text x", -500, 500, 0, 10, key=f'text_x_{index}')
            state['text_y'] = st.slider(f"Text y", -500, 500, 0, 10, key=f'text_y_{index}')
            state['text_z'] = st.slider(f"Text size", 0, 1000, 100, 8, key=f'text_z_{index}')
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

        with widget_image:
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
                state['qr_position'] = st.slider(f"QR Position",int(0), int(50), state['qr_position'], key=f'qr_position_{index}')
                state['qr_size'] = st.slider(f"QR Size", 0, 50, state['qr_size'], key=f'qr_size_{index}')

                image = process_qr(image,
                 qr_text,
                 state['qr_size'],
                 state['qr_position'],
                 state['qr_border'],
                 canvas_w=state['canvas_w'],
                 canvas_h=state['canvas_h']
                 )



        image.save(temp_image_path)
        state['image_paths'].append(temp_image_path)
        generated_count += 1
        # st.write(state['image_paths'])

    if state['gen_gif']:
        gif_fname = f"00000-{state['timestamp']}.gif"
        images_path = temp_dir
        # images_path = subfolder_path
        with widget_output:
            temp_gif_path = generate_gif(images_path, selected_ext, gif_fname, delay)
            state['image_paths'].append(temp_gif_path)


def main():
    state = st.session_state
    load_ui_config('ui-config.json')
    st.set_page_config(
        page_title=state['page_title'],
        page_icon=state['page_icon'],
        layout=state['layout'],
        initial_sidebar_state='auto')
    hide_ft_style()
    load_settings('settings.json')


    # project_root = Path(__file__).resolve().parent
    # temp_dir_path = project_root / "outputs"
    # if not temp_dir_path.exists():
    #    temp_dir = tempfile.mkdtemp(dir=temp_dir_path)

    temp_dir = "outputs"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)


    state['timestamp'] = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    title = st.title("Logo Maker Web UI")
    search_widgets = st.sidebar.text_input("", placeholder="Search  Function 🔍")
    if search_widgets:
        matched_files(search_widgets)
        st.write(matched_files)

    settings = st.sidebar.title("Settings")
    widget_input = st.sidebar.expander("Input")
    with widget_input:
        import_settings = st.file_uploader("Import")
        if import_settings:
            load_settings(import_settings)

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

    widget_filter = st.sidebar.expander("Filter")
    with widget_filter:
        match_q = st.text_input("Matching", "words to match")
        matched_files = []
        if match_q is not None:
            target_list = st.session_state['image_paths']
            matched_files = filename_matched(match_q, target_list)
            if matched_files is not None:
                st.write(matched_files)
        # Show matched only file view

        exclude_q = st.text_input("Excluding", "words to exclide")
        from_q = st.time_input("From ", datetime.time(8, 45))
        to_q = st.time_input("To ", datetime.time(8, 45))
        lang_q = st.selectbox("Language", [""])
        location_q = st.text_input("Location", [""])

    widget_view = st.sidebar.expander("View")
    with widget_view:
        state['gen_preview'] = st.checkbox("Preview All", True)
        state['gen_gridview'] = st.checkbox("Grid View", True)
        if state['gen_gridview']:
            state['grid_col'] = st.slider("Grid Col",1,8,2)

    widget_text = st.sidebar.expander("Text")
    with widget_text:
        pass

    widget_shape = st.sidebar.expander("Shape")
    with widget_shape:
        preset_selected = st.selectbox("Size Preset", list(state['preset'].keys()))
        if preset_selected:
            state['canvas_w'], state['canvas_h'], state['text_x'], state['text_y'], state['text_z'] = state['preset'][preset_selected]
        state['canvas_w'] = st.slider("Width", 0, 2560, state['canvas_w'], 8)
        state['canvas_h'] = st.slider("Height", 0, 2560, state['canvas_h'], 8)

        state['shape'] = st.multiselect('Shape', state['shapelist'], default=['fill'])

    widget_image = st.sidebar.expander("Image")
    with widget_image:
        # image_dir = 'images/logo'
        # for filename in os.listdir(image_dir):
        #     if filename.endswith(".png"):
        #         logolist.append(os.path.join(image_dir, filename))
        # logo = st.sidebar.selectbox("Logo", logolist)
        state['image'] = st.file_uploader("Image", accept_multiple_files=True)
        state['image_dir'] = state['image'] if state['image'] else [].append([])

    widget_qr = st.sidebar.expander("QR")
    with widget_qr:
        state['gen_qr'] = st.checkbox("QR", True)
        if state['gen_qr']:
            state['qr_text'] = st.text_area("QR text", state['qr_text'])
            state['qr_text'] = [line for line in state['qr_text'].splitlines() if line.strip()]

    widget_idcon = st.sidebar.expander("Identicon")
    with widget_idcon:
        state['gen_idcon'] = st.checkbox("Identicon", True)
        if state['gen_idcon']:
            state['idcon_id'] = st.text_area("Id", "\n".join(state['idcon_id']))
            state['idcon_id'] = [line for line in state['idcon_id'].splitlines() if line.strip()]

    widget_gif = st.sidebar.expander("GIF")
    with widget_gif:
        state['gen_gif'] = st.checkbox("GIF Animation", True)
        if state['gen_gif']:
            delay = st.slider("Delay", 0, 5000, 0, 100, key='delay')

    widget_svg = st.sidebar.expander("SVG")
    with widget_svg:
        svg_w = '500px'
        svg_h = '500px'

        markdown_text = st.text_area("Input markdown")
        if markdown_text:
            svg_text = markdown_to_svg(markdown_text, svg_w, svg_h)
            st.markdown(svg_text)

        combine = st.button("Combine Images")
        if combine:
            tile_x = st.slider("Tile x")
            tile_y = st.slider("Tile y")
            image_paths = st.session_state['image_paths']
            combined_image = combine_images(image_paths, tile_x, tile_y)
            st.images(combined_image, caption='Combined Image', use_column_width=True)

    widget_output = st.sidebar.expander("Output")
    with widget_output:
        selected_ext = st.selectbox("File Format", state['exts'])

    try:
        with st.spinner("Processing..."):
            generate_images(state, temp_dir, selected_ext, delay, widget_input, widget_filter, widget_view, widget_text, widget_shape, widget_image, widget_qr, widget_idcon, widget_gif, widget_svg, widget_output)
    except Exception as e:
        st.error(e)

    if state['image_paths'] is None:
        pass
    else:
        if state['gen_preview']:
            state['preview_image'] = state['image_paths']
        else:
            state['preview_image'] = [state['image_paths'][0]]

    if state['gen_gridview']:
        grid_view(state['preview_image'], state['grid_col'])
    else:
        for img in state['preview_image']:
            st.image(img, caption=os.path.basename(img), use_column_width=True)

    with widget_output:
        if st.button("Create Zip"):
            zip_fname = state['zip_fname']
            zip_path = os.path.join(temp_dir, zip_fname)
            image_paths = state['image_paths']
            create_zip(zip_path, image_paths)
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