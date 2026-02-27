import os
import zipfile
import hashlib
import xml.etree.ElementTree as ET

REPO_ROOT = "/opt/bgtv/archive/kodi_repo_staging"
ADDONS_XML_PATH = os.path.join(REPO_ROOT, "addons.xml")
ADDONS_MD5_PATH = os.path.join(REPO_ROOT, "addons.xml.md5")

def create_addons_xml():
    root = ET.Element("addons")
    # First, parse our own repository addon.xml
    repo_xml = os.path.join(REPO_ROOT, "repository.bgtv", "addon.xml")
    if os.path.exists(repo_xml):
        tree = ET.parse(repo_xml)
        root.append(tree.getroot())

    # Then parse the addon.xml out of every zip we host
    for walk_root, dirs, files in os.walk(REPO_ROOT):
        # don't traverse into .git or repository.bgtv
        if '.git' in dirs: dirs.remove('.git')
        if 'repository.bgtv' in dirs: dirs.remove('repository.bgtv')

        for file in files:
            if file.endswith(".zip"):
                zip_path = os.path.join(walk_root, file)
                try:
                    with zipfile.ZipFile(zip_path, 'r') as z:
                        # Find the addon.xml inside the zip. Usually it's in a subfolder `addon_id/addon.xml`
                        addon_xml_files = [f for f in z.namelist() if f.endswith('addon.xml')]
                        if addon_xml_files:
                            # Assume the shortest path is the root addon.xml
                            addon_xml_file = min(addon_xml_files, key=len)
                            with z.open(addon_xml_file) as xml_file:
                                addon_tree = ET.parse(xml_file)
                                root.append(addon_tree.getroot())
                except Exception as e:
                    print(f"Error processing {zip_path}: {e}")

    # Write the combined XML
    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ", level=0)
    tree.write(ADDONS_XML_PATH, encoding="UTF-8", xml_declaration=True)

    # Generate MD5 checksum
    with open(ADDONS_XML_PATH, "rb") as f:
        md5_hash = hashlib.md5()
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    
    with open(ADDONS_MD5_PATH, "w") as f:
        f.write(md5_hash.hexdigest())

    print("addons.xml and addons.xml.md5 successfully generated.")

if __name__ == "__main__":
    create_addons_xml()
