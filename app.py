import os
import datetime
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import zipfile
import tempfile
import matplotlib.font_manager as fm


def generate_images(colorlist, wordlist, f, ext, w, h, p1, p2, temp_path):
    i = 0
    filelist = []
    os.makedirs(temp_path, exist_ok=True)
    for words in wordlist:
        c1, c2 = words
        subfolder_path = os.path.join(temp_path, f"{c1}_{c2}")
        os.makedirs(subfolder_path, exist_ok=True)
        for colors in colorlist:
            bc, fc = colors
            out_name = f"{i:05d}{ext}"
            image = Image.new("RGB", (w, h), color=bc)
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype(f, p1)
            text_width, text_height = draw.textsize(c1, font=font)
            draw.text(((w - text_width) / 2, (h - text_height) / 2 - 200), c1, fill=fc, font=font)
            font = ImageFont.truetype(f, p2)
            text_width, text_height = draw.textsize(c2, font=font)
            draw.text(((w - text_width) / 2, (h - text_height) / 2 + 20), c2, fill=fc, font=font)
            temp_image_path = os.path.join(subfolder_path, out_name)
            image.save(temp_image_path)
            filelist.append(temp_image_path)
            i += 1

    return filelist

def create_zip(out, filelist):
    with zipfile.ZipFile(out, "w") as zipf:
        for file in filelist:
            zipf.write(file, os.path.join(os.path.basename(os.path.dirname(file)), os.path.basename(file)))
    return out

def main():
    _colorlist = [
        ("white", "black"),
        ("black", "white"),
    ]

    _wordlist = [
        ("Created by", "m.s."),
    ]

    st.title("Logo Maker Web UI")

    st.sidebar.title("Settings")
    st.sidebar.subheader("Color List (Background Color; Foreground Color)")
    colorlist_input = st.sidebar.text_area("Enter color list (one pair per line)", value="\n".join([f"{arg1};{arg2}" for arg1, arg2 in _colorlist]))
    colorlist = [tuple(line.split(';')) for line in colorlist_input.splitlines() if line.strip()]

    st.sidebar.subheader("Word List (Line1; Line2)")
    wordlist_input = st.sidebar.text_area("Enter color list (one pair per line)", value="\n".join([f"{arg1};{arg2}" for arg1, arg2 in _wordlist]))
    wordlist = [tuple(line.split(';')) for line in wordlist_input.splitlines() if line.strip()]

    st.sidebar.subheader("Font List (System Installed)")
    font_paths = fm.findSystemFonts()
    # fontlist = [os.path.splitext(os.path.basename(font_path))[0] for font_path in font_paths]
    fontlist = ["fonts/DelaGothicOne-Regular.ttf"]
    f = st.sidebar.selectbox("Font", fontlist)
    # exts = Image.registered_extensions()
    ext = st.sidebar.selectbox("File Format", [".png",".jpg",".tiff"])
    # ext = st.sidebar.selectbox("File Format", {ex for ex, f in exts.items() if f in Image.OPEN})
    w = st.sidebar.slider("Width", 0, 2560, 1024, 8)
    h = st.sidebar.slider("Height", 0, 2560, 512, 8)
    p1 = st.sidebar.slider("pointsize 1", 0, 1256, 100, 8)
    p2 = st.sidebar.slider("pointsize 2", 0, 1256, 400, 8)

    generate = st.sidebar.button("Generate")
    # if generate:
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    size = f"{w}x{h}"
    _out = f"outputs/{current_time}/{size}"
    temp_path = os.path.join(tempfile.gettempdir(), _out)
    filelist = generate_images(colorlist, wordlist, f, ext, w, h, p1, p2, temp_path)

        # save_as_path = st.text_input("Save as", "output.zip") # TODO
        # zip_path = create_zip(save_as_path, filelist)
        # st.download_button("Download as ZIP", data=zip_path, file_name=save_as_path)

    for file in filelist:
        image = Image.open(file)
        st.image(image, caption=os.path.basename(file), use_column_width=True)

if __name__ == "__main__":
    main()
