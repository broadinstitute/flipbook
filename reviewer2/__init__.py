import configargparse
import os
from reviewer2.utils import get_directory_to_image_files_list

p = configargparse.ArgumentParser()
p.add_argument("-x", "--exclude-file-keyword", action="append")
p.add_argument("-d", "--directory", default=".")
args = p.parse_args()

if not os.path.isdir(args.directory):
    p.error(f"{args.directory} directory not found")

DIRECTORY_TO_IMAGE_FILES_LIST = get_directory_to_image_files_list(args.directory, args.exclude_file_keyword)
if not DIRECTORY_TO_IMAGE_FILES_LIST:
    p.error(f"No images found in {args.directory}")
