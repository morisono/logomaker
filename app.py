import os
import datetime
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import zipfile
import tempfile
import matplotlib.font_manager as fm


def generate_images(colorlist, wordlist, f, ext, w, h, temp_path, logo_path, advanced_edit):
    filelist = []
    os.makedirs(temp_path, exist_ok=True)

    def process_image(image, words, bc, fc):
        draw = ImageDraw.Draw(image)

        for wrd in words:
            with advanced_edit:
                fs = st.slider("Fontsize", 0, 1256, 100, 8, key=f'{len(filelist):05d}_{wrd}_fs')
                py = st.slider("pad_y", -500, 500, 0, 10, key=f'{len(filelist):05d}_{wrd}_py')
                stc = st.text_input("stroke fill", "gray", key=f'{len(filelist):05d}_{wrd}_stc')
                stw = st.slider("stroke width", 0, 20, 0, key=f'{len(filelist):05d}_{wrd}_stw')

            font = ImageFont.truetype(f, fs)
            text_bbox = draw.textbbox((0, 0), wrd, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            draw.text(((w - text_width) * 0.5, (h - text_height) * 0.5 + py),
                text=wrd, stroke_fill=stc, stroke_width=stw, fill=fc, font=font, anchor='lt')

        return image

    if logo_path:
        for logo_file in logo_path:
            with advanced_edit:
                logo_x = st.slider("Logo x", -w, w, 0, 10, key=f'{logo_file}_x')
                logo_y = st.slider("Logo y", -h, h, 0, 10, key=f'{logo_file}_y')
                logo_z = st.slider("Logo Zoom", 0.05, 20.0, 2.0, 0.01, key=f'{logo_file}_z')

            logo_image = Image.open(logo_file).convert("RGBA")

            for words in wordlist:
                subfolder_path = os.path.join(temp_path, f"{words}")
                os.makedirs(subfolder_path, exist_ok=True)

                for colors in colorlist:
                    bc, fc = colors
                    out_name = f"{len(filelist):05d}{ext}"
                    image = Image.new("RGB", (w, h), color=bc)

                    logo_w, logo_h = logo_image.size
                    resized_logo_w = int(logo_w * logo_z)
                    resized_logo_h = int(logo_h * logo_z)
                    resized_logo = logo_image.resize((resized_logo_w, resized_logo_h))
                    image.paste(resized_logo, (logo_x, logo_y), mask=resized_logo)

                    image = process_image(image, words, bc, fc)

                    temp_image_path = os.path.join(subfolder_path, out_name)
                    image.save(temp_image_path)
                    filelist.append(temp_image_path)

    else:
        for words in wordlist:
            subfolder_path = os.path.join(temp_path, f"{words}")
            os.makedirs(subfolder_path, exist_ok=True)

            for colors in colorlist:
                bc, fc = colors
                out_name = f"{len(filelist):05d}{ext}"
                image = Image.new("RGB", (w, h), color=bc)

                image = process_image(image, words, bc, fc)

                temp_image_path = os.path.join(subfolder_path, out_name)
                image.save(temp_image_path)
                filelist.append(temp_image_path)

    return filelist



def create_zip(out, filelist):
    with zipfile.ZipFile(out, "w") as zipf:
        for file in filelist:
            zipf.write(file, os.path.join(os.path.basename(os.path.dirname(file)), os.path.basename(file)))
    return out

def main():
    _colorlist = [
        ("black", "white"),
        ("white", "red"),
    ]

    _wordlist = [
        ("Designed by", "m.s."),
    ]

    st.title("Logo Maker Web UI")

    st.sidebar.title("Settings")
    st.sidebar.subheader("Color List (Background Color; Foreground Color)")
    colorlist_input = st.sidebar.text_area("Enter color list (one pair per line)", value="\n".join([f"{arg1};{arg2}" for arg1, arg2 in _colorlist]))
    colorlist = [tuple(line.split(';')) for line in colorlist_input.splitlines() if line.strip()]

    st.sidebar.subheader("Word List (Line1; Line2)")
    wordlist_input = st.sidebar.text_area("Enter color list (one pair per line)", value="\n".join([f"{arg1};{arg2}" for arg1, arg2 in _wordlist]))
    wordlist = [tuple(line.split(';')) for line in wordlist_input.splitlines() if line.strip()]

    st.sidebar.subheader("Font List")
    font_paths = fm.findSystemFonts()
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

    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    size = f"{w}x{h}"

    logo_preset = st.sidebar.multiselect("Logo",["", "images/logo.png"])
    logo = st.sidebar.file_uploader("Logo Image", accept_multiple_files=True)
    logo_path = logo if logo else [].append(logo_preset)
    _out = f"outputs/{current_time}/{size}"
    temp_path = os.path.join(tempfile.gettempdir(), _out)

    # exts = Image.registered_extensions()
    # ext = st.sidebar.selectbox("File Format", {ex for ex, f in exts.items() if f in Image.OPEN})
    ext = st.sidebar.selectbox("File Format", [".png",".jpg",".tiff"])

    # generate = st.sidebar.button("Generate GIF")
    # if generate:

    advanced_edit = st.sidebar.expander("Advanced Edit")
    with advanced_edit:
        w = st.slider("Width", 0, 2560, w, 8)
        h = st.slider("Height", 0, 2560, h, 8)

    filelist = generate_images(colorlist, wordlist, f, ext, w, h, temp_path, logo_path, advanced_edit)

    # save_as_path = st.text_input("Save as", "output.zip") # TODO
    # export_path = st.text_input("Export Json", "output.json") # TODO
    # zip_path = create_zip(save_as_path, filelist)
    # st.download_button("Download as ZIP", data=zip_path, file_name=save_as_path)

    for file in filelist:
        image = Image.open(file)
        st.image(image, caption=os.path.basename(file), use_column_width=True)

if __name__ == "__main__":
    main()
