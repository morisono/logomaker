import os
import re
import markdown
import cairosvg
import pyshorteners


def markdown_to_svg(markdown_text, width ,height):
    try:
        html = markdown.markdown(markdown_text)
        svg_data = cairosvg.svg2svg(bytestring=html.encode('utf-8'), width=width, height=height)
        return svg_data
    except Exception as e:
        return e


def svg_to_png(svg_data, output_path):
    cairosvg.svg2png(bytestring=svg_data, write_to=output_path)


def combine_images(image_paths, x, y):
    images = [Image.open(file) for file in image_paths]

    if len(images) != x * y:
        return

    widths, heights = zip(*(i.size for i in images))

    total_width = sum(widths[:x])
    max_height = max(heights[i] for i in range(0, len(images), x))

    combined_image = Image.new('RGB', (total_width, max_height * y))

    x_offset, y_offset = 0, 0
    for i, image in enumerate(images):
        combined_image.paste(image, (x_offset, y_offset))
        x_offset += widths[i]

        if (i + 1) % x == 0:
            x_offset = 0
            y_offset += max_height

    return combined_image


def filename_matched(query, target_list):
    matched_files = []
    try:
        for file in target_list:
            if query in file:
                matched_files.append(file)
        return matched_files
    except Exception as e:
        return e


def full_text_search(query, path_list):
    matched_files = []

    for path in path_list:
        try:
            with open(path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

                for line_num, line in enumerate(lines, start=1):
                    if query in line:
                        matched_files.append((path, line_num))
        except FileNotFoundError:
            print(f"File not found: {path}")
        except IsADirectoryError:
            print(f"Directory is not supported: {path}")
        except Exception as e:
            print(f"Error occurred while processing file: {path}\n{e}")

    return matched_files


def recursive_search(pattern, path='.'):
    matched_files = []

    for root, dirs, files in os.walk(path):
        # Skip hidden directories and binary files
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        files[:] = [f for f in files if not is_binary(os.path.join(root, f))]

        for file in files:
            file_path = os.path.join(root, file)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                    for line_num, line in enumerate(lines, start=1):
                        if re.search(pattern, line):
                            matched_files.append((file_path, line_num))
            except UnicodeDecodeError:
                print(f"Skipped binary file: {file_path}")
            except Exception as e:
                print(f"Error occurred while processing file: {file_path}\n{e}")

    return matched_files


def is_binary(file_path):
    with open(file_path, 'rb') as f:
        chunk = f.read(1024)
        if b'\x00' in chunk:
            return True
        else:
            return False


def shorten_url(url):
    s = pyshorteners.Shortener(api_key="YOUR_KEY")
    short_url = s.bitly.short(url)
    return short_url
