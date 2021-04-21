from flask import Flask, Response, send_from_directory
from flask_cors import CORS
import os
import pkg_resources

from reviewer2 import args
from reviewer2.main_list import main_list_handler
from reviewer2.data_page import data_page_handler
from reviewer2.save import save_form_handler


def send_file(path):
    print(f"Sending {args.directory} {path}")
    if path.startswith("favicon"):
        return Response(pkg_resources.resource_stream('reviewer2', 'icons/favicon.png'), mimetype='image/png')

    return send_from_directory(args.directory, path, as_attachment=True)


app = Flask(__name__)
CORS(app)

app.url_map.strict_slashes = False

app.add_url_rule('/', view_func=main_list_handler, methods=['GET'])
app.add_url_rule('/page', view_func=data_page_handler, methods=['POST', 'GET'])
app.add_url_rule('/save', view_func=save_form_handler, methods=['POST'])
app.add_url_rule('/<path:path>', view_func=send_file, methods=['GET'])

os.environ["WERKZEUG_RUN_MAIN"] = "true"

app.run(
    debug=args.dev_mode,
    host=os.environ.get('HOST', '127.0.0.1'),
    port=int(os.environ.get('PORT', 8080)))

