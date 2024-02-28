"""
Script that lets the user serve one or more files across the local network.

"""

import argparse
import pathlib

import magic
from flask import Flask

HTML_HEAD = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Web dump</title>
<style>
    .scroll-box {
        width: 300px; /* Set the width of the box */
        height: 200px; /* Set the height of the box */
        overflow: auto; /* Enable scrolling */
        border: 1px solid #ccc; /* Add border for styling */
        padding: 10px; /* Add padding for content spacing */
    }
    .collapsible {
        cursor: pointer;
    }
    .content {
        margin-top:10px;
        display: none;
        overflow: hidden;
    }
    img {
        max-height:
        width: auto;
    }
    video {
        max-height: 300px;
        width: auto;
    }
</style>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-secondary-subtle">
<nav class="navbar navbar-dark bg-secondary" style="margin-bottom: 20px;">
  <a class="navbar-brand" style="margin-left: 10px;" href="#">Dump to web</a>
</nav>
"""

HTML_FOOT = """
<script>
    var coll = document.getElementsByClassName("collapsible");
    var i;

    for (i = 0; i < coll.length; i++) {
        coll[i].addEventListener("click", function() {
            this.classList.toggle("active");
            var content = this.nextElementSibling;
            if (content.style.display === "block") {
                this.textContent = "Open";
                content.style.display = "none";
            } else {
                this.textContent = "Close";
                content.style.display = "block";
            }
        });
    }
</script>
</body>
</html>
"""

parser = argparse.ArgumentParser(description='Flask server to serve files across the web')
parser.add_argument('-i', '--ip-address', default='0.0.0.0', help='Listen IP')
parser.add_argument('-p', '--port', default=8000, help='Listen port')
parser.add_argument('-d', '--directory', help='Directory containing files',
                    required=True)
parser.add_argument('-r', '--recursive', action='store_true', help='Search recursively')
parser.add_argument('--verbose', action='store_true', help='Verbose output')
parser.add_argument('--debug', action='store_true', help='Flask debug mode')
args = parser.parse_args()

scan_dir = pathlib.Path(args.directory)

app = Flask(__name__, static_url_path="", static_folder=str(scan_dir))

VIDEO_MIME_TYPES = [
    'video/mp4',
    'video/webm',
    'video/ogg',
]

IMAGE_MIME_TYPES = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/svg+xml',
    'image/webp',
    'image/bmp',
    'image/x-icon',
    'image/tiff',
    'image/jp2'
]


def vprint(message):
    if not args.verbose:
        return
    print(message)


def get_html_link(file_path, file_type):
    ret = f'<a class="link-primary" href="{file_path}" target="_blank">{file_path}</a>'
    ret += f' <sub>({file_type})</sub>'
    return ret


def get_html_text_plain(text):
    return f'<div class="scroll-box">{text}</div>'


def get_html_image(file_path):
    return f'<img src="{file_path}" alt="Image Description">'


def get_html_video(file_path, video_type):
    ret = '<video controls>'
    ret += f'<source src="{file_path}" type="{video_type}">'
    ret += '</video>'
    return ret


class WebFile:
    def __init__(self, path):
        self.file_path = path
        self.file_rel_path = self.file_path.relative_to(scan_dir)
        self.file_type = None
        self.html = None

    def generate_html(self):
        mime = magic.Magic(mime=True)
        self.file_type = mime.from_file(self.file_path)

        self.html = '<div class="card bg-primary-subtle" style="width:90%; margin:0 auto;">'
        self.html += '<div class="card-body">'
        self.html += get_html_link(self.file_rel_path, self.file_type)

        preview = None

        match self.file_type:
            case 'text/plain':
                try:
                    with open(self.file_path, 'r', encoding='utf-8') as f:
                        preview = get_html_text_plain(f.read())
                except UnicodeDecodeError:
                    vprint(f"Failed to decode {self.file_path}")
            case x if x in VIDEO_MIME_TYPES:
                preview = get_html_video(self.file_rel_path, self.file_type)
            case x if x in IMAGE_MIME_TYPES:
                preview = get_html_image(self.file_rel_path)

        if preview:
            self.html += ' <button class="collapsible btn btn-secondary btn-sm">Open</button>'
            self.html += '<div class="content">'
            self.html += preview
            self.html += '</div>'
        self.html += '</div></div><br/>'

    def get_html(self):
        return self.html or ""


def read_files(directory, recursive=False):
    if not directory.is_dir():
        raise TypeError(f"{directory} is not a directory")

    objects = []
    for file in directory.iterdir():
        if file.is_file():
            objects.append(file)
        elif file.is_dir():
            if recursive:
                objects.extend(read_files(file, recursive))
        else:
            vprint(f"{file} is neither file nor directory, ignoring")

    return objects


@app.route('/')
def index():
    # Read files
    file_store = read_files(scan_dir, args.recursive)

    # Process files and get their html
    html = HTML_HEAD
    for fil in sorted(file_store):
        wf = WebFile(fil)
        wf.generate_html()
        html += wf.get_html()
    html += HTML_FOOT

    return html


app.run(debug=args.debug, host=args.ip_address, port=args.port)
