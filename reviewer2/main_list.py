from flask import Response
from reviewer2 import DIRECTORY_TO_IMAGE_FILES_LIST
from reviewer2.utils import get_page_url, get_html_head


def main_list_handler():
    add_images_column = any(len(contents) > 1 for _, contents in DIRECTORY_TO_IMAGE_FILES_LIST)

    table_rows_html = ""
    for page_number, (dirname, contents) in enumerate(DIRECTORY_TO_IMAGE_FILES_LIST):
        page_number += 1

        table_rows_html += '<tr>'
        table_rows_html += f'  <td style="width: 1%">{page_number}.</td>'
        table_rows_html += (f'  <td style="width: 1%; padding-right: 100px;">'
            f'<a href="{get_page_url(page_number, DIRECTORY_TO_IMAGE_FILES_LIST)}">{dirname}</a>'
            f'</td>')
        if add_images_column:
            table_rows_html += f'<td style="width: 1%">{len(contents)} images</td>'
        table_rows_html += '</tr>'

    html = f"""
<html>
{get_html_head()}
<body>
    <div class="ui stackable grid">
        <div class="row">
            <div class="one wide column"></div>
            <div class="one wide column">
                <br />
                For review: <br />

                <table class='ui stackable table' style='border: none'>
                    {table_rows_html}
                </table>
            </div>
        </div>
    </div>
</body>
</html>    
"""
    return Response(html, mimetype='text/html')


