import json
import os
from flask import request, Response

from reviewer2 import DIRECTORY_TO_IMAGE_FILES_LIST
from reviewer2.utils import get_page_url, get_html_head


def image_page_handler():
    params = {}
    if request.values:
        params.update(request.values)

    if 'i' not in params:
        params.update(request.get_json(force=True, silent=True) or {})

    i = params.get("i")
    try:
        i = int(i)
    except ValueError:
        i = 1

    last = params.get("last", i)
    try:
        last = int(last)
    except ValueError:
        last = i

    if i < 1 or i > len(DIRECTORY_TO_IMAGE_FILES_LIST):
        i = 1

    dirname, image_files = DIRECTORY_TO_IMAGE_FILES_LIST[i - 1]

    # top of page
    prev_link = "" if i <= 1 else get_page_url(i - 1, DIRECTORY_TO_IMAGE_FILES_LIST)
    next_link = "" if i >= last else get_page_url(i + 1, DIRECTORY_TO_IMAGE_FILES_LIST)

    # metadata html
    metadata_json = {}
    metadata_path = os.path.join(dirname, "reviewer2_metadata.json")
    if os.path.isfile(metadata_path):
        try:
            with open(metadata_path, "rt") as f:
                metadata_json = json.load(f)
        except Exception as e:
            print(f"Unable to parse {metadata_path}: {e}")

    metadata_html = ""
    if isinstance(metadata_json, dict):
        for key, value in metadata_json.items():
            metadata_html += f"""{key}: {value} <br />"""

    # image files
    image_files_html = ""
    for path in image_files:
        image_files_html += f"""
   <hr />
   <b>{path}</b> <br />
   <img src="/{path}" /><br /><br />     
"""

    html = f"""
<html>
{get_html_head()}
<body>
    <div class="ui stackable grid" style="margin-top: 1px">
        <div class="row">
            <div class="one wide column"></div>
            <div class="fourteen wide column">
                <div class="ui stackable grid">
                    <div class="row">
                        <div class="one wide column"></div>
                        <div class="two wide column">
                            <a href="/"><i class="home icon"></i> &nbsp; page list</a>
                        </div>
                        <div class="ten wide column" style="text-align:center">
                            <b>{dirname}</b>
                        </div>
                        <div class="two wide column">     
                            <a href="{prev_link}"><i class="arrow left icon"></i> &nbsp; prev</a> 
                            &nbsp; 
                            <a href="{next_link}">next &nbsp; <i class="arrow right icon"></i></a>
                        </div>
                        <div class="one wide column"></div>
                    </div>
                </div>
                {metadata_html}<br/>
                {image_files_html}<br />
            </div>
            <div class="one wide column"></div>
        </div>
    </div>
</body>
</html>    
"""
    return Response(html, mimetype='text/html')

