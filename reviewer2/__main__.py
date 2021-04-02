from flask import Flask, Response, send_from_directory
from flask_cors import CORS
import os
import pkg_resources
from reviewer2 import args
from reviewer2.main_list import main_list_handler
from reviewer2.image_page import image_page_handler


def send_file(path):
    print(f"Fetching {args.directory} {path}")
    if path.startswith("favicon"):
        stream = pkg_resources.resource_stream('reviewer2', path)
        return Response(stream, mimetype='image/png')

    return send_from_directory(args.directory, path, as_attachment=True)


app = Flask(__name__)
CORS(app)

app.add_url_rule('/', view_func=main_list_handler, methods=['GET'])
app.add_url_rule('/page/', view_func=image_page_handler, methods=['POST', 'GET'])
app.add_url_rule('/<path:path>', view_func=send_file, methods=['GET'])

app.run(
    debug=os.environ.get("DEBUG", False),
    host=os.environ.get('HOST', '127.0.0.1'),
    port=int(os.environ.get('PORT', 8080)))

