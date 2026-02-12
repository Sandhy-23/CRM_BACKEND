from functools import wraps
from flask import jsonify, request

# Temporary example user role fetch
# Later you connect this with JWT user
def get_current_user_role():
    # For now return Admin to avoid blocking
    return "Admin"


def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_role = get_current_user_role()

            roles_hierarchy = {
                "Admin": 3,
                "Manager": 2,
                "Agent": 1
            }

            if roles_hierarchy.get(user_role, 0) < roles_hierarchy.get(required_role, 0):
                return jsonify({"error": "Unauthorized"}), 403

            return f(*args, **kwargs)

        return wrapper
    return decorator