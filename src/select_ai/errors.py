class SelectAIError(Exception):
    """Base class for any SelectAIErrors"""

    pass


class ProfileNotFoundError(SelectAIError):
    """Profile not found in the database"""

    def __init__(self, profile_name: str):
        self.profile_name = profile_name

    def __str__(self):
        return f"Profile {self.profile_name} not found"


class VectorIndexNotFoundError(SelectAIError):
    """VectorIndex not found in the database"""

    def __init__(self, index_name: str, profile_name: str = None):
        self.index_name = index_name
        self.profile_name = profile_name

    def __str__(self):
        if self.profile_name:
            return (
                f"VectorIndex {self.index_name} "
                f"not found for profile {self.profile_name}"
            )
        else:
            return f"VectorIndex {self.index_name} not found"
