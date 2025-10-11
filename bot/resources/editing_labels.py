from enum import Enum


class EditingLabels(Enum):
    EDITED = "(Edited)"
    EDIT_FAILED = "(Editing failed, previous state remains)"
    DELETION_FAILED = "(Deletion failed, expense stays)"
