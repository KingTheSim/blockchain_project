# File specifics
ALLOWED_EXTENSIONS = {"txt", "jpg", "jpeg", "png", "gif", "mp4", "mkv", "avi"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS