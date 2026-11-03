"""Compatibility imports; implementations live in dedicated apps."""
from customer_accounts.models import Customer, CustomerManager
from staff_access.models import Group, StaffUser
__all__ = ["Customer", "CustomerManager", "Group", "StaffUser"]
