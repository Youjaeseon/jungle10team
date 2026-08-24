from flask import Blueprint, g, jsonify, redirect, render_template, request
from bson import ObjectId
from datetime import datetime, timezone

from db import db
from auth_util import login_required

chat_bp = Blueprint('caht', __name__)