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
import itertools
import requests
from io import BytesIO

def process_shape(_s_):
    draw = ImageDraw.Draw(_s_['image'])
    if _s_['shape'] == "fill":
        draw.rectangle((0, 0, _s_['canvas_w'], _s_['canvas_h']), fill=_s_['bc'])
    elif _s_['shape'] == "circle":
        draw.ellipse((_s_['circle_x'] - _s_['radius'], _s_['circle_y'] - _s_['radius'], _s_['circle_x'] + _s_['radius'], _s_['circle_y'] + _s_['radius']), fill=_s_['bc'], outline=None)
    elif _s_['shape'] == "roundrect":
        draw.rounded_rectangle((_s_['rect_x'], _s_['rect_y'], _s_['rect_x'] + _s_['canvas_w'], _s_['rect_y'] + _s_['canvas_h']), _s_['radius'], fill=_s_['bc'], outline=None)
    elif _s_['shape'] == "frame":
        draw.rectangle((_s_['margin'], _s_['margin'], _s_['canvas_w'] - _s_['margin'], _s_['canvas_h'] - _s_['margin']), fill=_s_['frame_fill'], outline=_s_['bc'], width=_s_['frame_width'])
    # draw.rounded_rectangle((_s_['rect_x'], _s_['rect_y'], _s_['rect_x'] + _s_['canvas_w'], _s_['rect_y'] + _s_['canvas_h']), _s_['radius'], fill=(0, 0, 0, 0), outline=None)


def process_image(_s_):
    for img_path in _s_['image_dir']:
        logo_image = Image.open(img_path).convert("RGBA")
        image_w, image_h = logo_image.size
        resized_image_w = int(image_w * _s_['image_z'])
        resized_image_h = int(image_h * _s_['image_z'])
        resized_logo = logo_image.resize((resized_image_w, resized_image_h))
        _s_['image'].paste(resized_logo, (_s_['image_x'], _s_['image_y']), mask=resized_logo)

def process_logotext(_s_):
    for word in _s_['words']:
        font = ImageFont.truetype(_s_['fonts'], _s_['text_z'])
        text_bbox = ImageDraw.Draw(_s_['image']).textbbox((0, 0), word, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        adjusted_text_x = int((_s_['canvas_w'] - text_width) * 0.5 + _s_['text_x'])
        adjusted_text_y = int((_s_['canvas_h'] - text_height) * 0.5 + _s_['text_y'])

        ImageDraw.Draw(_s_['image']).text((adjusted_text_x, adjusted_text_y),
                    text=word, stroke_fill=_s_['stroke_fill'], stroke_width=_s_['stroke_width'], fill=_s_['fc'], font=font, anchor='lt')

def process_qr(_s_):
    qr_size = _s_['canvas_h'] * 0.005 if _s_['canvas_h'] < _s_['canvas_w'] else _s_['canvas_w'] * 0.005
    qr_border =  qr_size * 0.2
    qr_position = (int(_s_['canvas_w']-30*qr_size),  int(_s_['canvas_h']-30*qr_size))
    qr_image = generate_qr(qr_text, qr_size, qr_border)
    _s_['image'].paste(qr_image, qr_position)

def process_idcon(_s_):
    url = f"https://avatar.vercel.sh/{_s_['idcon_id']}.{_s_['idcon_ext']}?size={_s_['idcon_size']}&text={_s_['idcon_text']}"
    position = (int((_s_['canvas_w']-_s_['idcon_size']) * 0.50),  int((_s_['canvas_h']-_s_['idcon_size']) * 0.50))
    # params = {
    #     'size': _s_['idcon_ext'],
    #     'text': _s_['idcon_text']
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
            trimmed_image = Image.new("RGBA", (_s_['canvas_w'], _s_['canvas_h']))
            trimmed_image.paste(identicon, (0,0), mask=mask)

            _s_['image'].paste(trimmed_image, position, mask=trimmed_image)
    except Exception as e:
        st.write(e)


def generate_gif(_s_):
    image_paths = []
    frames = []
    for image_path in os.listdir(_s_['image_dir']):
        if image_path.endswith(ext):
            image_paths.append(os.path.join(_s_['image_dir'], image_path))

    for image_path in image_paths:
        _s_['image'] = Image.open(image_path)
        frames.append(_s_['image'])

    out_path = os.path.join(_s_['image_dir'], gif_fname)

    frames[0].save(out_path, format="GIF", append_images=frames[1:], save_all=True, duration=delay, loop=0)


def grid_view(file_paths, col_count):
    # image_count = len(file_paths)
    for idx, image_url in enumerate(file_paths):
        col_idx = idx % col_count
        if col_idx == 0:
            col = st.columns(col_count)
        col[col_idx].image(image_url, caption=os.path.basename(image_url), use_column_width=True)


def generate_images(_s_, temp_dir, selected_ext, delay, widget_input, widget_filter, widget_view, widget_text, widget_shape, widget_image, widget_qr, widget_idcon, widget_gif, widget_svg, widget_output):

    _s_['image_paths'] = []
    # temp_image_path = os.path.join(subfolder_path, temp_fname)    # os.makedirs(temp_dir, exist_ok=True)
    # for words in _s_['wordlist']:
        # subfolder_path = os.path.join(temp_dir, f"{words}")
        # os.makedirs(subfolder_path, exist_ok=True)
    # font_paths = fm.findSystemFonts()
    # fontlist = [os.path.splitext(os.path.basename(font_path))[0] for font_path in font_paths]
    # TODO: _s_ --> param ?
    # Load font
    for font_path in os.listdir(_s_['font_dir']):
        if font_path.endswith(".ttf"):
            _s_['fontlist'].append(os.path.join(_s_['font_path'], font_path))

    with widget_filter:
        pass

    with widget_view:
        limits_gen = st.slider("Limits of Generation", 0, 100, _s_['limits_gen'], 1)

    with widget_text:
        st.title(f'Global')
        _s_['font'] = st.selectbox(f"Font", _s_['fontlist'], key=f'font_global')
        _s_['text_x'] = st.slider(f"Text x", -500, 500, _s_['text_x'], 10, key=f'text_x_global')
        _s_['text_y'] = st.slider(f"Text y", -500, 500, _s_['text_y'], 10, key=f'text_y_global')
        _s_['text_z'] = st.slider(f"Text size", 0, 1000, _s_['text_z'], 8, key=f'text_z_global')
        _s_['stroke_width'] = st.slider(f"Stroke width", 0, 20, _s_['stroke_width'], key=f'stroke_width_global')
        _s_['stroke_fill'] = st.text_input(f"Stroke fill", _s_['stroke_fill'], key=f'stroke_fill_global')

    with widget_shape:
        st.title('Global')
        if "circle" in _s_['shape']:
            _s_['circle_x'] = int(_s_['canvas_w'] *0.5)
            _s_['circle_y'] = int(_s_['canvas_h'] *0.5)

            _s_['radius'] = st.slider("Circle Radius", 1, 200, _s_['radius'], key=f'radius_global')
            _s_['circle_x'] = st.slider("Circle Center X", 0, _s_['canvas_w'], _s_['circle_x'], key=f'circle_x_global')
            _s_['circle_y'] = st.slider("Circle Center Y", 0, _s_['canvas_h'], _s_['circle_y'], key=f'circle_y_global')

        elif "roundrect" in _s_['shape']:
            _s_['rect_x'] = st.slider("Round Rectangle X", 0, 400, 0, key=f'rect_x_global')
            _s_['rect_y'] = st.slider("Round Rectangle Y", 0, _s_['canvas_h'], 0, key=f'rect_y_global')

        elif "frame" in _s_['shape']:
            _s_['margin'] = st.slider("Frame margin", 0, min(_s_['canvas_w'], _s_['canvas_h'])//2, 0, key=f'margin_global')

    generated_count = 0
    for index, (clrs, wrds, sh, qr_text, idcon_id) in enumerate(itertools.product(_s_['colorlist'], _s_['wordlist'], _s_['shape'], _s_['qr_text'], _s_['idcon_id']), start=1):
        if generated_count >= limits_gen:
            break

        temp_fname = f"{index:05d}-{_s_['timestamp']}{selected_ext}"
        temp_image_path = os.path.join(temp_dir, temp_fname)
        _s_['bc'], _s_['fc'] = clrs
        _s_['image'] = Image.new("RGBA", (_s_['canvas_w'], _s_['canvas_h']), (0, 0, 0, 0))

        with widget_shape:
            st.title(f'{index:05d}')
            if "circle" in sh:
                _s_['radius'] = st.slider("Circle Radius", 1, 200, _s_['radius'], key=f'radius_{index}')
                _s_['circle_x'] = st.slider("Circle Center X", 0, _s_['canvas_w'], _s_['circle_x'], key=f'circle_x_{index}')
                _s_['circle_y'] = st.slider("Circle Center Y", 0, _s_['canvas_h'], _s_['circle_y'], key=f'circle_y_{index}')

            elif "roundrect" in sh:
                _s_['rect_x'] = st.slider("Round Rectangle X", 0, 400, 0, key=f'rect_x_{index}')
                _s_['rect_y'] = st.slider("Round Rectangle Y", 0, _s_['canvas_h'], 0, key=f'rect_y_{index}')

            elif "frame" in sh:
                _s_['margin'] = st.slider("Frame margin", 0, min(_s_['canvas_w'], _s_['canvas_h'])//2, 0, key=f'margin_{index}')

            process_shape(_s_)

        with widget_idcon:
            if _s_['gen_idcon']:
                st.title(f'{index:05d}')
                _s_['idcon_size'] = st.slider("Size", 5, 2560, _s_['idcon_size'], key=f'idcon_size_{index}')
                _s_['idcon_ext'] = st.selectbox("Format", ["png", "svg", "jpg"], key=f'idcon_ext_{index}')
                _s_['idcon_text'] = ""
                if _s_['idcon_ext'] == "svg":
                    _s_['idcon_text'] = st.text_input("Text", "", key=f'idcon_text_{index}')
                _s_['idcon_position'] = st.slider(f"idcon Position", 0, 2560, _s_['idcon_position'], key=f'idcon_position_{index}')

            process_idcon(_s_)

        with widget_text:
            st.title(f'{index:05d}')
            _s_['font'] = st.selectbox(f"Font", _s_['fontlist'], key=f'font_{index}')
            _s_['text_x'] = st.slider(f"Text x", -500, 500, _s_['text_x'], 10, key=f'text_x_{index}')
            _s_['text_y'] = st.slider(f"Text y", -500, 500, _s_['text_y'], 10, key=f'text_y_{index}')
            _s_['text_z'] = st.slider(f"Text size", 0, 1000, _s_['text_z'], 8, key=f'text_z_{index}')
            _s_['stroke_width'] = st.slider(f"Stroke width", 0, 20, _s_['stroke_width'], key=f'stroke_width_{index}')
            _s_['stroke_fill'] = st.text_input(f"Stroke fill", _s_['stroke_fill'], key=f'stroke_fill_{index}')

            process_logotext(_s_)

        with widget_image:
            if _s_['image_dir']:
                st.title(f'{index:05d}')
                _s_['image_x'] = st.slider(f"Image x", -_s_['canvas_w'], _s_['canvas_w'], 0, 10, key=f'image_x_{index}')
                _s_['image_y'] = st.slider(f"Image y", -_s_['canvas_h'], _s_['canvas_h'], 0, 10, key=f'image_y_{index}')
                _s_['image_z'] = st.slider(f"Image z", 0.2, 10.0, 0.2, 0.1, key=f'image_z_{index}')

                process_image(_s_)

        with widget_qr:
            if _s_['gen_qr']:
                st.title(f'{index:05d}')
                _s_['qr_position'] = st.slider(f"QR Position",int(0), int(50), _s_['qr_position'], key=f'qr_position_{index}')
                _s_['qr_size'] = st.slider(f"QR Size", 0, 50, _s_['qr_size'], key=f'qr_size_{index}')

                process_qr(_s_)

        _s_['image'].save(temp_image_path)
        _s_['image_paths'].append(temp_image_path)
        generated_count += 1
        # st.write(_s_['image_paths'])

    if _s_['gen_gif']:
        _s_['gif_fname'] = f"00000-{_s_['timestamp']}.gif"
        _s_['images_path'] = temp_dir
        # images_path = subfolder_path
        with widget_output:
            _s_['temp_gif_path'] = generate_gif(_s_)
            _s_['image_paths'].append(_s_['temp_gif_path'])


def main():
    _s_ = st.session_state
    load_ui_config('ui-config.json')
    st.set_page_config(
        page_title=_s_['page_title'],
        page_icon=_s_['page_icon'],
        layout=_s_['layout'],
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


    _s_['timestamp'] = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

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

        cols1, cols2 = st.columns([1, 1])
        with cols1:
            bc_pick = st.color_picker('Background color',key=f'bc_pick')
        with cols2:
            fc_pick = st.color_picker('Foreground color', '#fff',key=f'fc_pick')

        append_colors = st.button("Append", key=f'append_colors')
        if append_colors:
            _s_['colorlist'].extend([(bc_pick, fc_pick) for bc_pick, fc_pick in [tuple(line.split(',')) for line in colors.splitlines() if line.strip()]])
        colors = st.text_area("Colors", value="\n".join([f"{bc},{fc}" for bc, fc in _s_['colorlist']]))

        _s_['colorlist'] = [tuple(line.split(',')) for line in colors.splitlines() if line.strip()]


        cols1, cols2 = st.columns([1, 1])
        with cols1:
            word1 = st.text_input('Word 1',key=f'word1')
        with cols2:
            word2 = st.text_input('Word 2',key=f'word2')

        append_words = st.button("Append", key=f'append_words')
        if append_words:
            _s_['wordlist'] = list(_s_['wordlist'])
            _s_['wordlist'].append((word1, word2))
        _s_['words'] = st.text_area("Words", value="\n".join([f"{arg1},{arg2}" for arg1, arg2 in _s_['wordlist']]))
        _s_['wordlist'] = [tuple(line.split(',')) for line in _s_['words'].splitlines() if line.strip()]

        if st.button("Reset"):
            clear_temp_folder(temp_dir)

    widget_filter = st.sidebar.expander("Filter")
    with widget_filter:
        match_q = st.text_input("Matching", placeholder="words to match")
        matched_files = []
        if match_q is not None:
            matched_files = filename_matched(match_q, _s_['image_paths'])
            if matched_files:
                st.write("Matching Files:")
                st.write(matched_files)
            else:
                st.write("No matching files found.")

        exclude_q = st.text_input("Excluding", placeholder="words to exclide")
        if exclude_q is not None:
            excluded_files = filename_excluded(exclude_q, _s_['image_paths'])
            if excluded_files:
                st.write("Excluded Files:")
                st.write(excluded_files)
            else:
                st.write("No excluded files found.")

        from_q = st.time_input("From ", datetime.time(8, 45))
        to_q = st.time_input("To ", datetime.time(8, 45))
        if from_q is not None and to_q is not None:
            filtered_by_date = filter_by_date_range(from_q, to_q, _s_['image_paths'])
            if filtered_by_date:
                st.write("Files within Date Range:")
                st.write(filtered_by_date)
            else:
                st.write("No files found within the specified date range.")

        lang_q = st.selectbox("Language", [""])
        if lang_q != "":
            filtered_by_language = filter_by_language(lang_q, _s_['image_paths'])
            if filtered_by_language:
                st.write("Files filtered by Language:")
                st.write(filtered_by_language)
            else:
                st.write("No files found for the specified language.")

        location_q = st.text_input("Location", [""])
        if location_q != "":
            filtered_by_location = filter_by_location(location_q, _s_['image_paths'])
            if filtered_by_location:
                st.write("Files filtered by Location:")
                st.write(filtered_by_location)
            else:
                st.write("No files found for the location")

    widget_view = st.sidebar.expander("View")
    with widget_view:
        _s_['gen_preview'] = st.checkbox("Preview All", True)
        _s_['gen_gridview'] = st.checkbox("Grid View", True)
        if _s_['gen_gridview']:
            _s_['grid_col'] = st.slider("Grid Col",1,8,2)

    widget_text = st.sidebar.expander("Text")
    with widget_text:
        pass

    widget_shape = st.sidebar.expander("Shape")
    with widget_shape:
        preset_selected = st.selectbox("Size Preset", list(_s_['preset'].keys()))
        if preset_selected:
            _s_['canvas_w'], _s_['canvas_h'], _s_['text_x'], _s_['text_y'], _s_['text_z'] = _s_['preset'][preset_selected]
        _s_['canvas_w'] = st.slider("Width", 0, 2560, _s_['canvas_w'], 8)
        _s_['canvas_h'] = st.slider("Height", 0, 2560, _s_['canvas_h'], 8)

        _s_['shape'] = st.multiselect('Shape', _s_['shapelist'], default=['fill'])

    widget_image = st.sidebar.expander("Image")
    with widget_image:
        # image_dir = 'images/logo'
        # for filename in os.listdir(image_dir):
        #     if filename.endswith(".png"):
        #         logolist.append(os.path.join(image_dir, filename))
        # logo = st.sidebar.selectbox("Logo", logolist)
        _s_['image'] = st.file_uploader("Image", accept_multiple_files=True)
        _s_['image_dir'] = _s_['image'] if _s_['image'] else [].append([])

    widget_qr = st.sidebar.expander("QR")
    with widget_qr:
        _s_['gen_qr'] = st.checkbox("QR", True)
        if _s_['gen_qr']:
            _s_['qr_text'] = st.text_area("QR text", _s_['qr_text'])
            _s_['qr_text'] = [line for line in _s_['qr_text'].splitlines() if line.strip()]

    widget_idcon = st.sidebar.expander("Identicon")
    with widget_idcon:
        _s_['gen_idcon'] = st.checkbox("Identicon", True)
        if _s_['gen_idcon']:
            _s_['idcon_id'] = st.text_area("Id", "\n".join(_s_['idcon_id']))
            _s_['idcon_id'] = [line for line in _s_['idcon_id'].splitlines() if line.strip()]

    widget_gif = st.sidebar.expander("GIF")
    with widget_gif:
        _s_['gen_gif'] = st.checkbox("GIF Animation", True)
        if _s_['gen_gif']:
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
            image_paths = _s_['image_paths']
            combined_image = combine_images(image_paths, tile_x, tile_y)
            st.images(combined_image, caption='Combined Image', use_column_width=True)

    widget_output = st.sidebar.expander("Output")
    with widget_output:
        selected_ext = st.selectbox("File Format", _s_['exts'])

    try:
        with st.spinner("Processing..."):
            generate_images(_s_, temp_dir, selected_ext, delay, widget_input, widget_filter, widget_view, widget_text, widget_shape, widget_image, widget_qr, widget_idcon, widget_gif, widget_svg, widget_output)
    except Exception as e:
        st.error(e)

    if _s_['image_paths'] is None:
        pass
    else:
        if _s_['gen_preview']:
            _s_['preview_image'] = _s_['image_paths']
        else:
            _s_['preview_image'] = [_s_['image_paths'][0]]

    if _s_['gen_gridview']:
        grid_view(_s_['preview_image'], _s_['grid_col'])
    else:
        for img in _s_['preview_image']:
            st.image(img, caption=os.path.basename(img), use_column_width=True)

    with widget_output:
        if st.button("Create Zip"):
            zip_fname = _s_['zip_fname']
            zip_path = os.path.join(temp_dir, zip_fname)
            image_paths = _s_['image_paths']
            create_zip(zip_path, image_paths)
            with open(zip_path, "rb") as file:
                st.download_button(
                    label="Download images (.zip)",
                    data=file,
                    file_name=zip_fname,
                    mime="application/zip"
                )


        st.download_button("Export settings (.json)", data=open
        (_s_['settings_fname'], 'rb').read(), file_name=_s_['settings_fname'])


if __name__ == "__main__":
    main()