from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsPatient(BasePermission):
    message = "Patient access is required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "patient")


class IsDoctor(BasePermission):
    message = "Doctor access is required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "doctor")


class IsVerifiedDoctor(BasePermission):
    message = "A verified doctor account is required for patient-care workflows."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "doctor"
            and request.user.is_verified
        )


class IsPatientOrVerifiedDoctor(BasePermission):
    message = "Patient or verified doctor access is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.role == "patient"
                or (user.role == "doctor" and user.is_verified)
            )
        )


class IsAdminStaff(BasePermission):
    message = "Staff access is required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsOwnUserOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        return bool(request.user.is_staff or obj.pk == request.user.pk)
