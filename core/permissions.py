from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    """
    ✅ Seuls les utilisateurs avec le rôle "ADMIN" peuvent accéder.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "ADMIN"
