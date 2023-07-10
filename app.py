import os
import datetime
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import tempfile
from pathlib import Path
import matplotlib.font_manager as fm
from modules.common import load_settings, load_ui_config, create_zip, export_settings, generate_qr, clear_temp_folder
from modules.ui import hide_ft_style
from modules.utils import markdown_to_svg, combine_images
from modules.utils import filename_matched, filename_excluded, filter_by_date_range, filter_by_language, filter_by_location, full_text_search
from modules.automator import google_image_search

import itertools
import urllib.request
from io import BytesIO


def process_shape(image, shape, **kwargs):
    draw = ImageDraw.Draw(image)
    if shape == "fill":
        draw.rectangle((0, 0, st.session_state['canvas_w'], st.session_state['canvas_h']), fill=st.session_state['bc'])
    elif shape == "circle":
        draw.ellipse((kwargs['circle_x'] - kwargs['radius'], kwargs['circle_y'] - kwargs['radius'], kwargs['circle_x'] + kwargs['radius'], kwargs['circle_y'] + kwargs['radius']), fill=st.session_state['bc'], outline=None)
    elif shape == "roundrect":
        draw.rounded_rectangle((kwargs['rect_x'], kwargs['rect_y'], kwargs['rect_x'] + st.session_state['canvas_w'], kwargs['rect_y'] + st.session_state['canvas_h']), kwargs['radius'], fill=st.session_state['bc'], outline=None)
    elif shape == "frame":
        draw.rectangle((kwargs['margin'], kwargs['margin'], st.session_state['canvas_w'] - kwargs['margin'], st.session_state['canvas_h'] - kwargs['margin']), fill=st.session_state['frame_fill'], outline=st.session_state['bc'], width=st.session_state['frame_width'])
    # draw.rounded_rectangle((st.session_state['rect_x'], st.session_state['rect_y'], st.session_state['rect_x'] + st.session_state['canvas_w'], st.session_state['rect_y'] + st.session_state['canvas_h']), st.session_state['radius'], fill=(0, 0, 0, 0), outline=None)
    return image


def process_image(image, image_dir, image_x, image_y, image_z):
    for img_path in image_dir:
        logo_image = Image.open(img_path).convert("RGBA")
        image_w, image_h = logo_image.size
        resized_image_w = int(image_w * image_z)
        resized_image_h = int(image_h * image_z)
        resized_logo = logo_image.resize((resized_image_w, resized_image_h))
        image.paste(resized_logo, (image_x, image_y), mask=resized_logo)
    return image

def process_mask(image, mask_dir, mask_x, mask_y, mask_z):
    for img_path in mask_dir:
        mask_image = image.open(img_path).convert("RGBA")
        mask_w, mask_h = mask_image.size
        resized_mask_w = int(mask_w * mask_z)
        resized_mask_h = int(mask_h * mask_z)
        resized_logo = mask_image.resize((resized_mask_w, resized_mask_h))
        # TODO: Opacity modification
        image.paste(resized_logo, (mask_x, mask_y), mask=resized_logo)
    return image

def process_logotext(image, word, fonts, fc, text_x, text_y, text_z, stroke_fill, stroke_width, **kwargs):
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

    try:
        with urllib.request.urlopen(url) as response:
            if response.status == 200:
                image_data = response.read()
                identicon = Image.open(BytesIO(image_data))

                mask = Image.new("L", (size, size), 0)
                draw = ImageDraw.Draw(mask)
                circle_mask = (0, 0, size, size)
                draw.ellipse(circle_mask, fill=255)
                trimmed_image = Image.new("RGBA", (kwargs['canvas_w'], kwargs['canvas_h']))
                trimmed_image.paste(identicon, (0,0), mask=mask)

                result_image = image.copy()
                result_image.paste(trimmed_image, position, mask=trimmed_image)

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


