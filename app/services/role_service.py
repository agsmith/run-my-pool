from enum import Enum, auto


class Tab(Enum):
    DASHBOARD = auto()
    RULE = auto()
    EVENT = auto()


class Role(Enum):
    ADMIN = auto()
    BUSINESS = auto()
    VIEWER = auto()


class Operation(Enum):
    VIEW = auto()
    EDIT = auto()
    ADD = auto()
    DELETE = auto()


class RoleService:

    TAB_OPERATION_ROLE_PERMISSIONS = {
        Tab.DASHBOARD: {
            Operation.VIEW: {Role.ADMIN, Role.BUSINESS, Role.VIEWER},
        },
        Tab.EVENT: {
            Operation.VIEW: {Role.ADMIN, Role.BUSINESS, Role.VIEWER},
        },
        Tab.RULE: {
            Operation.VIEW: {Role.ADMIN, Role.BUSINESS, Role.VIEWER},
            Operation.EDIT: {Role.BUSINESS, Role.ADMIN},
            Operation.ADD: {Role.ADMIN},
            Operation.DELETE: {Role.ADMIN},
        }
    }

    @staticmethod
    def is_authorized(role: str, tab: Tab, operation: Operation) -> bool:
        if not role:
            return False
        try:
            role = Role[role.upper()]
        except KeyError:
            return False

        tab_ops = RoleService.TAB_OPERATION_ROLE_PERMISSIONS.get(tab, {})
        allowed_roles = tab_ops.get(operation, set())
        return role in allowed_roles

    @staticmethod
    def parse_role(role_str: str):
        if not role_str:
            return None
        role_part = role_str.rsplit('_', 1)[-1].upper()
        try:
            return Role[role_part]
        except KeyError:
            return None

    @staticmethod
    def has_permission(session_data: dict, tab: Tab, operation: Operation) -> bool:
        role_name = session_data["user_role"]
        role = RoleService.parse_role(role_name)
        if not role:
            return False

        tab_ops = RoleService.TAB_OPERATION_ROLE_PERMISSIONS.get(tab, {})
        allowed_roles = tab_ops.get(operation, set())
        return role in allowed_roles
