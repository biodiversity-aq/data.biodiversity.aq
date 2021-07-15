from rest_framework import permissions


class IsAuthenticatedAndIsOwner(permissions.BasePermission):
    """
    Permission class that allows access only to authenticated users and objects owner.
    """

    def has_permission(self, request, view):
        """
        Allows access only to authenticated users.
        """
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        """
        Allows access only to object which belongs to the authenticated user. Object has to have a user attribute.
        """
        return obj.user == request.user