def generate_images(state, temp_dir, selected_ext, delay, widget_input, widget_filter, widget_view, widget_text, widget_shape, widget_image, widget_mask, widget_qr, widget_idcon, widget_gif, widget_svg, widget_output):

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


    with widget_input:

        st.subheader("Mutiply Switch")
        check_lists = {
            'colorlist': st.checkbox("colorlist", value=True),
            'wordlist': st.checkbox("wordlist", value=True),
            'shape': st.checkbox("shape", value=True),
            'qr_text': st.checkbox("qr_text", value=True),
            'idcon_id': st.checkbox("idcon_id", value=True)
        }

        checked_lists = [label for label, checked in check_lists.items() if checked]


    with widget_filter:
        pass

    with widget_view:
        limits_gen = st.slider("Limits of Generation", 0, 100, state['limits_gen'], 1)

    with widget_text:
        st.title(f'Global')
        state['font'] = st.selectbox(f"Font", state['fontlist'], key=f'font_global')
        state['text_x'] = st.slider(f"Text x", -500, 500, state['text_x'], 10, key=f'text_x_global')
        state['text_y'] = st.slider(f"Text y", -500, 500, state['text_y'], 10, key=f'text_y_global')
        state['text_z'] = st.slider(f"Text size", 0, 1000, state['text_z'], 8, key=f'text_z_global')
        state['stroke_width'] = st.slider(f"Stroke width", 0, 20, state['stroke_width'], key=f'stroke_width_global')
        state['stroke_fill'] = st.text_input(f"Stroke fill", state['stroke_fill'], key=f'stroke_fill_global')

    with widget_shape:
        st.title('Global')
        if "circle" in state['shape']:
            state['circle_x'] = int(state['canvas_w'] *0.5)
            state['circle_y'] = int(state['canvas_h'] *0.5)

            state['radius'] = st.slider("Circle Radius", 1, 200, state['radius'], key=f'radius_global')
            state['circle_x'] = st.slider("Circle Center X", 0, state['canvas_w'], state['circle_x'], key=f'circle_x_global')
            state['circle_y'] = st.slider("Circle Center Y", 0, state['canvas_h'], state['circle_y'], key=f'circle_y_global')

        elif "roundrect" in state['shape']:
            state['rect_x'] = st.slider("Round Rectangle X", 0, 400, 0, key=f'rect_x_global')
            state['rect_y'] = st.slider("Round Rectangle Y", 0, state['canvas_h'], 0, key=f'rect_y_global')

        elif "frame" in state['shape']:
            state['margin'] = st.slider("Frame margin", 0, min(state['canvas_w'], state['canvas_h'])//2, 0, key=f'margin_global')

    generated_count = 0
    for index, (values) in enumerate(itertools.product(*[state[label] for label in checked_lists]), start=1):

        if generated_count >= limits_gen:
            break

        temp_fname = f"{index:05d}-{state['timestamp']}{selected_ext}"
        temp_image_path = os.path.join(temp_dir, temp_fname)
        image = Image.new("RGBA", (state['canvas_w'], state['canvas_h']), (0, 0, 0, 0))

        if 'colorlist' in checked_lists:
            clrs = values[checked_lists.index('colorlist')]
            state['bc'], state['fc'] = clrs

        if 'shape' in checked_lists:
            sh = values[checked_lists.index('shape')]
            with widget_shape:
                st.title(f'{index:05d}')
                if "circle" in sh:
                    state['radius'] = st.slider("Circle Radius", 1, 200, state['radius'], key=f'radius_{index}')
                    state['circle_x'] = st.slider("Circle Center X", 0, state['canvas_w'], state['circle_x'], key=f'circle_x_{index}')
                    state['circle_y'] = st.slider("Circle Center Y", 0, state['canvas_h'], state['circle_y'], key=f'circle_y_{index}')

                elif "roundrect" in sh:
                    state['rect_x'] = st.slider("Round Rectangle X", 0, 400, 0, key=f'rect_x_{index}')
                    state['rect_y'] = st.slider("Round Rectangle Y", 0, state['canvas_h'], 0, key=f'rect_y_{index}')

                elif "frame" in sh:
                    state['margin'] = st.slider("Frame margin", 0, min(state['canvas_w'], state['canvas_h'])//2, 0, key=f'margin_{index}')

                image = process_shape(
                        image,
                        sh,
                        radius=state['radius'],
                        circle_x=state['circle_x'],
                        rect_x=state['rect_x'],
                        rect_y=state['rect_y'],
                        margin=state['margin']
                    )

        if 'idcon_id' in checked_lists:
            idcon_id = values[checked_lists.index('idcon_id')]
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

        if 'wordlist' in checked_lists:
            wrds = values[checked_lists.index('wordlist')]
            for wrd in wrds:
                with widget_text:
                    st.title(f'{index:05d}')
                    state['font'] = st.selectbox(f"Font: {wrd}", state['fontlist'], key=f'font_{wrd}{index}')
                    state['text_x'] = st.slider(f"Text x: {wrd}{index}", -500, 500, state['text_x'], 10, key=f'text_x_{wrd}{index}')
                    state['text_y'] = st.slider(f"Text y: {wrd}{index}", -500, 500, state['text_y'], 10, key=f'text_y_{wrd}{index}')
                    state['text_z'] = st.slider(f"Text size: {wrd}{index}", 0, 1000, state['text_z'], 8, key=f'text_z_{wrd}{index}')
                    state['stroke_width'] = st.slider(f"Stroke width : {wrd}", 0, 20, state['stroke_width'], key=f'stroke_width_{wrd}{index}')
                    state['stroke_fill'] = st.text_input(f"Stroke fill: {wrd}", state['stroke_fill'], key=f'stroke_fill_{wrd}{index}')

                    image = process_logotext(
                        image,
                        wrd,
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
        # with widget_image:
        #     if state['image_dir']:
        #         st.title(f'{index:05d}')
        #         state['image_x'] = st.slider(f"Image x", -state['canvas_w'], state['canvas_w'], 0, 10, key=f'image_x_{index}')
        #         state['image_y'] = st.slider(f"Image y", -state['canvas_h'], state['canvas_h'], 0, 10, key=f'image_y_{index}')
        #         state['image_z'] = st.slider(f"Image z", 0.2, 10.0, 0.2, 0.1, key=f'image_z_{index}')

        #         image = process_image(
        #         image,
        #         state['image_dir'],
        #         state['image_x'],
        #         state['image_y'],
        #         state['image_z']
        #         )

        # with widget_mask:
        #     if state['masks_dir']:
        #         st.title(f'{index:05d}')
        #         state['mask_x'] = st.slider(f"mask x", -state['canvas_w'], state['canvas_w'], 0, 10, key=f'mask_x_{index}')
        #         state['mask_y'] = st.slider(f"mask y", -state['canvas_h'], state['canvas_h'], 0, 10, key=f'mask_y_{index}')
        #         state['mask_z'] = st.slider(f"mask z", 0.2, 10.0, 0.2, 0.1, key=f'mask_z_{index}')

        #         image = process_mask(
        #         image,
        #         state['masks_dir'],
        #         state['mask_x'],
        #         state['mask_y'],
        #         state['mask_z']
        #         )

        if 'qr_text' in checked_lists:
            qr_text = values[checked_lists.index('qr_text')]
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
    search_widgets = st.sidebar.text_input("", placeholder="[WIP] Search  Function 🔍")
    if search_widgets:
        matched_files(search_widgets)
        st.write(matched_files)

    settings = st.sidebar.title("Settings")
    widget_input = st.sidebar.expander("Input")
    with widget_input:
        import_settings = st.file_uploader("Import")
        if import_settings:
            load_settings(import_settings)

        # cols1, cols2 = st.columns([1, 1])
        # with cols1:
        #     bc_pick = st.color_picker('Background color',key=f'bc_pick')
        # with cols2:
        #     fc_pick = st.color_picker('Foreground color', '#fff',key=f'fc_pick')

        # append_colors = st.button("Append", key=f'append_colors')
        # if append_colors:
        #     state['colorlist'].extend([(bc_pick, fc_pick) for bc_pick, fc_pick in [tuple(line.split(',')) for line in colors.splitlines() if line.strip()]])
        colors = st.text_area("Colors", value="\n".join([f"{bc},{fc}" for bc, fc in state['colorlist']]))

        state['colorlist'] = [tuple(line.split(',')) for line in colors.splitlines() if line.strip()]


        # cols1, cols2 = st.columns([1, 1])
        # with cols1:
        #     word1 = st.text_input('Word 1',key=f'word1')
        # with cols2:
        #     word2 = st.text_input('Word 2',key=f'word2')

        # append_words = st.button("Append", key=f'append_words')
        # if append_words:
        #     state['wordlist'] = list(state['wordlist'])
        #     state['wordlist'].append((word1, word2))
        words = st.text_area("Words", value="\n".join([f"{arg1},{arg2}" for arg1, arg2 in state['wordlist']]))
        state['wordlist'] = [tuple(line.split(',')) for line in words.splitlines() if line.strip()]

        if st.button("Reset"):
            clear_temp_folder(temp_dir)

    widget_filter = st.sidebar.expander("Filter")
    # with widget_filter:
    #     match_q = st.text_input("Matching", placeholder="words to match")
    #     matched_files = []
    #     if match_q is not None:
    #         matched_files = filename_matched(match_q, state['image_paths'])
    #         if matched_files:
    #             st.write("Matching Files:")
    #             st.write(matched_files)
    #         else:
    #             st.write("No matching files found.")

    #     exclude_q = st.text_input("Excluding", placeholder="words to exclide")
    #     if exclude_q is not None:
    #         excluded_files = filename_excluded(exclude_q, state['image_paths'])
    #         if excluded_files:
    #             st.write("Excluded Files:")
    #             st.write(excluded_files)
    #         else:
    #             st.write("No excluded files found.")

    #     from_q = st.time_input("From ", datetime.time(8, 45))
    #     to_q = st.time_input("To ", datetime.time(8, 45))
    #     if from_q is not None and to_q is not None:
    #         filtered_by_date = filter_by_date_range(from_q, to_q, state['image_paths'])
    #         if filtered_by_date:
    #             st.write("Files within Date Range:")
    #             st.write(filtered_by_date)
    #         else:
    #             st.write("No files found within the specified date range.")

    #     lang_q = st.selectbox("Language", [""])
    #     if lang_q != "":
    #         filtered_by_language = filter_by_language(lang_q, state['image_paths'])
    #         if filtered_by_language:
    #             st.write("Files filtered by Language:")
    #             st.write(filtered_by_language)
    #         else:
    #             st.write("No files found for the specified language.")

    #     location_q = st.text_input("Location", [""])
    #     if location_q != "":
    #         filtered_by_location = filter_by_location(location_q, state['image_paths'])
    #         if filtered_by_location:
    #             st.write("Files filtered by Location:")
    #             st.write(filtered_by_location)
    #         else:
    #             st.write("No files found for the location")

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

        state['shape'] = st.multiselect('Shape', state['shapelist'], state['shape'])

    widget_image = st.sidebar.expander("Image")
    with widget_image:
        state['uploaded_image'] = st.file_uploader("Image", accept_multiple_files=True)
        state['image_dir'] = [state['uploaded_image'] if state['uploaded_image'] else [].append([])]

        search_queries = st.text_input('Google Search Keyword: ', "Apple")
        image_formats = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'bmp', 'tiff', 'webp', 'ico', 'icons', 'pdf']
        image_format = st.selectbox('Formats: ', image_formats)
        limits = st.slider('Limits: ', 0, 100, 2)
        image_size = st.text_input("image_size", value="500")
        aspect_ratio = st.text_input("aspect_ratio", value="s")
        color = st.text_input("color", value="gray")
        image_type = st.text_input("image_type", value="clipart")
        region = st.text_input("region", value="jp")
        safe_search = st.text_input("safe_search", value="active")
        license = st.text_input("license", value="fmc")

        if search_queries:
            with st.spinner("Progress ..."):
                # state['google_image_paths'] = google_image_search(search_queries, image_format, limits, temp_dir, image_size, aspect_ratio, color, image_type, region, safe_search, license)
                pass

        if state['google_image_paths'] is None:
            pass
        else:
            state['image_dir'].append(state['google_image_paths'])
            # state['image_paths'].append(state['google_image_paths'])
#
    widget_mask = st.sidebar.expander("Mask")
    with widget_mask:
        state['masks_dir'] = 'images/masks'
        for filename in os.listdir(state['masks_dir']):
            if filename.endswith(".png"):
                state['masks'].append(os.path.join(state['masks_dir'], filename))
        state['mask'] = st.selectbox("Mask", state['masks'])

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
            # svg_text = markdown_to_svg(markdown_text, svg_w, svg_h)
            # st.markdown(svg_text)
            pass # TODO
        combine = st.button("Combine Images")
        if combine:
            tile_x = st.slider("Tile x")
            tile_y = st.slider("Tile y")
            image_paths = state['image_paths']
            # combined_image = combine_images(image_paths, tile_x, tile_y)
            # st.images(combined_image, caption='Combined Image', use_column_width=True)
            pass # TODO

    widget_output = st.sidebar.expander("Output")
    with widget_output:
        selected_ext = st.selectbox("File Format", state['exts'])

    try:
        with st.spinner("Processing..."):
            generate_images(state, temp_dir, selected_ext, delay, widget_input, widget_filter, widget_view, widget_text, widget_shape, widget_image, widget_mask, widget_qr, widget_idcon, widget_gif, widget_svg, widget_output)
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