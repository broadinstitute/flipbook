from flask import Flask, Response, send_from_directory
from flask_cors import CORS
import jinja2
import os
import pkg_resources

from flipbook import args
from flipbook.main_list import main_list_handler
from flipbook.data_page import data_page_handler
from flipbook.save import save_form_handler


def send_file(path):
    print(f"Sending {args.directory} {path}")
    if path.startswith("favicon"):
        return Response(pkg_resources.resource_stream('flipbook', 'icons/favicon.png'), mimetype='image/png')

    return send_from_directory(args.directory, path, as_attachment=True)


app = Flask(__name__)
CORS(app)

# add a ctime(..) function to allow the last-changed-time of a path to be computed within a jinja template
jinja2.environment.DEFAULT_FILTERS['ctime'] = lambda path: int(os.path.getctime(path)) if os.path.isfile(path) else 0

#app.add_template_filter(lambda path: int(os.path.getctime(path)) if os.path.isfile(path) else 0, name="ctime")

app.url_map.strict_slashes = False

app.add_url_rule('/', view_func=main_list_handler, methods=['GET'])
app.add_url_rule('/page', view_func=data_page_handler, methods=['POST', 'GET'])
app.add_url_rule('/save', view_func=save_form_handler, methods=['POST'])
app.add_url_rule('/<path:path>', view_func=send_file, methods=['GET'])



os.environ["WERKZEUG_RUN_MAIN"] = "true"

host = os.environ.get('HOST', args.host)
port = int(os.environ.get('PORT', args.port))
if args.verbose:
    print(f"Connecting to {host}:{port}")

app.run(
    debug=args.dev_mode,
    host=host,
    port=port)

