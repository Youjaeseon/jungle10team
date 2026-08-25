import os
from datetime import datetime, timezone

from bson import ObjectId
from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
)
from werkzeug.utils import secure_filename

from auth_util import login_required
from db import db