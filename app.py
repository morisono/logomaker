import os
import datetime
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import zipfile
import tempfile
import matplotlib.font_manager as fm


def generate_images(colorlist, wordlist, f, ext, w, h, gfs, temp_path, logo_path, global_settings):
    filelist = []
    os.makedirs(temp_path, exist_ok=True)

    def process_image(image, words, fc):
        draw = ImageDraw.Draw(image)

        for word in words:
            with st.expander(f"Settings: {word}"):
                fs = st.slider("Fontsize", 0, 1256, gfs, 8, key=f'{len(filelist):05d}_{word}_fs')
                py = st.slider("pad_y", -500, 500, 0, 10, key=f'{len(filelist):05d}_{word}_py')
                stc = st.text_input("stroke fill", "gray", key=f'{len(filelist):05d}_{word}_stc')
                stw = st.slider("stroke width", 0, 20, 0, key=f'{len(filelist):05d}_{word}_stw')

            font = ImageFont.truetype(f, fs)
            text_bbox = draw.textbbox((0, 0), word, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            draw.text(((w - text_width) * 0.5, (h - text_height) * 0.5 + py),
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

                for colors in colorlist:
                    bc, fc = colors
                    out_name = f"{len(filelist):05d}{ext}"
                    image = Image.new("RGB", (w, h), color=bc)
                    temp_image_path = os.path.join(subfolder_path, out_name)

                    logo_w, logo_h = logo_image.size
                    resized_logo_w = int(logo_w * logo_z)
                    resized_logo_h = int(logo_h * logo_z)
                    resized_logo = logo_image.resize((resized_logo_w, resized_logo_h))
                    image.paste(resized_logo, (logo_x, logo_y), mask=resized_logo)

                    image = process_image(image, words, fc)
                    st.image(image, caption=logo_file.name, use_column_width=True)
                    image.save(temp_image_path)
                    filelist.append(temp_image_path)

    else:
        for words in wordlist:
            subfolder_path = os.path.join(temp_path, f"{words}")
            os.makedirs(subfolder_path, exist_ok=True)

            # with st.expander(f"Settings: {words}"):
            #     fs = st.slider("Fontsize", 0, 1256, gfs, 8, key=f'{len(filelist):05d}_{words}_fs')

            for colors in colorlist:
                bc, fc = colors
                out_name = f"{len(filelist):05d}{ext}"
                image = Image.new("RGB", (w, h), color=bc)

                image = process_image(image, words, fc)

                temp_image_path = os.path.join(subfolder_path, out_name)
                image.save(temp_image_path)
                st.image(image, caption=os.path.basename(temp_image_path), use_column_width=True)
                filelist.append(temp_image_path)

    return filelist


def create_zip(zip_path, filelist):
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in filelist:
            arcname = os.path.join(os.path.dirname(file), os.path.basename(file))
            zipf.write(file, arcname)
    return zip_path

def export_json():
    pass

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
    colorlist_input = st.sidebar.text_area("Enter color list (one pair per line)", value="\n".join([f"{arg1};{arg2}" for arg1, arg2 in _colorlist]))
    colorlist = [tuple(line.split(';')) for line in colorlist_input.splitlines() if line.strip()]

    wordlist_input = st.sidebar.text_area("Enter color list (one pair per line)", value="\n".join([f"{arg1};{arg2}" for arg1, arg2 in _wordlist]))
    wordlist = [tuple(line.split(';')) for line in wordlist_input.splitlines() if line.strip()]

    # font_paths = fm.findSystemFonts()
    # fontlist = [os.path.splitext(os.path.basename(font_path))[0] for font_path in font_paths]
    fontlist = []
    for filename in os.listdir('fonts'):
        if filename.endswith(".ttf"):
            fontlist.append(os.path.join('fonts', filename))
    f = st.sidebar.selectbox("Font", fontlist)

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
            gfs = st.slider("Font size", 0, 2560, 100, 8)

    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    size = f"{w}x{h}"

    logo_preset = st.sidebar.multiselect("Logo",["", "images/logo.png"])
    logo = st.sidebar.file_uploader("Logo Image", accept_multiple_files=True)
    logo_path = logo if logo else [].append(logo_preset)

    temp_dir = f"outputs/{current_time}/{size}"
    temp_path = os.path.join(tempfile.gettempdir(), temp_dir)

    # exts = Image.registered_extensions()
    # ext = st.sidebar.selectbox("File Format", {ex for ex, f in exts.items() if f in Image.OPEN})
    ext = st.sidebar.selectbox("File Format", [".png",".jpg",".tiff"])

    # generate = st.sidebar.button("Generate GIF")
    # if generate:

    export_path = st.sidebar.button("Export Settings (.json)", "outputs.json")
    if export_path:
        export_json()

    filelist = generate_images(colorlist, wordlist, f, ext, w, h, gfs, temp_path, logo_path, global_settings)

    save_as_path = "outputs.zip"
    zip_path = create_zip(save_as_path, filelist)
    st.sidebar.download_button("Download ZIP", data=zip_path, file_name=save_as_path)


if __name__ == "__main__":
    main()
