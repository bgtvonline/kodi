import os

def generate_index(directory):
    files_and_dirs = os.listdir(directory)
    files_and_dirs.sort()

    html = "<html><head><title>Index of /</title></head><body><h1>BGTV Kodi Repository</h1><hr><pre>\n"
    html += "<a href=\"../\">../</a>\n"

    for item in files_and_dirs:
        if item in ['.git', 'generate_index.py', 'index.html', 'README.md']: continue
        path = os.path.join(directory, item)
        if os.path.isdir(path):
            html += f"<a href=\"{item}/\">{item}/</a>\n"
            generate_index(path)
        elif item.endswith(".zip"):
            html += f"<a href=\"{item}\">{item}</a>\n"

    html += "</pre><hr></body></html>"
    
    with open(os.path.join(directory, "index.html"), "w") as f:
        f.write(html)

generate_index(".")
